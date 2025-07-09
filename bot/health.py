"""
Health Check Module

Provides health check endpoints for monitoring the bot's status
and basic system information.
"""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from core.rate_limiter import get_global_rate_limit_stats


@dataclass
class HealthStatus:
    """Health status information."""
    status: str
    timestamp: float
    uptime_seconds: float
    version: str
    environment: str
    cache_status: str
    rate_limit_stats: Dict[str, Any]
    memory_usage: Dict[str, Any]
    monitoring_stats: Dict[str, Any]


class HealthChecker:
    """Health check service for monitoring bot status."""
    
    def __init__(self, start_time: float):
        """Initialize health checker with start time."""
        self.start_time = start_time
        self.version = "1.0.0"
        self.environment = "production"
    
    def get_health_status(self) -> HealthStatus:
        """Get current health status."""
        import psutil
        
        # Get uptime
        uptime = time.time() - self.start_time
        
        # Get memory usage
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_usage = {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2)
        }
        
        # Get rate limit stats
        try:
            rate_limit_stats = get_global_rate_limit_stats()
        except Exception:
            rate_limit_stats = {"error": "Unable to fetch rate limit stats"}
        
        # Determine cache status
        try:
            from core.cache import get_cache_status
            cache_status = get_cache_status()
        except ImportError:
            cache_status = "unknown"
        except Exception:
            cache_status = "error"
        
        # Get monitoring status
        try:
            from core.monitoring import get_monitoring_manager
            monitoring_stats = get_monitoring_manager().get_stats()
        except ImportError:
            monitoring_stats = {"sentry_available": False, "sentry_initialized": False}
        except Exception:
            monitoring_stats = {"sentry_available": False, "sentry_initialized": False}
        
        return HealthStatus(
            status="healthy",
            timestamp=time.time(),
            uptime_seconds=uptime,
            version=self.version,
            environment=self.environment,
            cache_status=cache_status,
            rate_limit_stats=rate_limit_stats,
            memory_usage=memory_usage,
            monitoring_stats=monitoring_stats
        )
    
    def get_health_response(self) -> str:
        """Get health check response as JSON string."""
        status = self.get_health_status()
        return json.dumps(asdict(status), indent=2)
    
    def is_healthy(self) -> bool:
        """Check if the system is healthy."""
        try:
            status = self.get_health_status()
            
            # Basic health checks
            if status.status != "healthy":
                return False
            
            # Memory usage check (warn if > 500MB)
            if status.memory_usage["rss_mb"] > 500:
                return False
            
            # Uptime check (should be > 0)
            if status.uptime_seconds <= 0:
                return False
            
            return True
            
        except Exception:
            return False


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def initialize_health_checker():
    """Initialize the global health checker."""
    global _health_checker
    _health_checker = HealthChecker(time.time())


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    if _health_checker is None:
        initialize_health_checker()
    assert _health_checker is not None  # Type guard
    return _health_checker


def get_health_response() -> str:
    """Get health check response."""
    return get_health_checker().get_health_response()


def is_healthy() -> bool:
    """Check if the system is healthy."""
    return get_health_checker().is_healthy() 