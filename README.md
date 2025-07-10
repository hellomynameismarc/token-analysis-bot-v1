# Token Sentiment Bot 🤖

A Telegram bot that analyzes token sentiment using onchain data, social signals, and fundamentals.

## �� Quick Start

1. **Setup:**
   ```bash
   git clone <your-repo>
   cd "Token Sentiment v1"
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Run:**
   ```bash
   ./start_bot.sh
   # Or: python run_bot.py
   ```

## 📊 Features

- **Multi-chain support**: Ethereum, Base, Solana
- **Smart sentiment analysis**: 80% onchain + 5% social + 15% fundamentals
- **Real-time data**: Nansen, Twitter, CoinMarketCap integration
- **Rate limiting**: 2 analyses per minute per user
- **Confidence scoring**: 0-100% based on data quality

## 🔧 Configuration

Required API keys in `.env`:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TWITTER_BEARER_TOKEN` - Twitter API access
- `NANSEN_API_KEY` - Nansen onchain data
- `COINMARKETCAP_API_KEY` - Market data

## 📱 Usage

1. Start a chat with your bot on Telegram
2. Send a token contract address
3. Get instant sentiment analysis with confidence scores

**Supported formats:**
- Ethereum/Base: `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984`
- Solana: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`

## 🏗️ Project Structure

```
Token Sentiment v1/
├── bot/                 # Bot implementation
│   └── main.py         # Main bot logic
├── core/               # Core functionality
│   ├── sentiment_engine.py
│   ├── data_sources.py
│   ├── validation.py
│   └── rate_limiter.py
├── run_bot.py          # Bot runner
├── start_bot.sh        # Startup script
├── requirements.txt    # Dependencies
└── .env               # API keys (create from env.example)
```

## ⚠️ Disclaimer

This bot provides sentiment analysis for educational purposes only. Not financial advice. Always do your own research (DYOR).

## 🛠️ Development

- **Tests**: `python -m pytest tests/`
- **Documentation**: `mkdocs serve`
- **Deployment**: See `DEPLOYMENT.md`
