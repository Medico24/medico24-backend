"""Redis client configuration and utilities."""

import json
from typing import Any, cast

import redis

from app.config import settings

# Global Redis client instance
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            username=settings.redis_username,
            password=settings.redis_password,
            decode_responses=settings.redis_decode_responses,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )

    return _redis_client


async def check_redis_connection() -> bool:
    """
    Check if Redis connection is healthy.

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception:
        return False


def close_redis_connection() -> None:
    """Close Redis connection."""
    global _redis_client

    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


# Rate limiting helper
class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize rate limiter with Redis client."""
        self.redis = redis_client

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int = 60,
    ) -> bool:
        """
        Check if rate limit is exceeded.

        Args:
            key: Rate limit key (e.g., user_id or IP)
            limit: Maximum number of requests
            window: Time window in seconds

        Returns:
            True if within limit, False if exceeded
        """
        try:
            current = cast(str | None, self.redis.get(key))

            if current is None:
                # First request
                self.redis.setex(key, window, 1)
                return True

            current_count = int(current)

            if current_count >= limit:
                return False

            # Increment counter
            self.redis.incr(key)
            return True
        except Exception:
            # On error, allow request (fail open)
            return True


# Cache helpers
class CacheManager:
    """Redis-based cache manager."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize cache manager with Redis client."""
        self.redis = redis_client

    def get(self, key: str) -> str | None:
        """Get value from cache."""
        try:
            return cast(str | None, self.redis.get(key))
        except Exception:
            return None

    def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if ttl:
                self.redis.setex(key, ttl, value)
            else:
                self.redis.set(key, value)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            self.redis.delete(key)
            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis.exists(key))
        except Exception:
            return False

    def get_json(self, key: str) -> Any | None:
        """
        Get JSON value from cache and deserialize.

        Args:
            key: Cache key

        Returns:
            Deserialized object or None
        """
        try:
            value = cast(str | None, self.redis.get(key))
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    def set_json(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Serialize and set JSON value in cache.

        Args:
            key: Cache key
            value: Value to serialize and cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            json_value = json.dumps(value, default=str)
            if ttl:
                self.redis.setex(key, ttl, json_value)
            else:
                self.redis.set(key, json_value)
            return True
        except Exception:
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., 'user:*')

        Returns:
            Number of keys deleted
        """
        try:
            keys = cast(list[str], self.redis.keys(pattern))
            if keys:
                return cast(int, self.redis.delete(*keys))
            return 0
        except Exception:
            return 0
