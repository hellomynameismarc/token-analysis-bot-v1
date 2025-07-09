"""
Monitoring and Error Tracking Module

Integrates Sentry for error tracking and provides additional monitoring capabilities
for the Token Sentiment Bot.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


class MonitoringManager:
    """Manages monitoring and error tracking for the bot."""
    
    def __init__(self):
        """Initialize monitoring manager."""
        self.sentry_initialized = False
        self.start_time = time.time()
        self.error_count = 0
        self.request_count = 0
        
        # Initialize Sentry if available
        self._init_sentry()
    
    def _init_sentry(self):
        """Initialize Sentry error tracking."""
        if not SENTRY_AVAILABLE:
            logger.warning("Sentry SDK not available. Error tracking disabled.")
            return
        
        sentry_dsn = os.getenv("SENTRY_DSN")
        if not sentry_dsn:
            logger.info("SENTRY_DSN not set. Error tracking disabled.")
            return
        
        try:
            # Configure Sentry
            sentry_logging = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    sentry_logging,
                    HttpxIntegration(),
                    RedisIntegration(),
                ],
                # Performance monitoring
                traces_sample_rate=0.1,  # 10% of transactions
                profiles_sample_rate=0.1,  # 10% of profiles
                
                # Environment
                environment=os.getenv("ENVIRONMENT", "development"),
                release=os.getenv("VERSION", "1.0.0"),
                
                # Before send filter
                before_send=self._before_send,
                
                # Debug mode
                debug=os.getenv("SENTRY_DEBUG", "false").lower() == "true"
            )
            
            self.sentry_initialized = True
            logger.info("Sentry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    def _before_send(self, event, hint):
        """Filter events before sending to Sentry."""
        # Don't send events for certain error types
        if "exception" in hint:
            exc_type = type(hint["exception"]).__name__
            if exc_type in ["KeyboardInterrupt", "SystemExit"]:
                return None
        
        # Add custom context
        event.setdefault("tags", {})
        event["tags"]["service"] = "token-sentiment-bot"
        event["tags"]["component"] = "telegram-bot"
        
        return event
    
    def capture_exception(self, exc_info=None, context: Optional[Dict[str, Any]] = None):
        """Capture an exception with optional context."""
        self.error_count += 1
        
        if self.sentry_initialized:
            try:
                with sentry_sdk.push_scope() as scope:
                    if context:
                        scope.set_context("bot", context)
                    sentry_sdk.capture_exception(exc_info)
            except Exception as e:
                logger.error(f"Failed to capture exception in Sentry: {e}")
        
        # Always log locally
        logger.exception("Exception captured by monitoring")
    
    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
        """Capture a message with optional context."""
        if self.sentry_initialized:
            try:
                with sentry_sdk.push_scope() as scope:
                    if context:
                        scope.set_context("bot", context)
                    sentry_sdk.capture_message(message, level=level)
            except Exception as e:
                logger.error(f"Failed to capture message in Sentry: {e}")
        
        # Always log locally
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, message)
    
    def set_user_context(self, user_id: int, username: Optional[str] = None):
        """Set user context for error tracking."""
        if self.sentry_initialized:
            try:
                sentry_sdk.set_user({
                    "id": str(user_id),
                    "username": username,
                    "service": "telegram-bot"
                })
            except Exception as e:
                logger.error(f"Failed to set user context in Sentry: {e}")
    
    def clear_user_context(self):
        """Clear user context."""
        if self.sentry_initialized:
            try:
                sentry_sdk.set_user(None)
            except Exception as e:
                logger.error(f"Failed to clear user context in Sentry: {e}")
    
    @contextmanager
    def transaction(self, name: str, operation: str = "bot.operation"):
        """Create a performance transaction."""
        if self.sentry_initialized:
            with sentry_sdk.start_transaction(name=name, op=operation) as transaction:
                try:
                    yield transaction
                except Exception as e:
                    transaction.set_status("internal_error")
                    raise
        else:
            yield None
    
    @contextmanager
    def span(self, name: str, operation: str = "bot.span"):
        """Create a performance span."""
        if self.sentry_initialized:
            with sentry_sdk.start_span(name=name, op=operation) as span:
                try:
                    yield span
                except Exception as e:
                    span.set_status("internal_error")
                    raise
        else:
            yield None
    
    def add_breadcrumb(self, message: str, category: str = "bot", level: str = "info", data: Optional[Dict[str, Any]] = None):
        """Add a breadcrumb for debugging."""
        if self.sentry_initialized:
            try:
                sentry_sdk.add_breadcrumb(
                    message=message,
                    category=category,
                    level=level,
                    data=data
                )
            except Exception as e:
                logger.error(f"Failed to add breadcrumb in Sentry: {e}")
    
    def set_tag(self, key: str, value: str):
        """Set a tag for error tracking."""
        if self.sentry_initialized:
            try:
                sentry_sdk.set_tag(key, value)
            except Exception as e:
                logger.error(f"Failed to set tag in Sentry: {e}")
    
    def set_context(self, name: str, data: Dict[str, Any]):
        """Set context data for error tracking."""
        if self.sentry_initialized:
            try:
                sentry_sdk.set_context(name, data)
            except Exception as e:
                logger.error(f"Failed to set context in Sentry: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "error_count": self.error_count,
            "request_count": self.request_count,
            "sentry_initialized": self.sentry_initialized,
            "error_rate": self.error_count / max(self.request_count, 1),
            "sentry_available": SENTRY_AVAILABLE
        }
    
    def record_request(self):
        """Record a request for statistics."""
        self.request_count += 1
    
    def record_error(self):
        """Record an error for statistics."""
        self.error_count += 1


# Global monitoring instance
_monitoring_manager: Optional[MonitoringManager] = None


def get_monitoring_manager() -> MonitoringManager:
    """Get the global monitoring manager instance."""
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager()
    return _monitoring_manager


def init_monitoring():
    """Initialize monitoring globally."""
    get_monitoring_manager()


def capture_exception(exc_info=None, context: Optional[Dict[str, Any]] = None):
    """Capture an exception with optional context."""
    get_monitoring_manager().capture_exception(exc_info, context)


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
    """Capture a message with optional context."""
    get_monitoring_manager().capture_message(message, level, context)


def set_user_context(user_id: int, username: Optional[str] = None):
    """Set user context for error tracking."""
    get_monitoring_manager().set_user_context(user_id, username)


def clear_user_context():
    """Clear user context."""
    get_monitoring_manager().clear_user_context()


@contextmanager
def transaction(name: str, operation: str = "bot.operation"):
    """Create a performance transaction."""
    with get_monitoring_manager().transaction(name, operation) as txn:
        yield txn


@contextmanager
def span(name: str, operation: str = "bot.span"):
    """Create a performance span."""
    with get_monitoring_manager().span(name, operation) as s:
        yield s


def add_breadcrumb(message: str, category: str = "bot", level: str = "info", data: Optional[Dict[str, Any]] = None):
    """Add a breadcrumb for debugging."""
    get_monitoring_manager().add_breadcrumb(message, category, level, data)


def set_tag(key: str, value: str):
    """Set a tag for error tracking."""
    get_monitoring_manager().set_tag(key, value)


def set_context(name: str, data: Dict[str, Any]):
    """Set context data for error tracking."""
    get_monitoring_manager().set_context(name, data) 