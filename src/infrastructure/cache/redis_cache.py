"""Redis cache layer for caching queries and results."""

import json
import redis
from typing import Optional, Any
from datetime import timedelta


class RedisCache:
    """Simple Redis cache wrapper."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 1):
        """
        Initialize Redis connection.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number (0 is for Celery, use 1 for cache)
        """
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
        )

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = self.redis.get(key)
            if value is None:
                return None

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except redis.RedisError as e:
            print(f"Redis GET error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)

            if ttl:
                return self.redis.setex(key, ttl, value)
            else:
                return self.redis.set(key, value)

        except redis.RedisError as e:
            print(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            return bool(self.redis.delete(key))
        except redis.RedisError as e:
            print(f"Redis DELETE error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., "tenant:1:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except redis.RedisError as e:
            print(f"Redis DELETE_PATTERN error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            return bool(self.redis.exists(key))
        except redis.RedisError as e:
            print(f"Redis EXISTS error: {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration on existing key.

        Args:
            key: Cache key
            seconds: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            return bool(self.redis.expire(key, seconds))
        except redis.RedisError as e:
            print(f"Redis EXPIRE error: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value or None if error
        """
        try:
            return self.redis.incrby(key, amount)
        except redis.RedisError as e:
            print(f"Redis INCREMENT error: {e}")
            return None

    def flush_all(self) -> bool:
        """
        Clear entire cache database.

        WARNING: This will delete ALL keys in the current database.

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.redis.flushdb()
        except redis.RedisError as e:
            print(f"Redis FLUSH error: {e}")
            return False


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Get global cache instance.

    Returns:
        RedisCache instance
    """
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


# =============================================================================
# Cache Key Builders
# =============================================================================


def build_tenant_key(tenant_id: int, suffix: str) -> str:
    """Build cache key for tenant-scoped data."""
    return f"tenant:{tenant_id}:{suffix}"


def build_contact_key(tenant_id: int, contact_id: int) -> str:
    """Build cache key for contact."""
    return f"tenant:{tenant_id}:contact:{contact_id}"


def build_campaign_key(tenant_id: int, campaign_id: int) -> str:
    """Build cache key for campaign."""
    return f"tenant:{tenant_id}:campaign:{campaign_id}"


def build_template_key(tenant_id: int, template_id: int) -> str:
    """Build cache key for template."""
    return f"tenant:{tenant_id}:template:{template_id}"


def build_stats_key(tenant_id: int, stat_type: str) -> str:
    """Build cache key for statistics."""
    return f"tenant:{tenant_id}:stats:{stat_type}"


# =============================================================================
# Common Cache Durations (in seconds)
# =============================================================================

CACHE_TTL_1_MINUTE = 60
CACHE_TTL_5_MINUTES = 300
CACHE_TTL_15_MINUTES = 900
CACHE_TTL_1_HOUR = 3600
CACHE_TTL_1_DAY = 86400
