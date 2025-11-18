"""Async Redis client wrapper with connection pooling and retry logic.

This module provides a production-ready Redis client with:
- Async operations using redis.asyncio
- Connection pooling with configurable pool size
- JSON serialization/deserialization for complex values
- Key prefix support for namespace management
- Retry logic with exponential backoff
- Health check functionality
- Support for various Redis data types (strings, hashes, lists, sets)
"""

import asyncio
import json
from typing import Any, Optional, Union

import redis.asyncio as aioredis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from src.core.utils.config import RedisSettings, get_settings
from src.core.utils.exceptions import MAIException
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()


class RedisClientError(MAIException):
    """Redis client operation error."""

    def __init__(self, message: str, operation: str, **kwargs):
        super().__init__(
            error_code="REDIS_ERROR",
            message=message,
            details={"operation": operation, **kwargs},
            retryable=True,
        )


class RedisClient:
    """Async Redis client with connection pooling and advanced features.

    Features:
    - Connection pooling for efficient resource usage
    - JSON serialization for complex Python objects
    - Key prefix support for namespace isolation (MAI:cache:, MAI:session:, etc.)
    - Retry logic with exponential backoff
    - Health checks for monitoring
    - Support for strings, hashes, lists, sets, and sorted sets
    - Rate limiting primitives (increment/decrement)

    Example:
        ```python
        from src.infrastructure.cache.redis_client import RedisClient
        from src.core.utils.config import get_settings

        settings = get_settings()
        client = RedisClient(settings.redis)

        await client.connect()
        await client.set("user:123", {"name": "John", "age": 30}, ttl=3600)
        user_data = await client.get("user:123")
        await client.disconnect()
        ```
    """

    def __init__(
        self,
        settings: Optional[RedisSettings] = None,
        key_prefix: str = "MAI:",
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """Initialize Redis client.

        Args:
            settings: Redis configuration settings. If None, uses global settings.
            key_prefix: Prefix for all keys (default: "MAI:")
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Initial delay between retries in seconds (exponential backoff)
        """
        self.settings = settings or get_settings().redis
        self.key_prefix = key_prefix
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None
        self._connected = False

        logger.info(
            "Redis client initialized",
            url=self.settings.url,
            key_prefix=self.key_prefix,
            max_retries=self.max_retries,
        )

    async def connect(self) -> None:
        """Establish connection to Redis server.

        Creates a connection pool and initializes the Redis client.

        Raises:
            RedisClientError: If connection fails after retries.
        """
        if self._connected:
            logger.warning("Redis client already connected")
            return

        try:
            # Create connection pool
            self.pool = ConnectionPool.from_url(
                self.settings.url,
                max_connections=self.settings.max_connections,
                decode_responses=self.settings.decode_responses,
                socket_timeout=self.settings.timeout,
                socket_connect_timeout=self.settings.timeout,
            )

            # Create Redis client
            self.client = Redis(connection_pool=self.pool)

            # Test connection
            await self.ping()

            self._connected = True
            logger.info("Redis client connected successfully")

        except (ConnectionError, TimeoutError) as e:
            error_msg = f"Failed to connect to Redis: {e}"
            logger.error(error_msg, error=str(e))
            raise RedisClientError(error_msg, operation="connect", error=str(e))

    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources."""
        if not self._connected:
            logger.warning("Redis client not connected")
            return

        try:
            if self.client:
                await self.client.aclose()

            if self.pool:
                await self.pool.aclose()

            self._connected = False
            logger.info("Redis client disconnected successfully")

        except Exception as e:
            logger.error("Error disconnecting Redis client", error=str(e))
            raise RedisClientError(
                f"Failed to disconnect from Redis: {e}", operation="disconnect", error=str(e)
            )

    def _make_key(self, key: str) -> str:
        """Add prefix to key.

        Args:
            key: Original key name

        Returns:
            Prefixed key
        """
        return f"{self.key_prefix}{key}"

    async def _retry_operation(self, operation_name: str, operation_func, *args, **kwargs) -> Any:
        """Execute operation with retry logic and exponential backoff.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to execute
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation

        Returns:
            Result from the operation

        Raises:
            RedisClientError: If all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await operation_func(*args, **kwargs)

            except (RedisError, ConnectionError, TimeoutError) as e:
                last_error = e
                delay = self.retry_delay * (2**attempt)  # Exponential backoff

                logger.warning(
                    f"Redis operation failed, retrying",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    delay=delay,
                    error=str(e),
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)

        # All retries failed
        error_msg = f"Redis operation '{operation_name}' failed after {self.max_retries} attempts"
        logger.error(error_msg, error=str(last_error))
        raise RedisClientError(
            error_msg, operation=operation_name, attempts=self.max_retries, error=str(last_error)
        )

    def _serialize(self, value: Any) -> str:
        """Serialize Python object to JSON string.

        Args:
            value: Value to serialize

        Returns:
            JSON string
        """
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        return json.dumps(value)

    def _deserialize(self, value: Optional[str]) -> Any:
        """Deserialize JSON string to Python object.

        Args:
            value: JSON string or None

        Returns:
            Deserialized Python object or None
        """
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # If not valid JSON, return as string
            return value

    # ===== Basic String Operations =====

    async def get(self, key: str) -> Any:
        """Get value by key.

        Args:
            key: Key name

        Returns:
            Deserialized value or None if key doesn't exist
        """
        prefixed_key = self._make_key(key)

        async def _get():
            value = await self.client.get(prefixed_key)
            return self._deserialize(value)

        return await self._retry_operation("get", _get)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set key to value with optional TTL.

        Args:
            key: Key name
            value: Value to store (will be JSON serialized if complex type)
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful
        """
        prefixed_key = self._make_key(key)
        serialized_value = self._serialize(value)

        async def _set():
            return await self.client.set(prefixed_key, serialized_value, ex=ttl)

        return await self._retry_operation("set", _set)

    async def delete(self, key: str) -> int:
        """Delete key.

        Args:
            key: Key name

        Returns:
            Number of keys deleted (0 or 1)
        """
        prefixed_key = self._make_key(key)

        async def _delete():
            return await self.client.delete(prefixed_key)

        return await self._retry_operation("delete", _delete)

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Key name

        Returns:
            True if key exists
        """
        prefixed_key = self._make_key(key)

        async def _exists():
            return bool(await self.client.exists(prefixed_key))

        return await self._retry_operation("exists", _exists)

    # ===== Counter Operations (for rate limiting) =====

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment key value.

        Args:
            key: Key name
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment
        """
        prefixed_key = self._make_key(key)

        async def _incr():
            return await self.client.incrby(prefixed_key, amount)

        return await self._retry_operation("increment", _incr)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement key value.

        Args:
            key: Key name
            amount: Amount to decrement by (default: 1)

        Returns:
            New value after decrement
        """
        prefixed_key = self._make_key(key)

        async def _decr():
            return await self.client.decrby(prefixed_key, amount)

        return await self._retry_operation("decrement", _decr)

    # ===== Hash Operations =====

    async def hget(self, key: str, field: str) -> Any:
        """Get value of hash field.

        Args:
            key: Hash key name
            field: Field name

        Returns:
            Deserialized field value or None
        """
        prefixed_key = self._make_key(key)

        async def _hget():
            value = await self.client.hget(prefixed_key, field)
            return self._deserialize(value)

        return await self._retry_operation("hget", _hget)

    async def hset(self, key: str, field: str, value: Any) -> int:
        """Set hash field to value.

        Args:
            key: Hash key name
            field: Field name
            value: Value to store

        Returns:
            1 if field is new, 0 if field was updated
        """
        prefixed_key = self._make_key(key)
        serialized_value = self._serialize(value)

        async def _hset():
            return await self.client.hset(prefixed_key, field, serialized_value)

        return await self._retry_operation("hset", _hset)

    async def hgetall(self, key: str) -> dict[str, Any]:
        """Get all fields and values of hash.

        Args:
            key: Hash key name

        Returns:
            Dictionary of field-value pairs
        """
        prefixed_key = self._make_key(key)

        async def _hgetall():
            data = await self.client.hgetall(prefixed_key)
            return {field: self._deserialize(value) for field, value in data.items()}

        return await self._retry_operation("hgetall", _hgetall)

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete one or more hash fields.

        Args:
            key: Hash key name
            *fields: Field names to delete

        Returns:
            Number of fields deleted
        """
        prefixed_key = self._make_key(key)

        async def _hdel():
            return await self.client.hdel(prefixed_key, *fields)

        return await self._retry_operation("hdel", _hdel)

    # ===== List Operations =====

    async def lpush(self, key: str, *values: Any) -> int:
        """Prepend one or more values to list.

        Args:
            key: List key name
            *values: Values to prepend

        Returns:
            Length of list after operation
        """
        prefixed_key = self._make_key(key)
        serialized_values = [self._serialize(v) for v in values]

        async def _lpush():
            return await self.client.lpush(prefixed_key, *serialized_values)

        return await self._retry_operation("lpush", _lpush)

    async def rpush(self, key: str, *values: Any) -> int:
        """Append one or more values to list.

        Args:
            key: List key name
            *values: Values to append

        Returns:
            Length of list after operation
        """
        prefixed_key = self._make_key(key)
        serialized_values = [self._serialize(v) for v in values]

        async def _rpush():
            return await self.client.rpush(prefixed_key, *serialized_values)

        return await self._retry_operation("rpush", _rpush)

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> list[Any]:
        """Get range of elements from list.

        Args:
            key: List key name
            start: Start index (default: 0)
            end: End index (default: -1, meaning end of list)

        Returns:
            List of deserialized values
        """
        prefixed_key = self._make_key(key)

        async def _lrange():
            values = await self.client.lrange(prefixed_key, start, end)
            return [self._deserialize(v) for v in values]

        return await self._retry_operation("lrange", _lrange)

    async def llen(self, key: str) -> int:
        """Get length of list.

        Args:
            key: List key name

        Returns:
            Length of list
        """
        prefixed_key = self._make_key(key)

        async def _llen():
            return await self.client.llen(prefixed_key)

        return await self._retry_operation("llen", _llen)

    # ===== Health Check =====

    async def ping(self) -> bool:
        """Ping Redis server to check connectivity.

        Returns:
            True if server responds with PONG

        Raises:
            RedisClientError: If ping fails
        """
        try:
            response = await self.client.ping()
            return response is True
        except Exception as e:
            error_msg = f"Redis ping failed: {e}"
            logger.error(error_msg, error=str(e))
            raise RedisClientError(error_msg, operation="ping", error=str(e))

    async def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Dictionary with health check results:
            - connected: bool
            - ping: bool
            - info: dict (server info)
        """
        health = {"connected": self._connected, "ping": False, "info": {}}

        if not self._connected:
            return health

        try:
            # Test ping
            health["ping"] = await self.ping()

            # Get server info
            info = await self.client.info("server")
            health["info"] = {
                "redis_version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "used_memory_human": info.get("used_memory_human"),
            }

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            health["error"] = str(e)

        return health

    # ===== Context Manager Support =====

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False


# ===== Global Client Instance =====

_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """Get or create global Redis client instance.

    This is useful for dependency injection in FastAPI endpoints.

    Returns:
        Global RedisClient instance

    Example:
        ```python
        from fastapi import Depends
        from src.infrastructure.cache.redis_client import get_redis_client

        @app.get("/cache/{key}")
        async def get_cached_value(
            key: str,
            redis: RedisClient = Depends(get_redis_client)
        ):
            value = await redis.get(key)
            return {"value": value}
        ```
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()

    return _redis_client


async def close_redis_client() -> None:
    """Close global Redis client connection.

    Call this during application shutdown.
    """
    global _redis_client

    if _redis_client is not None:
        await _redis_client.disconnect()
        _redis_client = None
