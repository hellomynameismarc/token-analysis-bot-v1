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
    """Perform an HTTP request with exponential backoff.

    Retries on network errors, timeouts, and retryable status codes.
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
