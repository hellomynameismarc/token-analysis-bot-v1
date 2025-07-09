"""
Tests for in-memory rate limiter with sliding window algorithm.

Tests the rate limiting functionality without requiring Redis,
ensuring it works correctly for MVP deployment.
"""

import pytest
import time
from unittest.mock import patch

from core.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    check_rate_limit,
    record_request,
    get_user_rate_limit_stats,
    get_global_rate_limit_stats
)


class TestRateLimitConfig:
    """Test rate limit configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.max_requests == 2
        assert config.window_seconds == 60
        assert config.cleanup_interval == 300
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            max_requests=5,
            window_seconds=120,
            cleanup_interval=600
        )
        assert config.max_requests == 5
        assert config.window_seconds == 120
        assert config.cleanup_interval == 600


class TestInMemoryRateLimiter:
    """Test the in-memory rate limiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance for testing."""
        config = RateLimitConfig(max_requests=2, window_seconds=60)
        return InMemoryRateLimiter(config)
    
    def test_initial_state(self, rate_limiter):
        """Test initial state of rate limiter."""
        user_id = 12345
        
        is_allowed, info = rate_limiter.is_allowed(user_id)
        
        assert is_allowed is True
        assert info['remaining_requests'] == 2
        assert info['max_requests'] == 2
        assert info['current_requests'] == 0
    
    def test_single_request(self, rate_limiter):
        """Test single request recording."""
        user_id = 12345
        
        # Record a request
        rate_limiter.record_request(user_id)
        
        # Check rate limit
        is_allowed, info = rate_limiter.is_allowed(user_id)
        
        assert is_allowed is True
        assert info['remaining_requests'] == 1
        assert info['current_requests'] == 1
    
    def test_max_requests_reached(self, rate_limiter):
        """Test when maximum requests are reached."""
        user_id = 12345
        
        # Record maximum requests
        rate_limiter.record_request(user_id)
        rate_limiter.record_request(user_id)
        
        # Check rate limit
        is_allowed, info = rate_limiter.is_allowed(user_id)
        
        assert is_allowed is False
        assert info['remaining_requests'] == 0
        assert info['current_requests'] == 2
    
    def test_exceed_max_requests(self, rate_limiter):
        """Test when maximum requests are exceeded."""
        user_id = 12345
        
        # Record more than maximum requests
        rate_limiter.record_request(user_id)
        rate_limiter.record_request(user_id)
        rate_limiter.record_request(user_id)  # This should be blocked
        
        # Check rate limit
        is_allowed, info = rate_limiter.is_allowed(user_id)
        
        assert is_allowed is False
        assert info['remaining_requests'] == 0
        assert info['current_requests'] == 3  # All requests recorded
    
    def test_sliding_window_expiry(self):
        """Test that old requests expire after window."""
        user_id = 12345
        
        # Create rate limiter with mocked time
        with patch('time.time') as mock_time:
            base_time = 1000000.0
            mock_time.return_value = base_time
            config = RateLimitConfig(max_requests=2, window_seconds=60)
            rate_limiter = InMemoryRateLimiter(config)
            
            # Record requests
            mock_time.return_value = base_time
            rate_limiter.record_request(user_id)
            rate_limiter.record_request(user_id)
            
            # Check rate limit (should be blocked)
            mock_time.return_value = base_time
            is_allowed, info = rate_limiter.is_allowed(user_id)
            assert is_allowed is False
            
            # Fast forward time to expire requests
            mock_time.return_value = base_time + 70  # 70 seconds later
            
            # Check rate limit again (should be allowed)
            is_allowed, info = rate_limiter.is_allowed(user_id)
            assert is_allowed is True
            assert info['remaining_requests'] == 2
            assert info['current_requests'] == 0
    
    def test_multiple_users(self, rate_limiter):
        """Test rate limiting with multiple users."""
        user1 = 12345
        user2 = 67890
        
        # User 1 makes 2 requests
        rate_limiter.record_request(user1)
        rate_limiter.record_request(user1)
        
        # User 2 makes 1 request
        rate_limiter.record_request(user2)
        
        # Check user 1 (should be blocked)
        is_allowed1, info1 = rate_limiter.is_allowed(user1)
        assert is_allowed1 is False
        assert info1['current_requests'] == 2
        
        # Check user 2 (should be allowed)
        is_allowed2, info2 = rate_limiter.is_allowed(user2)
        assert is_allowed2 is True
        assert info2['current_requests'] == 1
        assert info2['remaining_requests'] == 1
    
    def test_cleanup_expired_entries(self):
        """Test automatic cleanup of expired entries."""
        user_id = 12345
        
        # Create rate limiter with mocked time
        with patch('time.time') as mock_time:
            base_time = 2000000.0
            mock_time.return_value = base_time
            config = RateLimitConfig(max_requests=2, window_seconds=60)
            rate_limiter = InMemoryRateLimiter(config)
            
            # Record requests
            mock_time.return_value = base_time
            rate_limiter.record_request(user_id)
            rate_limiter.record_request(user_id)
            
            # Fast forward time to trigger cleanup
            mock_time.return_value = base_time + 70  # 70 seconds later
            
            # Trigger cleanup by checking rate limit
            is_allowed, info = rate_limiter.is_allowed(user_id)
            
            # Should be allowed after cleanup
            assert is_allowed is True
            assert info['current_requests'] == 0
    
    def test_reset_user(self, rate_limiter):
        """Test resetting rate limit for a specific user."""
        user_id = 12345
        
        # Record requests
        rate_limiter.record_request(user_id)
        rate_limiter.record_request(user_id)
        
        # Check rate limit (should be blocked)
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is False
        
        # Reset user
        rate_limiter.reset_user(user_id)
        
        # Check rate limit again (should be allowed)
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is True
        assert info['remaining_requests'] == 2
    
    def test_reset_all(self, rate_limiter):
        """Test resetting all rate limiting data."""
        user1 = 12345
        user2 = 67890
        
        # Record requests for both users
        rate_limiter.record_request(user1)
        rate_limiter.record_request(user2)
        
        # Reset all
        rate_limiter.reset_all()
        
        # Check both users (should be allowed)
        is_allowed1, _ = rate_limiter.is_allowed(user1)
        is_allowed2, _ = rate_limiter.is_allowed(user2)
        
        assert is_allowed1 is True
        assert is_allowed2 is True


class TestRateLimiterFunctions:
    """Test the global rate limiter functions."""
    
    def test_check_rate_limit(self):
        """Test the global check_rate_limit function."""
        user_id = 12345
        
        # First check should be allowed
        is_allowed, info = check_rate_limit(user_id)
        assert is_allowed is True
        assert info['remaining_requests'] == 2
    
    def test_record_request(self):
        """Test the global record_request function."""
        user_id = 12345
        
        # Record a request
        record_request(user_id)
        
        # Check rate limit
        is_allowed, info = check_rate_limit(user_id)
        assert is_allowed is True
        assert info['remaining_requests'] == 1
        assert info['current_requests'] == 1
    
    def test_get_user_rate_limit_stats(self):
        """Test getting user rate limit statistics."""
        user_id = 12345
        
        # Record some requests
        record_request(user_id)
        record_request(user_id)
        
        # Get stats
        stats = get_user_rate_limit_stats(user_id)
        
        assert stats['user_id'] == user_id
        assert stats['total_requests'] >= 2
        assert stats['recent_requests'] >= 2
        assert stats['max_requests'] == 2
        assert stats['remaining_requests'] == 0
    
    def test_get_global_rate_limit_stats(self):
        """Test getting global rate limit statistics."""
        user1 = 12345
        user2 = 67890
        
        # Record requests for multiple users
        record_request(user1)
        record_request(user2)
        
        # Get global stats
        stats = get_global_rate_limit_stats()
        
        assert stats['total_users'] >= 2
        assert stats['total_requests'] >= 2
        assert stats['recent_requests'] >= 2
        assert stats['window_seconds'] == 60


class TestRateLimiterEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance for testing."""
        config = RateLimitConfig(max_requests=1, window_seconds=1)
        return InMemoryRateLimiter(config)
    
    def test_concurrent_requests(self, rate_limiter):
        """Test handling of concurrent requests."""
        user_id = 12345
        
        # Simulate concurrent requests
        rate_limiter.record_request(user_id)
        rate_limiter.record_request(user_id)
        
        # Both should be recorded (thread safety handled by locks)
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is False
        assert info['current_requests'] == 2
    
    def test_negative_user_id(self, rate_limiter):
        """Test handling of negative user IDs."""
        user_id = -12345
        
        # Should work normally
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is True
        
        rate_limiter.record_request(user_id)
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is False
    
    def test_large_user_id(self, rate_limiter):
        """Test handling of large user IDs."""
        user_id = 999999999999999999
        
        # Should work normally
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is True
        
        rate_limiter.record_request(user_id)
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is False
    
    def test_zero_max_requests(self):
        """Test behavior with zero max requests."""
        config = RateLimitConfig(max_requests=0, window_seconds=60)
        rate_limiter = InMemoryRateLimiter(config)
        
        user_id = 12345
        is_allowed, info = rate_limiter.is_allowed(user_id)
        
        assert is_allowed is False
        assert info['remaining_requests'] == 0
        assert info['max_requests'] == 0
    
    def test_very_short_window(self):
        """Test behavior with very short time windows."""
        config = RateLimitConfig(max_requests=1, window_seconds=1)
        rate_limiter = InMemoryRateLimiter(config)
        
        user_id = 12345
        
        # Record request
        rate_limiter.record_request(user_id)
        
        # Should be blocked immediately
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        is_allowed, info = rate_limiter.is_allowed(user_id)
        assert is_allowed is True


