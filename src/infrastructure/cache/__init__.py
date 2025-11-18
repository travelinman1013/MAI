"""Cache infrastructure module.

Provides Redis-based caching functionality with:
- Async Redis client wrapper
- Connection pooling
- JSON serialization
- Key prefix support
- Retry logic
"""

from src.infrastructure.cache.redis_client import (
    RedisClient,
    RedisClientError,
    get_redis_client,
    close_redis_client,
)

__all__ = [
    "RedisClient",
    "RedisClientError",
    "get_redis_client",
    "close_redis_client",
]
