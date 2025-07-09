import os
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict

import httpx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class TwitterAPIError(Exception):
    """Raised when Twitter API returns a non-success status."""


@dataclass
class Tweet:
    id: str
    text: str
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0


class TwitterClient:
    """Asynchronous wrapper around the Twitter v2 API for recent search + sentiment scoring."""

    _BASE_URL = "https://api.twitter.com/2"

    def __init__(self, bearer_token: str | None = None, *, timeout: float = 10.0):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            raise ValueError("Twitter bearer token not provided via arg or TWITTER_BEARER_TOKEN env var.")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        self._sentiment = SentimentIntensityAnalyzer()

    async def close(self) -> None:
        await self._client.aclose()

    # --------------------------- Twitter API ---------------------------
    async def search_recent_tweets(self, query: str, *, max_results: int = 50) -> List[Tweet]:
        """Return recent tweets matching a query.

        Docs: https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-recent
        """
        url = f"{self._BASE_URL}/tweets/search/recent"
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "public_metrics",
        }
        r = await self._client.get(url, params=params)
        if r.status_code != 200:
            raise TwitterAPIError(f"Twitter API {r.status_code}: {r.text}")
        payload = r.json()
        tweets: List[Tweet] = []
        for item in payload.get("data", []):
            metrics = item.get("public_metrics", {})
            tweets.append(
                Tweet(
                    id=item["id"],
                    text=item["text"],
                    like_count=metrics.get("like_count", 0),
                    retweet_count=metrics.get("retweet_count", 0),
                    reply_count=metrics.get("reply_count", 0),
                )
            )
        return tweets

    # ------------------------ Sentiment Utilities ----------------------
    def _score_text(self, text: str) -> float:
        """Return compound sentiment score in range [-1, 1]."""
        return self._sentiment.polarity_scores(text)["compound"]

    def _engagement_weight(self, tweet: Tweet) -> int:
        return tweet.like_count + tweet.retweet_count + tweet.reply_count + 1  # +1 to avoid 0 weight

    # --------------------- Public High-level Helper --------------------
    async def sentiment_for_token(self, token_symbol: str, *, limit: int = 50) -> dict:
        """Compute weighted sentiment score for a given token symbol (e.g., ABC).

        Returns dict with keys: score (float), tweet_count (int).
        """
        query = f"${token_symbol} lang:en -is:retweet"
        tweets = await self.search_recent_tweets(query, max_results=limit)
        if not tweets:
            return {"score": 0.0, "tweet_count": 0}

        scores = [self._score_text(t.text) for t in tweets]
        weights = [self._engagement_weight(t) for t in tweets]
        weighted_scores = [s * w for s, w in zip(scores, weights)]
        final = sum(weighted_scores) / sum(weights)
        return {"score": round(final, 3), "tweet_count": len(tweets)}


# ------------------------------ Convenience -----------------------------
async def get_token_sentiment(token_symbol: str, bearer_token: str | None = None) -> dict:
    """Convenience function to fetch weighted Twitter sentiment for a token."""
    client = TwitterClient(bearer_token)
    try:
        return await client.sentiment_for_token(token_symbol)
    finally:
        await client.close()


# =============================== NANSEN ==================================
import json
from typing import Dict

class NansenAPIError(Exception):
    """Raised when Nansen API returns an error response."""