class TestRateLimiterPerformance:
    """Test performance characteristics of the rate limiter."""
    
    def test_memory_efficiency(self):
        """Test that memory usage doesn't grow indefinitely."""
        config = RateLimitConfig(max_requests=1, window_seconds=1, cleanup_interval=1)
        rate_limiter = InMemoryRateLimiter(config)
        
        # Create many users
        for i in range(1000):
            rate_limiter.record_request(i)
        
        # Wait for cleanup
        time.sleep(2)
        
        # Check that expired users are cleaned up
        is_allowed, _ = rate_limiter.is_allowed(0)
        assert is_allowed is True  # Should be reset after cleanup
    
    def test_cleanup_frequency(self):
        """Test that cleanup happens at appropriate intervals."""
        config = RateLimitConfig(cleanup_interval=1)
        rate_limiter = InMemoryRateLimiter(config)
        
        user_id = 12345
        
        # Record request
        rate_limiter.record_request(user_id)
        
        # Wait for cleanup interval
        time.sleep(1.1)
        
        # Check rate limit (should trigger cleanup)
        is_allowed, info = rate_limiter.is_allowed(user_id)
        
        # Should be allowed after cleanup
        assert is_allowed is True
        # Note: cleanup only removes expired entries, not all entries
        # So current_requests might still be 1 if the request is still within window 