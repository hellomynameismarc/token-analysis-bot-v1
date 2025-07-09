# Token Sentiment Bot API Documentation

Welcome to the API documentation for the **Token Sentiment Telegram Bot** - a sophisticated cryptocurrency token analysis system that combines on-chain data, social sentiment, and market fundamentals.

## 🚀 Quick Start

The Token Sentiment Bot analyzes cryptocurrency tokens using three data pillars:

- **📊 Onchain Analysis (60%)**: Smart money flows via Nansen
- **🐦 Social Sentiment (25%)**: Twitter sentiment analysis  
- **📈 Market Fundamentals (15%)**: Market cap, volume, and financial ratios

## 📚 API Reference

### Core Modules

- **[Sentiment Engine](api/sentiment_engine.md)** - Main analysis engine with weighting and confidence calculation
- **[Data Sources](api/data_sources.md)** - API wrappers for Twitter, Nansen, and CoinGecko
- **[Cache](api/cache.md)** - Hybrid caching system (Redis + in-memory fallback)
- **[Validation](api/validation.md)** - Token address validation for multiple networks
- **[HTTP Utils](api/http_utils.md)** - Robust HTTP requests with retry logic
- **[Rate Limiter](api/rate_limiter.md)** - In-memory rate limiting for user requests

### Bot Implementation

- **[Main Bot](api/bot_main.md)** - Telegram bot core with webhook handling

## 🛠️ Development

- **[Testing](development/testing.md)** - Comprehensive test suite and coverage
- **[Load Testing](development/load_testing.md)** - Performance testing with Locust
- **[Deployment](development/deployment.md)** - Deployment options and configuration

## 📊 Project Status

- **Test Coverage**: 77% (150+ tests)
- **Supported Networks**: Ethereum, Solana, BSC, Polygon, Arbitrum, Optimism, Avalanche, Fantom
- **Rate Limiting**: 2 analyses per minute per user
- **Response Time**: <7 seconds median

## 🔧 Getting Started

```python
from core.sentiment_engine import SentimentEngine

# Initialize the sentiment engine
engine = SentimentEngine()

# Analyze a token
result = await engine.analyze_token("0x1f9840a85d5af5bf1d1762f925bdaddc4201f984")

print(f"Signal: {result.signal}")
print(f"Confidence: {result.confidence:.1%}")
print(f"Score: {result.overall_score:.3f}")
```

## 📖 Usage Examples

See the individual API documentation pages for detailed examples and usage patterns for each module.

---

**Built with ❤️ for the crypto community** 