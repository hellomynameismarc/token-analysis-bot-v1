"""
Custom Web Server for Token Sentiment Bot

Handles both Telegram webhook requests and health check endpoints
for comprehensive monitoring and deployment compatibility.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response

from telegram import Update
from telegram.ext import Application

from bot.health import initialize_health_checker, get_health_response, is_healthy

logger = logging.getLogger(__name__)


class TokenSentimentWebServer:
    """Custom web server for handling webhooks and health checks."""
    
    def __init__(self, bot_application: Application, webhook_path: str = "/webhook"):
        """Initialize the web server with bot application."""
        self.bot_application = bot_application
        self.webhook_path = webhook_path
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Initialize health checker
        initialize_health_checker()
        
        # Set up routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up web server routes."""
        # Telegram webhook endpoint
        self.app.router.add_post(self.webhook_path, self._handle_webhook)
        
        # Health check endpoints
        self.app.router.add_get("/health", self._handle_health_check)
        self.app.router.add_get("/health/", self._handle_health_check)
        self.app.router.add_get("/healthz", self._handle_health_check)
        self.app.router.add_get("/ready", self._handle_readiness_check)
        self.app.router.add_get("/ready/", self._handle_readiness_check)
        
        # Root endpoint with basic info
        self.app.router.add_get("/", self._handle_root)
        
        # Metrics endpoint (for monitoring)
        self.app.router.add_get("/metrics", self._handle_metrics)
        
        # Error handlers
        self.app.middlewares.append(self._error_middleware)
    
    async def _handle_webhook(self, request: Request) -> Response:
        """Handle Telegram webhook requests."""
        try:
            # Get the update data
            update_data = await request.json()
            
            # Create Update object
            update = Update.de_json(update_data, self.bot_application.bot)
            
            # Process the update
            await self.bot_application.process_update(update)
            
            return web.Response(text="OK", status=200)
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return web.Response(text="Error", status=500)
    
    async def _handle_health_check(self, request: Request) -> Response:
        """Handle health check requests."""
        try:
            # Check if the system is healthy
            healthy = is_healthy()
            
            if healthy:
                return web.Response(
                    text="OK",
                    status=200,
                    headers={"Content-Type": "text/plain"}
                )
            else:
                return web.Response(
                    text="UNHEALTHY",
                    status=503,
                    headers={"Content-Type": "text/plain"}
                )
                
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return web.Response(
                text="ERROR",
                status=500,
                headers={"Content-Type": "text/plain"}
            )
    
    async def _handle_readiness_check(self, request: Request) -> Response:
        """Handle readiness check requests."""
        try:
            # Check if the bot is ready to handle requests
            if self.bot_application and self.bot_application.bot:
                return web.Response(
                    text="READY",
                    status=200,
                    headers={"Content-Type": "text/plain"}
                )
            else:
                return web.Response(
                    text="NOT_READY",
                    status=503,
                    headers={"Content-Type": "text/plain"}
                )
                
        except Exception as e:
            logger.error(f"Error in readiness check: {e}")
            return web.Response(
                text="ERROR",
                status=500,
                headers={"Content-Type": "text/plain"}
            )
    
    async def _handle_root(self, request: Request) -> Response:
        """Handle root endpoint with basic information."""
        info = {
            "service": "Token Sentiment Bot",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "webhook": self.webhook_path,
                "health": "/health",
                "ready": "/ready",
                "metrics": "/metrics"
            }
        }
        
        return web.json_response(info)
    
    async def _handle_metrics(self, request: Request) -> Response:
        """Handle metrics endpoint for monitoring."""
        try:
            # Get detailed health metrics
            health_data = get_health_response()
            metrics = json.loads(health_data)
            
            # Add additional metrics
            metrics["bot"] = {
                "webhook_path": self.webhook_path,
                "application_ready": self.bot_application is not None,
                "bot_ready": self.bot_application.bot is not None if self.bot_application else False
            }
            
            return web.json_response(metrics)
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return web.Response(
                text="Error getting metrics",
                status=500
            )
    
    @web.middleware
    async def _error_middleware(self, request: Request, handler):
        """Error handling middleware."""
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            return web.Response(
                text="Internal Server Error",
                status=500
            )
    
    async def start(self, host: str = "0.0.0.0", port: int = 8443):
        """Start the web server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()
            
            logger.info(f"Web server started on {host}:{port}")
            logger.info(f"Webhook endpoint: http://{host}:{port}{self.webhook_path}")
            logger.info(f"Health check: http://{host}:{port}/health")
            logger.info(f"Metrics: http://{host}:{port}/metrics")
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise
    
    async def stop(self):
        """Stop the web server."""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("Web server stopped")
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")


async def create_web_server(bot_application: Application, webhook_path: str = "/webhook") -> TokenSentimentWebServer:
    """Create and configure the web server."""
    return TokenSentimentWebServer(bot_application, webhook_path) 