class NansenClient:
    """Async wrapper around the Nansen v1 API.

    Currently used for Smart-Money net flows.
    Docs: https://docs.nansen.ai/ › API › Smart Money › Flows
    """

    _BASE_URL = "https://api.nansen.ai/v1"

    def __init__(self, api_key: Optional[str] = None, *, timeout: float = 10.0):
        self.api_key = api_key or os.getenv("NANSEN_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Nansen API key not provided via arg or NANSEN_API_KEY env var."
            )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"x-api-key": self.api_key},
        )

    async def close(self) -> None:
        await self._client.aclose()

    # --------------------------- Nansen API ---------------------------
    async def smart_money_netflow(
        self,
        token_address: str,
        *,
        chain_id: int = 1,
        window: str = "24h",
    ) -> Dict[str, float]:
        """Fetch smart-money inflow/outflow data.

        Parameters
        ----------
        token_address : str  Contract address (checksum or lowercase).
        chain_id      : int  EVM chain id (1 = Ethereum, 56 = BSC…). Defaults to 1.
        window        : str  1h | 6h | 24h | 7d. Defaults to 24h.
        """
        url = f"{self._BASE_URL}/smart-money/flows"
        params = {
            "address": token_address,
            "chain_id": chain_id,
            "window": window,
        }
        r = await self._client.get(url, params=params)
        if r.status_code != 200:
            raise NansenAPIError(f"Nansen API {r.status_code}: {r.text}")
        data = r.json()
        return {
            "inflow_usd": float(data.get("inflow_usd", 0)),
            "outflow_usd": float(data.get("outflow_usd", 0)),
            "netflow_usd": float(data.get("netflow_usd", data.get("inflow_usd", 0) - data.get("outflow_usd", 0))),
        }

    async def netflow_score(
        self, token_address: str, *, chain_id: int = 1, window: str = "24h"
    ) -> Dict[str, float]:
        """Compute normalized netflow score in range [-1, 1].

        score = (inflow - outflow) / (inflow + outflow)
        Returns dict with score and raw flows.
        """
        flows = await self.smart_money_netflow(
            token_address, chain_id=chain_id, window=window
        )
        inflow = flows["inflow_usd"]
        outflow = flows["outflow_usd"]
        netflow = flows["netflow_usd"]
        denom = inflow + outflow or 1.0
        score = netflow / denom
        return {
            "score": round(score, 3),
            "inflow_usd": inflow,
            "outflow_usd": outflow,
        }

    # ----------------------- Token God Mode - Holders ----------------------
    async def holder_count(self, token_address: str, *, chain_id: int = 1) -> int:
        """Return total number of holders for a token.

        Docs path: /v1/token/holders
        Example response: {"address": "0x...", "chain_id": 1, "holder_count": 12345}
        """
        url = f"{self._BASE_URL}/token/holders"
        params = {"address": token_address, "chain_id": chain_id}
        r = await self._client.get(url, params=params)
        if r.status_code != 200:
            raise NansenAPIError(f"Nansen API {r.status_code}: {r.text}")
        data = r.json()
        return int(data.get("holder_count", 0))


async def get_nansen_netflow_score(
    token_address: str, *, chain_id: int = 1, api_key: Optional[str] = None
) -> Dict[str, float]:
    """Convenience helper for one-shot netflow score fetch."""
    client = NansenClient(api_key)
    try:
        return await client.netflow_score(token_address, chain_id=chain_id)
    finally:
        await client.close()


async def get_token_holder_count(token_address: str, *, chain_id: int = 1, api_key: Optional[str] = None) -> int:
    """Convenience helper to fetch holder count via Nansen Token God Mode."""
    client = NansenClient(api_key)
    try:
        return await client.holder_count(token_address, chain_id=chain_id)
    finally:
        await client.close()


# ============================= COINMARKETCAP =============================
class CoinMarketCapAPIError(Exception):
    """Raised when CoinMarketCap API responds with error."""


class CoinMarketCapClient:
    """Simple async wrapper for CoinMarketCap quotes endpoint.

    Docs: https://coinmarketcap.com/api/documentation/v1/#operation/getV1CryptocurrencyQuotesLatest
    """

    _BASE_URL = "https://pro-api.coinmarketcap.com/v1"

    def __init__(self, api_key: Optional[str] = None, *, timeout: float = 10.0):
        self.api_key = api_key or os.getenv("CMC_API_KEY")
        if not self.api_key:
            raise ValueError("CMC API key not provided via arg or CMC_API_KEY env var.")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"X-CMC_PRO_API_KEY": self.api_key},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def token_quote(self, symbol: str) -> Dict[str, float]:
        """Return market-cap, 24h volume (USD), and price for a token symbol."""
        url = f"{self._BASE_URL}/cryptocurrency/quotes/latest"
        params = {"symbol": symbol.upper(), "convert": "USD"}
        r = await self._client.get(url, params=params)
        if r.status_code != 200:
            raise CoinMarketCapAPIError(f"CMC {r.status_code}: {r.text}")
        data = r.json()
        info = data["data"].get(symbol.upper())
        if not info:
            raise CoinMarketCapAPIError("Symbol not found in CMC response")
        quote = info["quote"]["USD"]
        return {
            "market_cap_usd": float(quote.get("market_cap", 0)),
            "volume_24h_usd": float(quote.get("volume_24h", 0)),
            "price_usd": float(quote.get("price", 0)),
        }


async def get_cmc_metadata(symbol: str, api_key: Optional[str] = None) -> Dict[str, float]:
    client = CoinMarketCapClient(api_key)
    try:
        return await client.token_quote(symbol)
    finally:
        await client.close()
