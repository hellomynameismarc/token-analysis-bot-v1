import pytest

from core.data_sources import Tweet, TwitterClient, NansenClient


class DummyTwitterClient(TwitterClient):
    def __init__(self):
        # pass dummy token to parent
        super().__init__(bearer_token="dummy")

    async def search_recent_tweets(self, query: str, *, max_results: int = 50):  # type: ignore[override]
        # Return two hard-coded tweets for deterministic test
        return [
            Tweet(id="1", text="Amazing gains on $ABC, to the moon!", like_count=10, retweet_count=2, reply_count=1),
            Tweet(id="2", text="$ABC is trash, I am selling.", like_count=1, retweet_count=0, reply_count=0),
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

    async def smart_money_netflow(self, token_address: str, *, window: str = "24h"):
        return {"inflow_usd": 1500.0, "outflow_usd": 500.0}

@pytest.mark.asyncio
async def test_nansen_netflow_score():
    client = DummyNansenClient()
    result = await client.netflow_score("0xToken")
    assert result["score"] == 0.5  # (1500 - 500) / 2000
    await client.close() 