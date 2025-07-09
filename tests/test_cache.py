"""
Tests for cache utilities and helper functions.

Tests the InMemoryCache, RedisCache, and HybridCache classes
with various scenarios including TTL, eviction, and fallback behavior.
"""

import pytest
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
import redis.asyncio as redis

from core.cache import (
    InMemoryCache,
    RedisCache,
    HybridCache,
    get_cache,
    cached_request,
    CacheError
)


class TestInMemoryCache:
    """Test the InMemoryCache class."""
    
    @pytest.fixture
    def cache(self):
        """Create an InMemoryCache instance."""
        return InMemoryCache(max_size=10)
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        await cache.set(namespace, params, value, ttl_seconds=300)
        result = await cache.get(namespace, params)
        
        assert result == value
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """Test getting a non-existent key."""
        namespace = "test"
        params = {"key": "value"}
        
        result = await cache.get(namespace, params)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache):
        """Test that cached values expire after TTL."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Set with very short TTL
        await cache.set(namespace, params, value, ttl_seconds=0.1)
        
        # Should be available immediately
        result = await cache.get(namespace, params)
        assert result == value
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        result = await cache.get(namespace, params)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_eviction(self, cache):
        """Test that cache evicts oldest entries when full."""
        # Fill cache to capacity
        for i in range(10):
            namespace = f"test{i}"
            params = {"key": f"value{i}"}
            value = {"result": f"data{i}"}
            await cache.set(namespace, params, value)
        
        # Add one more entry
        await cache.set("test11", {"key": "value11"}, {"result": "data11"})
        
        # First entry should be evicted
        result = await cache.get("test0", {"key": "value0"})
        assert result is None
        
        # Last entry should still be available
        result = await cache.get("test11", {"key": "value11"})
        assert result == {"result": "data11"}
    
    @pytest.mark.asyncio
    async def test_lru_behavior(self, cache):
        """Test LRU (Least Recently Used) behavior."""
        # Create a cache with size 2 for this test
        small_cache = InMemoryCache(max_size=2)
        
        # Add two entries
        await small_cache.set("test1", {"key": "value1"}, {"result": "data1"})
        await small_cache.set("test2", {"key": "value2"}, {"result": "data2"})
        
        # Access first entry (should move to end)
        await small_cache.get("test1", {"key": "value1"})
        
        # Add third entry (should evict second entry)
        await small_cache.set("test3", {"key": "value3"}, {"result": "data3"})
        
        # First entry should still be available
        result = await small_cache.get("test1", {"key": "value1"})
        assert result == {"result": "data1"}
        
        # Second entry should be evicted
        result = await small_cache.get("test2", {"key": "value2"})
        assert result is None
        
        await small_cache.close()
    
    @pytest.mark.asyncio
    async def test_key_generation(self, cache):
        """Test that cache keys are generated consistently."""
        namespace = "test"
        params1 = {"key": "value", "order": 1}
        params2 = {"order": 1, "key": "value"}  # Same params, different order
        value = {"result": "data"}
        
        # Set with first params
        await cache.set(namespace, params1, value)
        
        # Get with second params (should work due to sorted keys)
        result = await cache.get(namespace, params2)
        assert result == value
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache):
        """Test automatic cleanup of expired entries."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Set with very short TTL
        await cache.set(namespace, params, value, ttl_seconds=0.1)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Get should trigger cleanup and return None
        result = await cache.get(namespace, params)
        assert result is None
        
        # Cache should be empty after cleanup
        assert len(cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_close(self, cache):
        """Test cache cleanup on close."""
        # Add some data
        await cache.set("test", {"key": "value"}, {"result": "data"})
        assert len(cache._cache) > 0
        
        # Close cache
        await cache.close()
        
        # Cache should be empty
        assert len(cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, cache):
        """Test that exceptions are handled gracefully."""
        # Mock _make_key to raise exception
        with patch.object(cache, '_make_key', side_effect=Exception("Key error")):
            result = await cache.get("test", {"key": "value"})
            assert result is None
        
        # Mock _cleanup_expired to raise exception
        with patch.object(cache, '_cleanup_expired', side_effect=Exception("Cleanup error")):
            result = await cache.get("test", {"key": "value"})
            assert result is None


class TestRedisCache:
    """Test the RedisCache class."""
    
    @pytest.fixture
    def redis_cache(self):
        """Create a RedisCache instance with mocked Redis client."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=redis.Redis)
            mock_from_url.return_value = mock_client
            cache = RedisCache("redis://localhost:6379")
            cache._client = mock_client
            return cache
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_cache):
        """Test basic set and get operations."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Mock Redis responses
        redis_cache._client.setex = AsyncMock(return_value=True)
        redis_cache._client.get = AsyncMock(return_value=json.dumps(value))
        
        await redis_cache.set(namespace, params, value, ttl_seconds=300)
        result = await redis_cache.get(namespace, params)
        
        assert result == value
        redis_cache._client.setex.assert_called_once()
        redis_cache._client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, redis_cache):
        """Test getting a non-existent key."""
        namespace = "test"
        params = {"key": "value"}
        
        # Mock Redis returning None
        redis_cache._client.get.return_value = None
        
        result = await redis_cache.get(namespace, params)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_redis_unavailable(self, redis_cache):
        """Test behavior when Redis is unavailable."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Mock Redis exception
        redis_cache._client.setex.side_effect = Exception("Redis error")
        
        # Should not raise exception
        await redis_cache.set(namespace, params, value)
        
        # Should be marked as unavailable
        assert redis_cache._available is False
        
        # Subsequent calls should return None
        result = await redis_cache.get(namespace, params)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_json_serialization(self, redis_cache):
        """Test JSON serialization of cached values."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data", "number": 42, "boolean": True}
        
        # Mock Redis responses
        redis_cache._client.setex = AsyncMock(return_value=True)
        redis_cache._client.get = AsyncMock(return_value=json.dumps(value))
        
        await redis_cache.set(namespace, params, value)
        result = await redis_cache.get(namespace, params)
        
        assert result == value
    
    @pytest.mark.asyncio
    async def test_close(self, redis_cache):
        """Test Redis connection cleanup."""
        await redis_cache.close()
        redis_cache._client.aclose.assert_called_once()


