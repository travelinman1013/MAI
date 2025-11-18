import asyncio
import pytest
from pydantic import BaseModel, ValidationError
from typing import Optional

from src.core.tools.base import tool, ToolMetadata
from src.core.tools.registry import tool_registry, ToolRegistry
from src.core.tools.decorators import with_retry, with_timeout, with_cache, with_rate_limit
from src.core.utils.exceptions import ToolExecutionError, RateLimitExceededError, ToolTimeoutError
from src.infrastructure.cache.redis_client import RedisClient # for mocking
from src.core.utils.logging import get_logger_with_context

# Clear registry before each test (important for isolated tests)
@pytest.fixture(autouse=True)
def clear_tool_registry():
    tool_registry.clear()
    yield

# --- Test tool decorator and registry ---
def test_tool_registration():
    @tool(name="test_func", description="A test function", category="testing")
    def my_test_func(a: int, b: str) -> str:
        return f"{b}_{a}"

    assert tool_registry.get_tool("test_func") is not None
    func, metadata = tool_registry.get_tool("test_func")
    assert func == my_test_func
    assert metadata.name == "test_func"
    assert metadata.description == "A test function"
    assert metadata.category == "testing"
    assert "parameters" in metadata.model_dump()
    assert "returns" in metadata.model_dump()

    # Check parameter schema
    param_schema = metadata.parameters
    assert "properties" in param_schema
    assert "a" in param_schema["properties"]
    assert param_schema["properties"]["a"]["type"] == "integer"
    assert "b" in param_schema["properties"]
    assert param_schema["properties"]["b"]["type"] == "string"

    # Check return schema
    return_schema = metadata.returns
    assert "type" in return_schema
    assert return_schema["type"] == "string"


def test_tool_input_validation():
    @tool(name="validate_input", description="Validates input")
    def validate_input_func(a: int, b: str):
        return f"{a}-{b}"

    func, _ = tool_registry.get_tool("validate_input")

    # Valid input
    result = func(a=1, b="hello")
    assert result == "1-hello"

    # Invalid input type
    with pytest.raises(ToolExecutionError):
        func(a="not_an_int", b="hello")

    # Missing required input
    with pytest.raises(ToolExecutionError):
        func(b="hello")


def test_tool_output_validation():
    @tool(name="validate_output", description="Validates output")
    def validate_output_func(a: int) -> str:
        return str(a)

    func, _ = tool_registry.get_tool("validate_output")
    result = func(a=10)
    assert result == "10"

    @tool(name="invalid_output", description="Returns wrong type")
    def invalid_output_func() -> int:
        return "not_an_int" # Should fail validation

    func_invalid, _ = tool_registry.get_tool("invalid_output")
    with pytest.raises(ToolExecutionError):
        func_invalid()


# --- Test decorators ---
async def test_with_retry_async():
    call_count = 0

    @tool(name="retry_tool", description="Tool with retry")
    @with_retry(max_attempts=3, initial_delay=0.01, catch_exceptions=(ValueError,))
    async def flaky_async_tool():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Flaky error")
        return "Success"
    
    # Original function is wrapped by tool decorator, which has async_wrapper
    # then with_retry adds another async_wrapper.
    # The tool_registry get_tool will return the outermost wrapper.
    wrapped_tool_func, _ = tool_registry.get_tool("retry_tool")
    result = await wrapped_tool_func()
    assert result == "Success"
    assert call_count == 3


def test_with_retry_sync():
    call_count = 0

    @tool(name="retry_tool_sync", description="Tool with sync retry")
    @with_retry(max_attempts=3, initial_delay=0.01, catch_exceptions=(ValueError,))
    def flaky_sync_tool():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Flaky error")
        return "Success"
    
    wrapped_tool_func, _ = tool_registry.get_tool("retry_tool_sync")
    result = wrapped_tool_func()
    assert result == "Success"
    assert call_count == 3


