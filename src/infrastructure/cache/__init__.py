"""Cache infrastructure - Redis caching layer."""

from .redis_cache import (
    RedisCache,
    get_cache,
    build_tenant_key,
    build_contact_key,
    build_campaign_key,
    build_template_key,
    build_stats_key,
    CACHE_TTL_1_MINUTE,
    CACHE_TTL_5_MINUTES,
    CACHE_TTL_15_MINUTES,
    CACHE_TTL_1_HOUR,
    CACHE_TTL_1_DAY,
)

__all__ = [
    "RedisCache",
    "get_cache",
    "build_tenant_key",
    "build_contact_key",
    "build_campaign_key",
    "build_template_key",
    "build_stats_key",
    "CACHE_TTL_1_MINUTE",
    "CACHE_TTL_5_MINUTES",
    "CACHE_TTL_15_MINUTES",
    "CACHE_TTL_1_HOUR",
    "CACHE_TTL_1_DAY",
]
