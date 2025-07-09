import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from core.data_sources import (
    TwitterClient,
    get_token_sentiment,
    NansenClient,
    get_nansen_netflow_score,
    CoinMarketCapClient,
    get_cmc_metadata,
    TwitterAPIError,
    NansenAPIError,
    CoinMarketCapAPIError,
)


class DummyTwitterClient(TwitterClient):
    def __init__(self):
        # pass dummy token to parent
        super().__init__(bearer_token="dummy")

    async def search_recent_tweets(self, query: str, *, max_results: int = 50):  # type: ignore[override]
        # Return two hard-coded tweets for deterministic test
        return [
            MagicMock(
                id="1",
                text="Amazing gains on $ABC, to the moon!",
                like_count=10,
                retweet_count=2,
                reply_count=1,
            ),
            MagicMock(
                id="2",
                text="$ABC is trash, I am selling.",
                like_count=1,
                retweet_count=0,
                reply_count=0,
            ),
        ]


@pytest.mark.asyncio
async def test_sentiment_for_token():
    client = DummyTwitterClient()
    result = await client.sentiment_for_token("ABC", limit=2)
    assert result["tweet_count"] == 2
    # Score should be between -1 and 1
    assert -1.0 <= result["score"] <= 1.0
    await client.close()


class DummyNansenClient(NansenClient):
    def __init__(self):
        super().__init__(api_key="dummy")

    async def smart_money_netflow(
        self, token_address: str, *, chain_id: int = 1, window: str = "24h"
    ):
        return {"inflow_usd": 1500.0, "outflow_usd": 500.0, "netflow_usd": 1000.0}


@pytest.mark.asyncio
async def test_nansen_netflow_score():
    client = DummyNansenClient()
    result = await client.netflow_score("0xToken")
    assert result["score"] == 0.5  # (1500 - 500) / 2000
    await client.close()


@pytest.mark.asyncio
async def test_holder_count():
    class DummyHoldClient(NansenClient):
        def __init__(self):
            super().__init__(api_key="dummy")

        async def holder_count(
            self, token_address: str, *, chain_id: int = 1
        ):  # type: ignore[override]
            return 12345

    client = DummyHoldClient()
    assert await client.holder_count("0xToken") == 12345
    await client.close()


@pytest.mark.asyncio
async def test_cmc_metadata():
    class DummyCMC(CoinMarketCapClient):
        def __init__(self):
            super().__init__(api_key="dummy")

        async def token_quote(self, symbol: str):  # type: ignore[override]
            return {
                "market_cap_usd": 1_000_000,
                "volume_24h_usd": 50_000,
                "price_usd": 0.05,
            }

    client = DummyCMC()
    meta = await client.token_quote("ABC")
    assert meta["market_cap_usd"] == 1_000_000
    await client.close()


@pytest.mark.asyncio
async def test_twitter_search_recent_tweets_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "1", "text": "Bullish $ABC!", "public_metrics": {"like_count": 5, "retweet_count": 2, "reply_count": 1}},
            {"id": "2", "text": "Bearish $ABC", "public_metrics": {"like_count": 1, "retweet_count": 0, "reply_count": 0}},
        ]
    }
    with patch.object(httpx.AsyncClient, "request", new=AsyncMock(return_value=mock_response)):
        client = TwitterClient(bearer_token="test")
        tweets = await client.search_recent_tweets("$ABC")
        assert len(tweets) == 2
        assert tweets[0].text == "Bullish $ABC!"
        await client.close()

@pytest.mark.asyncio
async def test_twitter_search_recent_tweets_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Error"
    with patch.object(httpx.AsyncClient, "request", new=AsyncMock(return_value=mock_response)):
        with patch('core.data_sources.cached_request') as mock_cached_request:
            # Make cached_request call the fetch function directly
            async def mock_cached_request_impl(namespace, params, fetch_func, ttl_seconds=300):
                return await fetch_func()
            mock_cached_request.side_effect = mock_cached_request_impl
            
            client = TwitterClient(bearer_token="test")
            with pytest.raises(TwitterAPIError):
                await client.search_recent_tweets("$ABC")
            await client.close()