async def test_with_timeout_async():
    @tool(name="timeout_tool", description="Tool with timeout")
    @with_timeout(timeout_seconds=0.1)
    async def slow_async_tool():
        await asyncio.sleep(0.2)
        return "Too slow"

    wrapped_tool_func, _ = tool_registry.get_tool("timeout_tool")
    with pytest.raises(ToolTimeoutError):
        await wrapped_tool_func()

    @tool(name="fast_tool", description="Fast tool")
    @with_timeout(timeout_seconds=0.5)
    async def fast_async_tool():
        await asyncio.sleep(0.01)
        return "Fast enough"
    
    wrapped_fast_tool_func, _ = tool_registry.get_tool("fast_tool")
    result = await wrapped_fast_tool_func()
    assert result == "Fast enough"

def test_with_timeout_sync():
    @tool(name="timeout_tool_sync", description="Sync tool with timeout")
    @with_timeout(timeout_seconds=0.1)
    def slow_sync_tool():
        time.sleep(0.2)
        return "Too slow"
    
    wrapped_tool_func, _ = tool_registry.get_tool("timeout_tool_sync")
    # Sync tools with timeout only log a warning, don't raise ToolTimeoutError directly
    # because the `with_timeout` decorator for sync functions doesn't enforce it
    # in the same way as async functions do.
    result = wrapped_tool_func()
    assert result == "Too slow" # The function still executes and returns


# --- Mock RedisClient for cache/rate_limit tests ---
class MockRedisClient:
    def __init__(self):
        self.cache = {}
        self.lists = {}
        self.ttl = {}
    
    async def connect(self): pass
    async def disconnect(self): pass
    async def ping(self): return True
    async def health_check(self): return True
    async def exists(self, key):
        if key in self.ttl and self.ttl[key] < time.time():
            self.cache.pop(key, None)
            self.ttl.pop(key, None)
            return False
        return key in self.cache

    async def get(self, key):
        if await self.exists(key):
            return self.cache[key]
        return None

    async def set(self, key, value, ttl=None):
        self.cache[key] = value
        if ttl:
            self.ttl[key] = time.time() + ttl
    
    async def lrange(self, key, start, end):
        return [ts for ts in self.lists.get(key, []) if ts > (time.time() - self.ttl.get(f"list_ttl_{key}", 0))]
    
    async def rpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)
    
    async def ltrim(self, key, start, end):
        if key in self.lists:
            self.lists[key] = self.lists[key][start:end]
            
    async def expire(self, key, ttl):
        # For simplicity in mock, just use the key directly for list expiration
        self.ttl[f"list_ttl_{key}"] = time.time() + ttl


async def test_with_cache():
    mock_redis = MockRedisClient()

    @tool(name="cached_tool", description="Tool with cache")
    @with_cache(ttl=1, redis_client_getter=lambda: mock_redis)
    async def my_cached_tool(value: str):
        return f"processed_{value}_{time.time()}"

    wrapped_tool_func, _ = tool_registry.get_tool("cached_tool")

    # First call, should cache
    result1 = await wrapped_tool_func(value="data")
    assert "processed_data" in result1
    assert await mock_redis.exists("tool_cache:cached_tool:data")

    # Second call, should hit cache
    result2 = await wrapped_tool_func(value="data")
    assert result1 == result2

    # Wait for cache to expire
    await asyncio.sleep(1.1)

    # Third call, cache should be expired, new result
    result3 = await wrapped_tool_func(value="data")
    assert result1 != result3
    assert "processed_data" in result3


async def test_with_rate_limit():
    mock_redis = MockRedisClient()
    mock_redis.lists = {} # Clear any previous lists from other tests

    @tool(name="rate_limited_tool", description="Tool with rate limit")
    @with_rate_limit(calls=2, period=1, redis_client_getter=lambda: mock_redis)
    async def my_rate_limited_tool():
        return "Called"

    wrapped_tool_func, _ = tool_registry.get_tool("rate_limited_tool")

    # First call
    result1 = await wrapped_tool_func()
    assert result1 == "Called"

    # Second call
    result2 = await wrapped_tool_func()
    assert result2 == "Called"

    # Third call, should exceed rate limit
    with pytest.raises(RateLimitExceededError):
        await wrapped_tool_func()
    
    # Wait for period to pass
    await asyncio.sleep(1.1)

    # Call again, should succeed
    result3 = await wrapped_tool_func()
    assert result3 == "Called"