class TestHybridCache:
    """Test the HybridCache class."""
    
    @pytest.fixture
    def hybrid_cache(self):
        """Create a HybridCache instance with mocked Redis."""
        with patch('core.cache.RedisCache') as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis_class.return_value = mock_redis
            cache = HybridCache(use_redis=True)
            return cache
    
    @pytest.mark.asyncio
    async def test_redis_available(self, hybrid_cache):
        """Test behavior when Redis is available."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Mock Redis returning cached value
        hybrid_cache._redis_cache.get.return_value = value
        
        result = await hybrid_cache.get(namespace, params)
        
        assert result == value
        hybrid_cache._redis_cache.get.assert_called_once_with(namespace, params)
        # Should not fall back to memory cache
        assert len(hybrid_cache._memory_cache._cache) == 0
    
    @pytest.mark.asyncio
    async def test_redis_unavailable_fallback(self, hybrid_cache):
        """Test fallback to memory cache when Redis is unavailable."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Mock Redis returning None
        hybrid_cache._redis_cache.get.return_value = None
        
        # Set in memory cache
        await hybrid_cache._memory_cache.set(namespace, params, value)
        
        result = await hybrid_cache.get(namespace, params)
        
        assert result == value
        hybrid_cache._redis_cache.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_exception_fallback(self, hybrid_cache):
        """Test fallback when Redis raises exception."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Mock Redis exception
        hybrid_cache._redis_cache.get.side_effect = Exception("Redis error")
        
        # Set in memory cache
        await hybrid_cache._memory_cache.set(namespace, params, value)
        
        result = await hybrid_cache.get(namespace, params)
        
        assert result == value
        # Should be marked as unavailable
        assert hybrid_cache._use_redis is False
    
    @pytest.mark.asyncio
    async def test_set_both_caches(self, hybrid_cache):
        """Test that values are set in both Redis and memory."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        await hybrid_cache.set(namespace, params, value, ttl_seconds=300)
        
        # Should be set in Redis
        hybrid_cache._redis_cache.set.assert_called_once_with(
            namespace, params, value, 300
        )
        
        # Should be set in memory
        result = await hybrid_cache._memory_cache.get(namespace, params)
        assert result == value
    
    @pytest.mark.asyncio
    async def test_set_redis_unavailable(self, hybrid_cache):
        """Test set behavior when Redis is unavailable."""
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        # Mock Redis exception
        hybrid_cache._redis_cache.set.side_effect = Exception("Redis error")
        
        await hybrid_cache.set(namespace, params, value)
        
        # Should be marked as unavailable
        assert hybrid_cache._use_redis is False
        
        # Should still be set in memory
        result = await hybrid_cache._memory_cache.get(namespace, params)
        assert result == value
    
    @pytest.mark.asyncio
    async def test_memory_only_mode(self):
        """Test behavior when Redis is disabled."""
        cache = HybridCache(use_redis=False)
        
        namespace = "test"
        params = {"key": "value"}
        value = {"result": "data"}
        
        await cache.set(namespace, params, value)
        result = await cache.get(namespace, params)
        
        assert result == value
        assert cache._redis_cache is None
    
    @pytest.mark.asyncio
    async def test_close(self, hybrid_cache):
        """Test cleanup of both caches."""
        await hybrid_cache.close()
        
        # Should close Redis cache
        hybrid_cache._redis_cache.close.assert_called_once()
        
        # Should close memory cache
        assert len(hybrid_cache._memory_cache._cache) == 0