@pytest.mark.asyncio
async def test_twitter_sentiment_for_token():
    # Patch search_recent_tweets to return mock tweets
    with patch.object(TwitterClient, "search_recent_tweets", new=AsyncMock(return_value=[
        MagicMock(text="Bullish $ABC!", like_count=5, retweet_count=2, reply_count=1),
        MagicMock(text="Bearish $ABC", like_count=1, retweet_count=0, reply_count=0),
    ])):
        client = TwitterClient(bearer_token="test")
        result = await client.sentiment_for_token("ABC")
        assert "score" in result and "tweet_count" in result
        assert result["tweet_count"] == 2
        await client.close()

@pytest.mark.asyncio
async def test_get_token_sentiment():
    # Patch TwitterClient.sentiment_for_token
    with patch.object(TwitterClient, "sentiment_for_token", new=AsyncMock(return_value={"score": 0.5, "tweet_count": 10})):
        result = await get_token_sentiment("ABC", bearer_token="test")
        assert result["score"] == 0.5
        assert result["tweet_count"] == 10

@pytest.mark.asyncio
async def test_nansen_smart_money_netflow_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"inflow_usd": 1000, "outflow_usd": 500, "netflow_usd": 500}
    with patch.object(httpx.AsyncClient, "request", new=AsyncMock(return_value=mock_response)):
        client = NansenClient(api_key="test")
        result = await client.smart_money_netflow("0xabc")
        assert result["inflow_usd"] == 1000
        assert result["outflow_usd"] == 500
        assert result["netflow_usd"] == 500
        await client.close()

@pytest.mark.asyncio
async def test_nansen_smart_money_netflow_error():
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    with patch.object(httpx.AsyncClient, "request", new=AsyncMock(return_value=mock_response)):
        with patch('core.data_sources.cached_request') as mock_cached_request:
            # Make cached_request call the fetch function directly
            async def mock_cached_request_impl(namespace, params, fetch_func, ttl_seconds=300):
                return await fetch_func()
            mock_cached_request.side_effect = mock_cached_request_impl
            
            client = NansenClient(api_key="test")
            with pytest.raises(NansenAPIError):
                await client.smart_money_netflow("0xabc")
            await client.close()

@pytest.mark.asyncio
async def test_get_nansen_netflow_score():
    # Patch NansenClient.netflow_score
    with patch.object(NansenClient, "netflow_score", new=AsyncMock(return_value={"netflow_usd": 123.45})):
        result = await get_nansen_netflow_score("0xabc", chain_id=1, api_key="test")
        assert result["netflow_usd"] == 123.45

@pytest.mark.asyncio
async def test_cmc_token_quote_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {"ABC": {"quote": {"USD": {"price": 1.23, "volume_24h": 10000, "market_cap": 123456}}}}
    }
    with patch.object(httpx.AsyncClient, "request", new=AsyncMock(return_value=mock_response)):
        with patch('core.data_sources.cached_request') as mock_cached_request:
            # Make cached_request call the fetch function directly
            async def mock_cached_request_impl(namespace, params, fetch_func, ttl_seconds=300):
                return await fetch_func()
            mock_cached_request.side_effect = mock_cached_request_impl
            
            client = CoinMarketCapClient(api_key="test")
            result = await client.token_quote("ABC")
            assert result["price_usd"] == 1.23
            assert result["volume_24h_usd"] == 10000
            assert result["market_cap_usd"] == 123456
            await client.close()

@pytest.mark.asyncio
async def test_cmc_token_quote_error():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    with patch.object(httpx.AsyncClient, "request", new=AsyncMock(return_value=mock_response)):
        with patch('core.data_sources.cached_request') as mock_cached_request:
            # Make cached_request call the fetch function directly
            async def mock_cached_request_impl(namespace, params, fetch_func, ttl_seconds=300):
                return await fetch_func()
            mock_cached_request.side_effect = mock_cached_request_impl
            
            client = CoinMarketCapClient(api_key="test")
            with pytest.raises(CoinMarketCapAPIError):
                await client.token_quote("ABC")
            await client.close()

@pytest.mark.asyncio
async def test_get_cmc_metadata():
    # Patch CoinMarketCapClient.token_quote
    with patch.object(CoinMarketCapClient, "token_quote", new=AsyncMock(return_value={"price": 1.23, "volume_24h": 10000, "market_cap": 123456})):
        result = await get_cmc_metadata("ABC", api_key="test")
        assert result["price"] == 1.23
        assert result["market_cap"] == 123456
