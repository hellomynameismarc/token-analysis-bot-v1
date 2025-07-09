"""
In-memory rate limiter with sliding window algorithm.

Provides rate limiting functionality without requiring Redis,
suitable for MVP deployment with zero infrastructure costs.
"""

import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 2
    window_seconds: int = 60
    cleanup_interval: int = 300  # Clean up old entries every 5 minutes


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    
    Features:
    - Sliding window rate limiting
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - Memory-efficient storage
    - No external dependencies
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._user_requests: Dict[int, List[float]] = defaultdict(list)
        self._global_requests: List[float] = []
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
    
    def _cleanup_expired_entries(self) -> None:
        """Remove expired request timestamps to prevent memory bloat."""
        current_time = time.time()
        cutoff_time = current_time - self.config.window_seconds
        
        # Clean up user requests
        expired_users = []
        for user_id, requests in self._user_requests.items():
            # Keep only requests within the window
            self._user_requests[user_id] = [
                req_time for req_time in requests
                if req_time > cutoff_time
            ]
            # Remove user if no requests remain
            if not self._user_requests[user_id]:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self._user_requests[user_id]
        
        # Clean up global requests
        self._global_requests = [
            req_time for req_time in self._global_requests
            if req_time > cutoff_time
        ]
        
        self._last_cleanup = current_time
    
    def _should_cleanup(self) -> bool:
        """Check if cleanup is needed."""
        return time.time() - self._last_cleanup > self.config.cleanup_interval
    
    def is_allowed(self, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a user is allowed to make a request.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self._lock:
            if self._should_cleanup():
                self._cleanup_expired_entries()
            
            current_time = time.time()
            cutoff_time = current_time - self.config.window_seconds
            
            # Get user's recent requests
            user_requests = self._user_requests[user_id]
            
            # Remove expired requests
            recent_requests = [
                req_time for req_time in user_requests
                if req_time > cutoff_time
            ]
            
            # Check if user has exceeded the limit
            is_allowed = len(recent_requests) < self.config.max_requests
            
            # Calculate rate limit info
            remaining_requests = max(0, self.config.max_requests - len(recent_requests))
            reset_time = None
            
            if recent_requests:
                # Calculate when the oldest request will expire
                oldest_request = min(recent_requests)
                reset_time = oldest_request + self.config.window_seconds
            
            rate_limit_info = {
                'is_allowed': is_allowed,
                'remaining_requests': remaining_requests,
                'max_requests': self.config.max_requests,
                'window_seconds': self.config.window_seconds,
                'reset_time': reset_time,
                'current_requests': len(recent_requests)
            }
            
            return is_allowed, rate_limit_info
    
    def record_request(self, user_id: int) -> None:
        """
        Record a successful request for rate limiting.
        
        Args:
            user_id: Telegram user ID
        """
        with self._lock:
            current_time = time.time()
            self._user_requests[user_id].append(current_time)
            self._global_requests.append(current_time)
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get rate limiting statistics for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user statistics
        """
        with self._lock:
            if self._should_cleanup():
                self._cleanup_expired_entries()
            
            current_time = time.time()
            cutoff_time = current_time - self.config.window_seconds
            
            user_requests = self._user_requests[user_id]
            recent_requests = [
                req_time for req_time in user_requests
                if req_time > cutoff_time
            ]
            
            return {
                'user_id': user_id,
                'total_requests': len(user_requests),
                'recent_requests': len(recent_requests),
                'max_requests': self.config.max_requests,
                'remaining_requests': max(0, self.config.max_requests - len(recent_requests)),
                'window_seconds': self.config.window_seconds,
                'last_request': max(recent_requests) if recent_requests else None
            }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """
        Get global rate limiting statistics.
        
        Returns:
            Dictionary with global statistics
        """
        with self._lock:
            if self._should_cleanup():
                self._cleanup_expired_entries()
            
            current_time = time.time()
            cutoff_time = current_time - self.config.window_seconds
            
            recent_global_requests = [
                req_time for req_time in self._global_requests
                if req_time > cutoff_time
            ]
            
            return {
                'total_users': len(self._user_requests),
                'total_requests': len(self._global_requests),
                'recent_requests': len(recent_global_requests),
                'window_seconds': self.config.window_seconds,
                'last_request': max(recent_global_requests) if recent_global_requests else None
            }
    
    def reset_user(self, user_id: int) -> None:
        """
        Reset rate limiting for a specific user.
        
        Args:
            user_id: Telegram user ID
        """
        with self._lock:
            if user_id in self._user_requests:
                del self._user_requests[user_id]
    
    def reset_all(self) -> None:
        """Reset all rate limiting data."""
        with self._lock:
            self._user_requests.clear()
            self._global_requests.clear()
            self._last_cleanup = time.time()


# Global rate limiter instance
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


def check_rate_limit(user_id: int) -> Tuple[bool, Dict[str, any]]:
    """
    Check if a user is within rate limits.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Tuple of (is_allowed, rate_limit_info)
    """
    return get_rate_limiter().is_allowed(user_id)


def record_request(user_id: int) -> None:
    """
    Record a successful request for rate limiting.
    
    Args:
        user_id: Telegram user ID
    """
    get_rate_limiter().record_request(user_id)


def get_user_rate_limit_stats(user_id: int) -> Dict[str, any]:
    """
    Get rate limiting statistics for a user.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Dictionary with user statistics
    """
    return get_rate_limiter().get_user_stats(user_id)


def get_global_rate_limit_stats() -> Dict[str, any]:
    """
    Get global rate limiting statistics.
    
    Returns:
        Dictionary with global statistics
    """
    return get_rate_limiter().get_global_stats() 