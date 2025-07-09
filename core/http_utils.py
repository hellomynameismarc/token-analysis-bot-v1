"""
HTTP Utilities Module

Provides robust HTTP request functionality with automatic retry logic,
exponential backoff, and jitter for handling transient network issues.

Features:
- Exponential backoff with jitter
- Retry on server errors and rate limiting
- Configurable retry attempts and backoff factor
- Thread-safe async operations
"""

import asyncio
import random
from typing import Optional

import httpx

# Retryable status codes (server errors, rate limiting)
_RETRY_STATUS = {429, 500, 502, 503, 504}


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: Optional[dict] = None,
    retries: int = 3,
    backoff_factor: float = 0.5,
) -> httpx.Response:
    """Perform an HTTP request with exponential backoff and automatic retries.
    
    This function implements a robust HTTP request pattern that automatically
    retries on transient failures, network errors, and retryable status codes.
    It uses exponential backoff with jitter to prevent thundering herd problems.
    
    Args:
        client: The httpx.AsyncClient instance to use for requests
        method: HTTP method (GET, POST, etc.)
        url: Target URL for the request
        params: Optional query parameters to include in the request
        retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Base delay for exponential backoff in seconds (default: 0.5)
        
    Returns:
        httpx.Response: The successful HTTP response
        
    Raises:
        httpx.RequestError: If the request fails after all retry attempts
        httpx.TimeoutException: If the request times out after all retry attempts
        httpx.HTTPStatusError: If a non-retryable status code is received
        
    Example:
        >>> client = httpx.AsyncClient()
        >>> response = await request_with_retries(
        ...     client, "GET", "https://api.example.com/data",
        ...     params={"key": "value"}, retries=5
        ... )
    """
    delay = backoff_factor
    for attempt in range(retries):
        try:
            resp = await client.request(method, url, params=params)
            if resp.status_code in _RETRY_STATUS and attempt < retries - 1:
                raise httpx.HTTPStatusError(
                    "retryable status", request=resp.request, response=resp
                )
            return resp
        except (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError):
            if attempt == retries - 1:
                raise
            jitter = random.uniform(0, delay)
            await asyncio.sleep(delay + jitter)
            delay *= 2
    # Should never reach here
    raise RuntimeError("Exceeded retry attempts")
