# Token Sentiment Telegram Bot 🚀

A sophisticated Telegram bot that provides real-time cryptocurrency token sentiment analysis using three data pillars: **onchain smart money flows**, **social sentiment**, and **market fundamentals**.

## 🎯 Overview

The Token Sentiment Bot analyzes cryptocurrency tokens and provides **Bullish/Neutral/Bearish** signals with confidence scores and detailed explanations. It combines:

- **📊 Onchain Analysis (60%)**: Smart money flows and volume analysis via Nansen
- **🐦 Social Sentiment (25%)**: Twitter sentiment analysis and social metrics  
- **📈 Market Fundamentals (15%)**: Market cap, trading volume, and financial ratios

## ✨ Features

### 🔍 **Multi-Chain Support**
- **Ethereum** (Mainnet)
- **Solana** 
- **BNB Smart Chain (BSC)**
- **Polygon**
- **Arbitrum**
- **Optimism**
- **Avalanche**
- **Fantom**

### 📊 **Advanced Analysis**
- **Real-time sentiment scoring** with confidence levels
- **Three-bullet rationale** explaining the analysis
- **Data quality indicators** showing reliability
- **Professional formatting** with emojis and clear sections

### 🛡️ **Production Ready**
- **Rate limiting** (2 analyses per minute per user)
- **Comprehensive error handling** with actionable guidance
- **Hybrid caching** (Redis + in-memory fallback)
- **Extensive testing** (150+ tests with 77% coverage)
- **MVP deployment** ready with free hosting options
- **Load testing** configured with Locust

### 📈 **Usage Statistics**
- **Global analytics** via `/stats` command
- **Per-user tracking** and rate limit management
- **Performance metrics** and system health monitoring
- **Network breakdown** and sentiment distribution

## 📋 Project Status

### ✅ **Completed Tasks**
- **Task 1**: Project Setup & Repository Initialization ✅
- **Task 2**: Infrastructure & Deployment Foundation ✅
- **Task 3**: Data Source Wrappers (Twitter, Nansen, CoinGecko) ✅
- **Task 4**: Sentiment Analysis Engine ✅
- **Task 5**: Telegram Bot Core ✅
- **Task 6**: Rate Limiting & Usage Metrics ✅
- **Task 7**: Testing Suite & QA Automation ✅

### 🚧 **In Progress**
- **Task 8**: Documentation & Developer Experience (Current)
- **Task 9**: Deployment & Monitoring

### 📊 **Current Metrics**
- **Test Coverage**: 77% (150+ tests passing)
- **Code Quality**: Linting and formatting configured
- **Load Testing**: Locust configured for 50 concurrent users
- **CI/CD**: GitHub Actions with coverage reporting

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Telegram Bot Token
- API keys for data sources (Nansen, Twitter, CoinGecko)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/token-sentiment-bot.git
cd token-sentiment-bot
```

2. **Set up virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Run the bot**
```bash
python -m bot.main
```

## 📋 Usage

### Bot Commands

- **`/start`** - Welcome message and quick start guide
- **`/help`** - Comprehensive usage instructions and examples
- **`/stats`** - View global usage statistics and system health

### Token Analysis

Simply send a token contract address to the bot:

```
0x1f9840a85d5af5bf1d1762f925bdaddc4201f984
```

The bot will analyze the token and return a detailed sentiment report.

### Example Response

🟢 **Token Sentiment Analysis**

**📍 Token Details:**
• Address: `0x1f9840...01f984`
• Network: Ethereum
• Analysis Time: <t:1752043169:R>

**BULLISH** 🟢
🎯 **Confidence**: 85%
✅ **Data Quality**: Excellent

**📋 Analysis Breakdown:**
1. 📊 Onchain flows show strong accumulation ($2.5M net inflow)
2. 🐦 Social sentiment is positive (65% bullish mentions)
3. 📈 Market fundamentals indicate healthy trading volume

**🔍 Data Sources:**
• 📊 Onchain (60%): Smart money flows & volume
• 🐦 Social (25%): Twitter sentiment analysis
• 📈 Fundamentals (15%): Market cap & trading metrics

⚠️ **Important Disclaimer:**
*This analysis is for informational purposes only and does not constitute financial advice...*

## 🏗️ Architecture

### Core Components

```
Token Sentiment Bot/
├── bot/                    # Telegram bot implementation
│   ├── main.py            # Bot core with sentiment integration
│   └── __init__.py
├── core/                   # Core analysis engine
│   ├── sentiment_engine.py # Main sentiment analysis logic
│   ├── data_sources.py     # API wrappers for data sources
│   ├── cache.py           # Hybrid caching layer (Redis + in-memory)
│   ├── validation.py      # Address validation utilities
│   ├── http_utils.py      # HTTP utilities and retry logic
│   └── rate_limiter.py    # Rate limiting implementation
├── tests/                  # Comprehensive test suite
│   ├── test_sentiment_engine.py
│   ├── test_data_sources.py
│   ├── test_validation.py
│   ├── test_bot_integration.py
│   ├── test_cache.py
│   ├── test_http_utils.py
│   └── test_rate_limit.py
├── locustfile.py          # Load testing configuration
├── pyproject.toml         # Project configuration and coverage settings
└── requirements.txt       # Python dependencies
```

### Data Flow

1. **User Input** → Address validation and network detection
2. **Data Collection** → Parallel API calls to Nansen, Twitter, CoinGecko
3. **Analysis** → Weighted sentiment calculation with confidence scoring
4. **Response** → Formatted output with rationale and disclaimers
5. **Caching** → In-memory storage for performance optimization

## 🔧 Configuration

### Environment Variables

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://your-domain.com/webhook  # Optional for MVP

# Data Sources
NANSEN_API_KEY=your_nansen_key
TWITTER_BEARER_TOKEN=your_twitter_token
COINGECKO_API_KEY=your_coingecko_key

# Optional: Redis (for production scaling)
REDIS_URL=redis://localhost:6379
USE_REDIS=true  # Set to false for in-memory only
```

