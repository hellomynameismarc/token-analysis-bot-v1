import os
import json
import hashlib
from typing import Optional, Any

import redis.asyncio as redis


class CacheError(Exception):
    """Raised when cache operations fail."""


class RedisCache:
    """Async Redis wrapper for caching API responses with TTL."""

    def __init__(self, redis_url: Optional[str] = None):
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._client = redis.from_url(url, decode_responses=True)

    async def close(self) -> None:
        await self._client.aclose()

    def _make_key(self, namespace: str, params: dict) -> str:
        """Create cache key from namespace and sorted params."""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{namespace}:{hash_suffix}"

    async def get(self, namespace: str, params: dict) -> Optional[dict]:
        """Get cached value or None if not found/expired."""
        try:
            key = self._make_key(namespace, params)
            cached = await self._client.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            return None  # Cache miss on any error

    async def set(self, namespace: str, params: dict, value: dict, ttl_seconds: int = 300) -> None:
        """Cache value with TTL (default 5 minutes)."""
        try:
            key = self._make_key(namespace, params)
            await self._client.setex(key, ttl_seconds, json.dumps(value))
        except Exception:
            pass  # Fail silently on cache errors


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Return the global cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


async def cached_request(
    namespace: str,
    params: dict,
    fetch_func,
    ttl_seconds: int = 300,
) -> dict:
    """Helper for cache-or-fetch pattern."""
    cache = get_cache()
    
    # Try cache first
    cached = await cache.get(namespace, params)
    if cached is not None:
        return cached
    
    # Cache miss - fetch fresh data
    result = await fetch_func()
    await cache.set(namespace, params, result, ttl_seconds)
    return result 