class TestCacheFunctions:
    """Test the global cache functions."""
    
    @pytest.mark.asyncio
    async def test_get_cache(self):
        """Test the get_cache function."""
        # Clear any existing cache
        import core.cache
        core.cache._cache = None
        
        cache = get_cache()
        assert isinstance(cache, HybridCache)
        
        # Second call should return same instance
        cache2 = get_cache()
        assert cache is cache2
    
    @pytest.mark.asyncio
    async def test_cached_request(self):
        """Test the cached_request function."""
        namespace = "test"
        params = {"key": "value"}
        expected_value = {"result": "data"}
        
        # Mock fetch function
        async def mock_fetch():
            return expected_value
        
        # Mock cache
        mock_cache = AsyncMock()
        mock_cache.get.return_value = expected_value
        
        with patch('core.cache.get_cache', return_value=mock_cache):
            result = await cached_request(namespace, params, mock_fetch)
        
        assert result == expected_value
        mock_cache.get.assert_called_once_with(namespace, params)
    
    @pytest.mark.asyncio
    async def test_cached_request_cache_miss(self):
        """Test cached_request when cache misses."""
        namespace = "test"
        params = {"key": "value"}
        expected_value = {"result": "data"}
        
        # Mock fetch function
        async def mock_fetch():
            return expected_value
        
        # Mock cache returning None (cache miss)
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        
        with patch('core.cache.get_cache', return_value=mock_cache):
            result = await cached_request(namespace, params, mock_fetch)
        
        assert result == expected_value
        mock_cache.get.assert_called_once_with(namespace, params)
        mock_cache.set.assert_called_once_with(namespace, params, expected_value, 300)
    
    @pytest.mark.asyncio
    async def test_cached_request_custom_ttl(self):
        """Test cached_request with custom TTL."""
        namespace = "test"
        params = {"key": "value"}
        expected_value = {"result": "data"}
        custom_ttl = 600
        
        # Mock fetch function
        async def mock_fetch():
            return expected_value
        
        # Mock cache returning None (cache miss)
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        
        with patch('core.cache.get_cache', return_value=mock_cache):
            result = await cached_request(namespace, params, mock_fetch, ttl_seconds=custom_ttl)
        
        assert result == expected_value
        mock_cache.set.assert_called_once_with(namespace, params, expected_value, custom_ttl) 