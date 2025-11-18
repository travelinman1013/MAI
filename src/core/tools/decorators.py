"""
Decorators for enhancing AI agent tools in MAI Framework.

Provides common cross-cutting concerns like retry logic, caching,
rate limiting, and timeouts for tool executions.
"""

from typing import Any, Callable, TypeVar
from functools import wraps
import time
import asyncio # Keep asyncio for wait_for
from inspect import iscoroutinefunction as _is_coroutine_function

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from src.infrastructure.cache.redis_client import RedisClient
from src.core.utils.exceptions import ToolExecutionError, RateLimitExceededError, ToolTimeoutError
from src.core.utils.logging import get_logger_with_context

ToolFunc = TypeVar("ToolFunc", bound=Callable[..., Any])
logger = get_logger_with_context(module="tool_decorators")


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    exp_base: float = 2.0,
    catch_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[ToolFunc], ToolFunc]:
    """
    Decorator to add retry logic to a tool function.

    Args:
        max_attempts: Maximum number of times to retry the function.
        initial_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum delay in seconds between retries.
        exp_base: The base of the exponential backoff.
        catch_exceptions: Tuple of exception types to catch and retry on.

    Returns:
        A decorator that adds retry logic to the tool function.
    """

    def decorator(func: ToolFunc) -> ToolFunc:
        @wraps(func)
        @retry(
            wait=wait_exponential(multiplier=initial_delay, min=initial_delay, max=max_delay, exp_base=exp_base),
            stop=stop_after_attempt(max_attempts),
            retry=retry_if_exception_type(catch_exceptions),
            reraise=True,
        )
        async def async_wrapper(*args, **kwargs) -> Any:
            logger.debug(f"Attempting to run tool {func.__name__}")
            return await func(*args, **kwargs)

        @wraps(func)
        @retry(
            wait=wait_exponential(multiplier=initial_delay, min=initial_delay, max=max_delay, exp_base=exp_base),
            stop=stop_after_attempt(max_attempts),
            retry=retry_if_exception_type(catch_exceptions),
            reraise=True,
        )
        def sync_wrapper(*args, **kwargs) -> Any:
            logger.debug(f"Attempting to run tool {func.__name__}")
            return func(*args, **kwargs)

        # Return the appropriate wrapper based on whether the function is a coroutine
        if _is_coroutine_function(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


def with_timeout(timeout_seconds: int) -> Callable[[ToolFunc], ToolFunc]:
    """
    Decorator to add a timeout to a tool function.

    Args:
        timeout_seconds: The maximum number of seconds to wait for the function to complete.

    Returns:
        A decorator that adds timeout logic to the tool function.
    """

    def decorator(func: ToolFunc) -> ToolFunc:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Tool {func.__name__} timed out after {timeout_seconds} seconds.")
                raise ToolTimeoutError(f"Tool {func.__name__} timed out.")

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Synchronous functions cannot be directly wrapped with asyncio.wait_for
            # A common approach is to run them in a separate thread.
            # For simplicity, we'll assume tools that need timeouts are async,
            # or the user handles it externally for sync tools.
            # Alternatively, could use threading.Thread and join with timeout.
            logger.warning(f"Timeout decorator applied to sync tool {func.__name__}. "
                           "This is not directly supported without running in a separate thread.")
            start_time = time.time()
            result = func(*args, **kwargs)
            if (time.time() - start_time) > timeout_seconds:
                 logger.warning(f"Sync tool {func.__name__} exceeded unofficial timeout of {timeout_seconds}s. "
                                "Result already returned.")
            return result
        
        if _is_coroutine_function(func):
            return async_wrapper # type: ignore
        else:
            # If the tool is synchronous, we can't directly apply asyncio.wait_for.
            # We'll return the original function but log a warning.
            return sync_wrapper # type: ignore

    return decorator


def with_cache(
    ttl: int = 3600,
    key_prefix: str = "tool_cache",
    redis_client_getter: Callable[[], RedisClient] = lambda: RedisClient(),
) -> Callable[[ToolFunc], ToolFunc]:
    """
    Decorator to cache tool function results in Redis.

    Args:
        ttl: Time-to-live in seconds for the cached result.
        key_prefix: Prefix for Redis cache keys.
        redis_client_getter: A callable that returns an instance of RedisClient.
                             Allows for dependency injection of Redis client.

    Returns:
        A decorator that adds caching logic to the tool function.
    """

    def decorator(func: ToolFunc) -> ToolFunc:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            redis = redis_client_getter()
            # Generate a cache key based on function name, args, and kwargs
            cache_key_parts = [key_prefix, func.__name__]
            cache_key_parts.extend(str(arg) for arg in args)
            cache_key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(cache_key_parts)

            try:
                if await redis.exists(cache_key):
                    cached_result = await redis.get(cache_key)
                    logger.debug(f"Cache hit for tool {func.__name__}: {cache_key}")
                    return cached_result
                
                logger.debug(f"Cache miss for tool {func.__name__}: {cache_key}")
                result = await func(*args, **kwargs)
                await redis.set(cache_key, result, ttl=ttl)
                return result
            except Exception as e:
                logger.error(f"Error during caching for tool {func.__name__}: {e}")
                # Don't prevent execution if caching fails, just log and proceed
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger.warning(f"Cache decorator applied to sync tool {func.__name__}. "
                           "Caching for sync tools requires an async Redis client. "
                           "Please ensure the Redis client getter can provide an async client "
                           "and that the tool is run in an async context, or implement sync caching.")
            
            # For a synchronous tool with an async RedisClient, we need to run async operations.
            # This is generally discouraged for simplicity of design.
            # For now, we'll just run the function directly.
            # A more robust solution might involve an internal asyncio event loop
            # or a synchronous Redis client.
            return func(*args, **kwargs)
        
        if _is_coroutine_function(func):
            return async_wrapper # type: ignore
        else:
            return sync_wrapper # type: ignore

    return decorator


def with_rate_limit(
    calls: int,
    period: int,
    key_prefix: str = "tool_ratelimit",
    redis_client_getter: Callable[[], RedisClient] = lambda: RedisClient(),
) -> Callable[[ToolFunc], ToolFunc]:
    """
    Decorator to add rate limiting to a tool function using a sliding window counter in Redis.

    Args:
        calls: Maximum number of calls allowed within the period.
        period: Time window in seconds for the rate limit.
        key_prefix: Prefix for Redis rate limit keys.
        redis_client_getter: A callable that returns an instance of RedisClient.

    Returns:
        A decorator that adds rate limiting logic to the tool function.
    """

    def decorator(func: ToolFunc) -> ToolFunc:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            redis = redis_client_getter()
            rate_limit_key = f"{key_prefix}:{func.__name__}"
            
            current_time = int(time.time())
            window_start = current_time - period

            try:
                # Remove timestamps older than the current window
                await redis.ltrim(rate_limit_key, -calls, -1) # Keep only the last 'calls' elements

                # Count calls within the current window
                timestamps = await redis.lrange(rate_limit_key, 0, -1)
                
                # Filter out expired timestamps
                active_calls = [ts for ts in timestamps if ts > window_start]

                if len(active_calls) >= calls:
                    logger.warning(f"Rate limit exceeded for tool {func.__name__}.")
                    raise RateLimitExceededError(f"Rate limit for tool {func.__name__} exceeded ({calls}/{period}s).")
                
                # Add current call timestamp
                await redis.rpush(rate_limit_key, current_time)
                await redis.expire(rate_limit_key, period) # Ensure the list expires

                return await func(*args, **kwargs)
            except RateLimitExceededError:
                raise # Re-raise if it's our own specific exception
            except Exception as e:
                logger.error(f"Error during rate limiting for tool {func.__name__}: {e}")
                # Don't prevent execution if rate limiting mechanism fails, just log and proceed
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            logger.warning(f"Rate limit decorator applied to sync tool {func.__name__}. "
                           "Rate limiting for sync tools requires an async Redis client. "
                           "Please ensure the Redis client getter can provide an async client "
                           "and that the tool is run in an async context, or implement sync rate limiting.")
            return func(*args, **kwargs)
        
        if _is_coroutine_function(func):
            return async_wrapper # type: ignore
        else:
            return sync_wrapper # type: ignore

    return decorator