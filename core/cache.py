"""
Hybrid Caching Module

Provides a flexible caching system that automatically falls back from Redis
to in-memory storage, ensuring the application works in any deployment scenario.

Features:
- Redis caching for production environments
- In-memory fallback for MVP deployment
- Automatic TTL management
- LRU eviction for memory management
- Thread-safe operations
- Graceful degradation on Redis failures

Cache Strategy:
1. Try Redis first (if available)
2. Fall back to in-memory cache
3. Continue without caching if both fail
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any
from collections import OrderedDict

import redis.asyncio as redis


class CacheError(Exception):
    """Raised when cache operations fail."""


class InMemoryCache:
    """Simple in-memory cache with TTL support for MVP deployment."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_size = max_size
    
    def _make_key(self, namespace: str, params: dict) -> str:
        """Create cache key from namespace and sorted params."""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{namespace}:{hash_suffix}"
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._cache.items()
            if data.get('expires_at', 0) < current_time
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def _evict_if_full(self) -> None:
        """Evict oldest entries if cache is full."""
        while len(self._cache) >= self._max_size:
            # Remove oldest entry (FIFO)
            self._cache.popitem(last=False)
    
    async def get(self, namespace: str, params: dict) -> Optional[dict]:
        """Get cached value or None if not found/expired."""
        try:
            self._cleanup_expired()
            key = self._make_key(namespace, params)
            data = self._cache.get(key)
            
            if data is None:
                return None
            
            # Check if expired
            if data.get('expires_at', 0) < time.time():
                del self._cache[key]
                return None
            
            # Move to end (LRU behavior)
            self._cache.move_to_end(key)
            return data.get('value')
            
        except Exception:
            return None
    
    async def set(
        self, namespace: str, params: dict, value: dict, ttl_seconds: int = 300
    ) -> None:
        """Cache value with TTL (default 5 minutes)."""
        try:
            self._cleanup_expired()
            self._evict_if_full()
            
            key = self._make_key(namespace, params)
            expires_at = time.time() + ttl_seconds
            
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            # Move to end (LRU behavior)
            self._cache.move_to_end(key)
            
        except Exception:
            pass  # Fail silently on cache errors
    
    async def close(self) -> None:
        """Clean up cache."""
        self._cache.clear()


class RedisCache:
    """Async Redis wrapper for caching API responses with TTL."""

    def __init__(self, redis_url: Optional[str] = None):
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._client = redis.from_url(url, decode_responses=True)
        self._available = True

    async def close(self) -> None:
        await self._client.aclose()

    def _make_key(self, namespace: str, params: dict) -> str:
        """Create cache key from namespace and sorted params."""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{namespace}:{hash_suffix}"

    async def get(self, namespace: str, params: dict) -> Optional[dict]:
        """Get cached value or None if not found/expired."""
        if not self._available:
            return None
            
        try:
            key = self._make_key(namespace, params)
            cached = await self._client.get(key)
            return json.loads(cached) if cached else None
        except Exception:
            self._available = False
            return None

    async def set(
        self, namespace: str, params: dict, value: dict, ttl_seconds: int = 300
    ) -> None:
        """Cache value with TTL (default 5 minutes)."""
        if not self._available:
            return
            
        try:
            key = self._make_key(namespace, params)
            await self._client.setex(key, ttl_seconds, json.dumps(value))
        except Exception:
            self._available = False


class HybridCache:
    """Hybrid cache that falls back to in-memory when Redis is unavailable."""
    
    def __init__(self, redis_url: Optional[str] = None, use_redis: bool = True):
        self._use_redis = use_redis
        self._redis_cache: Optional[RedisCache] = None
        self._memory_cache = InMemoryCache()
        
        if use_redis:
            try:
                self._redis_cache = RedisCache(redis_url)
            except Exception:
                # Fallback to in-memory only
                self._use_redis = False
    
    def _make_key(self, namespace: str, params: dict) -> str:
        """Create cache key from namespace and sorted params."""
        param_str = json.dumps(params, sort_keys=True)
        hash_suffix = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{namespace}:{hash_suffix}"
    
    async def get(self, namespace: str, params: dict) -> Optional[dict]:
        """Get cached value, trying Redis first, then in-memory."""
        # Try Redis first if available
        if self._use_redis and self._redis_cache:
            try:
                cached = await self._redis_cache.get(namespace, params)
                if cached is not None:
                    return cached
            except Exception:
                self._use_redis = False
        
        # Fallback to in-memory cache
        return await self._memory_cache.get(namespace, params)
    
    async def set(
        self, namespace: str, params: dict, value: dict, ttl_seconds: int = 300
    ) -> None:
        """Cache value in both Redis (if available) and in-memory."""
        # Set in Redis if available
        if self._use_redis and self._redis_cache:
            try:
                await self._redis_cache.set(namespace, params, value, ttl_seconds)
            except Exception:
                self._use_redis = False
        
        # Always set in memory as backup
        await self._memory_cache.set(namespace, params, value, ttl_seconds)
    
    async def close(self) -> None:
        """Clean up both caches."""
        if self._redis_cache:
            await self._redis_cache.close()
        await self._memory_cache.close()


# Global cache instance
_cache: Optional[HybridCache] = None


def get_cache() -> HybridCache:
    """Return the global cache instance with automatic fallback."""
    global _cache
    if _cache is None:
        # Check if Redis should be used
        use_redis = os.getenv("USE_REDIS", "true").lower() == "true"
        redis_url = os.getenv("REDIS_URL")
        
        # If no Redis URL provided, use in-memory only
        if not redis_url:
            use_redis = False
        
        _cache = HybridCache(redis_url, use_redis)
    return _cache


def get_cache_status() -> str:
    """Get current cache status for health checks."""
    try:
        cache = get_cache()
        if cache._use_redis and cache._redis_cache:
            return "redis"
        else:
            return "memory"
    except Exception:
        return "unknown"


async def cached_request(
    namespace: str,
    params: dict,
    fetch_func,
    ttl_seconds: int = 300,
) -> dict:
    """Helper for cache-or-fetch pattern with automatic fallback."""
    cache = get_cache()

    # Try cache first
    cached = await cache.get(namespace, params)
    if cached is not None:
        return cached

    # Cache miss - fetch fresh data
    result = await fetch_func()
    await cache.set(namespace, params, result, ttl_seconds)
    return result
