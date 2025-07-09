"""
Tests for HTTP utilities and helper functions.

Tests the request_with_retries function with various scenarios
including retries, timeouts, and different status codes.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from core.http_utils import request_with_retries


class TestRequestWithRetries:
    """Test the request_with_retries function."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock httpx client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.mark.asyncio
    async def test_successful_request_first_try(self, mock_client):
        """Test successful request on first attempt."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.request.return_value = mock_response
        
        result = await request_with_retries(
            mock_client, "GET", "https://api.example.com/test"
        )
        
        assert result == mock_response
        mock_client.request.assert_called_once_with(
            "GET", "https://api.example.com/test", params=None
        )
    
    @pytest.mark.asyncio
    async def test_successful_request_with_params(self, mock_client):
        """Test successful request with query parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.request.return_value = mock_response
        
        params = {"key": "value", "limit": 10}
        result = await request_with_retries(
            mock_client, "POST", "https://api.example.com/test", params=params
        )
        
        assert result == mock_response
        mock_client.request.assert_called_once_with(
            "POST", "https://api.example.com/test", params=params
        )
    
    @pytest.mark.asyncio
    async def test_retry_on_429_status(self, mock_client):
        """Test retry on 429 (rate limit) status code."""
        # First call returns 429, second call succeeds
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_429,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_on_500_status(self, mock_client):
        """Test retry on 500 (server error) status code."""
        # First call returns 500, second call succeeds
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_500,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_on_502_status(self, mock_client):
        """Test retry on 502 (bad gateway) status code."""
        mock_response_502 = MagicMock()
        mock_response_502.status_code = 502
        mock_response_502.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_502,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_on_503_status(self, mock_client):
        """Test retry on 503 (service unavailable) status code."""
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_503,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_on_504_status(self, mock_client):
        """Test retry on 504 (gateway timeout) status code."""
        mock_response_504 = MagicMock()
        mock_response_504.status_code = 504
        mock_response_504.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_504,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_status(self, mock_client):
        """Test that non-retryable status codes are not retried."""
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        
        mock_client.request.return_value = mock_response_404
        
        result = await request_with_retries(
            mock_client, "GET", "https://api.example.com/test", retries=3
        )
        
        assert result == mock_response_404
        mock_client.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_on_request_error(self, mock_client):
        """Test retry on httpx.RequestError."""
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            httpx.RequestError("Network error"),
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout_exception(self, mock_client):
        """Test retry on httpx.TimeoutException."""
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            httpx.TimeoutException("Request timeout"),
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=2
            )
        
        assert result == mock_response_200
        assert mock_client.request.call_count == 2
        mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_client):
        """Test that max retries are respected."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_client.request.return_value = mock_response_500
        
        # With retries=2, it should try 2 times and return the 500 response
        result = await request_with_retries(
            mock_client, "GET", "https://api.example.com/test", retries=2
        )
        
        assert result == mock_response_500
        assert mock_client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_custom_backoff_factor(self, mock_client):
        """Test custom backoff factor for retries."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_500,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", 
                retries=2, backoff_factor=1.0
            )
        
        # Check that sleep was called with the custom backoff factor
        mock_sleep.assert_called_once()
        # The sleep time should be approximately backoff_factor + jitter
        call_args = mock_sleep.call_args[0][0]
        assert call_args >= 1.0  # backoff_factor
        assert call_args <= 2.0  # backoff_factor + max jitter
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, mock_client):
        """Test that backoff increases exponentially."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_500,
            mock_response_500,
            mock_response_200
        ]
        
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", 
                retries=3, backoff_factor=0.5
            )
        
        # Should have slept twice (before 2nd and 3rd attempts)
        assert len(sleep_times) == 2
        # First sleep should be around 0.5 + jitter
        assert sleep_times[0] >= 0.5
        assert sleep_times[0] <= 1.0
        # Second sleep should be around 1.0 + jitter (doubled)
        assert sleep_times[1] >= 1.0
        assert sleep_times[1] <= 2.0
    
    @pytest.mark.asyncio
    async def test_jitter_in_backoff(self, mock_client):
        """Test that jitter is added to backoff delays."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_client.request.side_effect = [
            mock_response_500,
            mock_response_200
        ]
        
        sleep_times = []
        
        async def mock_sleep(delay):
            sleep_times.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", 
                retries=2, backoff_factor=1.0
            )
        
        # Should have slept once
        assert len(sleep_times) == 1
        # Sleep time should be base delay + jitter
        base_delay = 1.0
        assert sleep_times[0] >= base_delay
        assert sleep_times[0] <= base_delay + base_delay  # max jitter is base_delay
    
    @pytest.mark.asyncio
    async def test_different_http_methods(self, mock_client):
        """Test different HTTP methods work correctly."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        
        for method in methods:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.request.return_value = mock_response
            
            result = await request_with_retries(
                mock_client, method, "https://api.example.com/test"
            )
            
            assert result == mock_response
            mock_client.request.assert_called_with(
                method, "https://api.example.com/test", params=None
            )
            
            # Reset for next iteration
            mock_client.reset_mock()
    
    @pytest.mark.asyncio
    async def test_last_retry_attempt_fails(self, mock_client):
        """Test that the last retry attempt can still fail."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_client.request.return_value = mock_response_500
        
        # With retries=1, it should try once and return the 500 response
        result = await request_with_retries(
            mock_client, "GET", "https://api.example.com/test", retries=1
        )
        
        assert result == mock_response_500
        # Should have tried exactly once (no retries)
        mock_client.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_zero_retries(self, mock_client):
        """Test behavior with zero retries."""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.request = MagicMock()
        
        mock_client.request.return_value = mock_response_500
        
        with pytest.raises(RuntimeError, match="Exceeded retry attempts"):
            await request_with_retries(
                mock_client, "GET", "https://api.example.com/test", retries=0
            )
        
        # Should not have tried at all
        mock_client.request.assert_not_called() 