### Analysis Weights

The sentiment analysis uses configurable weights:

```python
WEIGHTS = {
    'onchain': 0.60,    # Smart money flows (60%)
    'social': 0.25,     # Twitter sentiment (25%)
    'fundamentals': 0.15 # Market metrics (15%)
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_sentiment_engine.py -v
python -m pytest tests/test_bot_integration.py -v
python -m pytest tests/test_validation.py -v

# Run with coverage
python -m pytest tests/ --cov=core --cov=bot --cov-report=html

# Run load tests (requires bot to be running)
locust -f locustfile.py --headless -u 50 -r 10 -H http://localhost:8000
```

## 🚀 Deployment Options

### 🆓 **Free MVP Options**

#### Option 1: Local Development (Free)
```bash
# Run bot in polling mode (no webhook needed)
python -m bot.main
```
**Cost**: $0/month
**Pros**: No setup, immediate testing
**Cons**: Requires your computer to be running

#### Option 2: Railway.app (Free Tier)
```bash
# Deploy to Railway (free tier: 500 hours/month)
railway login
railway init
railway up
```
**Cost**: $0/month (500 hours free)
**Pros**: Easy deployment, automatic HTTPS
**Cons**: Limited hours, may sleep after inactivity

#### Option 3: Render.com (Free Tier)
```bash
# Deploy to Render (free tier: 750 hours/month)
# Connect GitHub repo and deploy automatically
```
**Cost**: $0/month (750 hours free)
**Pros**: Easy setup, good documentation
**Cons**: Sleeps after 15 minutes of inactivity

#### Option 4: Heroku (Free Tier Discontinued)
**Note**: Heroku no longer offers free tier, but paid plans start at $7/month

### 💰 **Paid Production Options**

#### Option 1: Railway.app (Paid)
- **Starter**: $5/month (unlimited hours)
- **Pro**: $20/month (better performance)

#### Option 2: Render.com (Paid)
- **Starter**: $7/month (always on)
- **Standard**: $25/month (better performance)

#### Option 3: DigitalOcean App Platform
- **Basic**: $5/month (512MB RAM)
- **Professional**: $12/month (1GB RAM)

### 🔄 **Caching Strategy**

The bot uses a **hybrid caching approach**:

```python
# Automatic fallback: Redis → In-memory → No cache
if redis_available:
    use_redis_cache()
elif memory_available:
    use_in_memory_cache()
else:
    no_caching()
```

**Benefits**:
- ✅ No additional infrastructure costs for MVP
- ✅ Automatic fallback if Redis unavailable
- ✅ Works immediately without setup
- ✅ Can scale to Redis when needed

**Trade-offs**:
- ❌ In-memory cache lost on restart
- ❌ No shared cache across instances (in-memory mode)
- ❌ Limited by available memory

## 📊 Performance

- **Response Time**: <7 seconds median
- **Uptime**: 99%+ target (depends on hosting)
- **Rate Limits**: 2 analyses/minute per user
- **Cache Hit Ratio**: 80%+ for repeated requests
- **Error Rate**: <1% target
- **Test Coverage**: 77% overall (150+ tests)
- **Load Testing**: Configured for 50 concurrent users

## 🔒 Security & Compliance

- **API Key Management**: Secure environment variable storage
- **Rate Limiting**: Per-user and global limits
- **Input Validation**: Comprehensive address validation
- **Legal Disclaimers**: Required in all user-facing content
- **Error Handling**: No sensitive data exposure

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Set up pre-commit hooks (if configured)
pre-commit install

# Run linting
flake8 core/ bot/ tests/
black core/ bot/ tests/

# Run tests with coverage
python -m pytest --cov=core --cov=bot --cov-report=term-missing

# Run load tests
locust -f locustfile.py --headless -u 10 -r 2 -H http://localhost:8000
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**This bot is for informational purposes only and does not constitute financial advice.** 

- The sentiment analysis is based on algorithmic processing of available data
- Past performance does not guarantee future results
- Always conduct your own research (DYOR) before making investment decisions
- Consider consulting with a qualified financial advisor

## 🆘 Support

- **Documentation**: Check `/help` command in the bot
- **Issues**: [GitHub Issues](https://github.com/yourusername/token-sentiment-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/token-sentiment-bot/discussions)

## 🗺️ Roadmap

- [ ] **Multi-language support** (Spanish, Chinese, etc.)
- [ ] **Advanced charting** with price correlation
- [ ] **Portfolio tracking** and alerts
- [ ] **Custom analysis weights** per user
- [ ] **Web dashboard** for detailed analytics
- [ ] **API endpoints** for programmatic access
- [ ] **AWS production deployment** (when scaling needed)
- [ ] **Enhanced monitoring** with Prometheus/Grafana
- [ ] **Database integration** for historical analysis

---

**Built with ❤️ for the crypto community**
