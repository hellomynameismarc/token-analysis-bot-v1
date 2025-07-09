# Deployment Guide - Token Sentiment Bot 🚀

This guide covers free and low-cost deployment options for the Token Sentiment Bot MVP.

## 🆓 Free Deployment Options

### Option 1: Railway.app (Recommended for MVP)

**Cost**: $0/month (500 hours free)
**Pros**: Easy deployment, automatic HTTPS, good performance
**Cons**: Limited hours, may sleep after inactivity

#### Setup Steps:

1. **Install Railway CLI**
```bash
npm install -g @railway/cli
```

2. **Login to Railway**
```bash
railway login
```

3. **Initialize project**
```bash
railway init
```

4. **Set environment variables**
```bash
railway variables set TELEGRAM_BOT_TOKEN=your_bot_token
railway variables set NANSEN_API_KEY=your_nansen_key
railway variables set TWITTER_BEARER_TOKEN=your_twitter_token
railway variables set COINGECKO_API_KEY=your_coingecko_key
railway variables set USE_REDIS=false
```

5. **Configure sentiment weights (optional)**
   - The bot uses `config.yaml` for sentiment weighting
   - Default: 80% onchain, 5% social, 15% fundamentals
   - You can customize this by editing `config.yaml` in your repository

6. **Deploy**
```bash
railway up
```

7. **Get your webhook URL**
```bash
railway domain
```

8. **Set webhook in Telegram**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-railway-domain.railway.app/webhook"}'
```

### Option 2: Render.com

**Cost**: $0/month (750 hours free)
**Pros**: Easy setup, good documentation, GitHub integration
**Cons**: Sleeps after 15 minutes of inactivity

#### Setup Steps:

1. **Connect GitHub repository**
   - Go to [render.com](https://render.com)
   - Connect your GitHub account
   - Select your repository

2. **Create new Web Service**
   - **Name**: `token-sentiment-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m bot.main`

3. **Set environment variables**
   - `TELEGRAM_BOT_TOKEN`
   - `NANSEN_API_KEY`
   - `TWITTER_BEARER_TOKEN`
   - `COINGECKO_API_KEY`
   - `USE_REDIS=false`

4. **Configure sentiment weights (optional)**
   - The bot uses `config.yaml` for sentiment weighting
   - Default: 80% onchain, 5% social, 15% fundamentals
   - You can customize this by editing `config.yaml` in your repository

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy from your GitHub repo

### Option 3: Local Development (Free)

**Cost**: $0/month
**Pros**: No setup, immediate testing, full control
**Cons**: Requires your computer to be running

#### Setup Steps:

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Set environment variables**
```bash
export TELEGRAM_BOT_TOKEN=your_bot_token
export NANSEN_API_KEY=your_nansen_key
export TWITTER_BEARER_TOKEN=your_twitter_token
export COINGECKO_API_KEY=your_coingecko_key
export USE_REDIS=false
```

3. **Configure sentiment weights (optional)**
   - Edit `config.yaml` to customize sentiment weighting
   - Default: 80% onchain, 5% social, 15% fundamentals

4. **Run in polling mode**
```bash
python -m bot.main
```

## 💰 Paid Production Options

### Option 1: Railway.app (Paid)

- **Starter**: $5/month (unlimited hours)
- **Pro**: $20/month (better performance)

### Option 2: Render.com (Paid)

- **Starter**: $7/month (always on)
- **Standard**: $25/month (better performance)

### Option 3: DigitalOcean App Platform

- **Basic**: $5/month (512MB RAM)
- **Professional**: $12/month (1GB RAM)

## 🔧 Environment Configuration

### Configuration Files

The bot uses `config.yaml` for customizable parameters:

```yaml
# Sentiment Analysis Weighting (must sum to 1.0)
weights:
  onchain: 0.80      # Nansen smart money flows (80%)
  social: 0.05       # Twitter sentiment (5%)
  fundamentals: 0.15 # Token fundamentals (15%)

# Signal Classification Thresholds
thresholds:
  bullish: 0.2       # Score > 0.2 = Bullish
  bearish: -0.2      # Score < -0.2 = Bearish

# Rate Limiting Configuration
rate_limiting:
  window_seconds: 60        # Rate limit window
  max_requests: 2           # Max requests per window per user
```

**To customize:**
1. Edit `config.yaml` in your repository
2. Redeploy your application
3. The bot will automatically load the new configuration

### Required Environment Variables

```bash
# Telegram Bot (Required)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Data Sources (Required)
NANSEN_API_KEY=your_nansen_api_key
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
COINGECKO_API_KEY=your_coingecko_api_key

# Optional: Redis (set to false for MVP)
USE_REDIS=false
REDIS_URL=redis://localhost:6379

# Optional: Webhook URL (for production)
WEBHOOK_URL=https://your-domain.com/webhook

# Optional: Monitoring (Sentry)
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
ENVIRONMENT=production
VERSION=1.0.0
```

### Getting API Keys

#### 1. Telegram Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Follow instructions to create your bot
4. Copy the token provided

#### 2. Nansen API Key
1. Go to [nansen.ai](https://nansen.ai)
2. Sign up for an account
3. Navigate to API section
4. Generate an API key

#### 3. Twitter Bearer Token
1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Apply for developer access
3. Create a new app
4. Generate Bearer Token

#### 4. CoinGecko API Key
1. Go to [coingecko.com](https://coingecko.com)
2. Sign up for Pro account (free tier available)
3. Generate API key

## 📊 Performance Optimization

### For Free Tiers

1. **Use in-memory caching**
```bash
USE_REDIS=false
```

2. **Optimize response times**
- Cache frequently requested tokens
- Use async operations
- Implement rate limiting

3. **Monitor usage**
- Track API calls to stay within limits
- Monitor memory usage
- Check response times

### Scaling Considerations

When you need to scale beyond free tiers:

1. **Add Redis caching**
```bash
USE_REDIS=true
REDIS_URL=your_redis_url
```

2. **Implement database storage**
- Store user analytics
- Track usage patterns
- Cache persistent data

3. **Add monitoring**
- Application performance monitoring
- Error tracking
- Usage analytics

## 🚨 Troubleshooting

### Common Issues

#### 1. Bot not responding
- Check if `TELEGRAM_BOT_TOKEN` is set correctly
- Verify webhook URL is accessible
- Check application logs

#### 2. API rate limits
- Implement exponential backoff
- Add request queuing
- Monitor API usage

#### 3. Memory issues
- Reduce cache size
- Implement garbage collection
- Monitor memory usage

#### 4. Deployment failures
- Check environment variables
- Verify Python version compatibility
- Review build logs

### Debug Commands

```bash
# Test bot locally
python -m bot.main

# Check environment variables
echo $TELEGRAM_BOT_TOKEN

# Test API connections
python -c "from core.data_sources import *; print('APIs configured')"

# Run tests
python -m pytest tests/ -v
```

## 📈 Monitoring & Analytics

### Health Check Endpoints

The bot provides several health check endpoints for monitoring:

- **`/health`** - Basic health check (returns OK/UNHEALTHY)
- **`/ready`** - Readiness check (returns READY/NOT_READY)
- **`/metrics`** - Detailed metrics and system information
- **`/`** - Root endpoint with service information

### Setting Up Uptime Monitoring

#### Option 1: Automated Setup

Use our monitoring setup script:

```bash
# Basic setup (shows manual instructions)
python monitoring/setup_monitoring.py your-domain.railway.app

# Automated setup with UptimeRobot
python monitoring/setup_monitoring.py your-domain.railway.app --uptimerobot-api-key YOUR_KEY
```

#### Option 2: Manual Setup

**UptimeRobot (Recommended - Free):**
1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Sign up for a free account
3. Create a new monitor:
   - URL: `https://your-domain.railway.app/health`
   - Type: HTTP(s)
   - Interval: 5 minutes
   - Expected response: `OK`

**Pingdom (Free):**
1. Go to [pingdom.com](https://www.pingdom.com)
2. Sign up for a free account
3. Create a new HTTP check:
   - URL: `https://your-domain.railway.app/health`
   - Interval: 1 minute

**StatusCake (Free):**
1. Go to [statuscake.com](https://www.statuscake.com)
2. Sign up for a free account
3. Create a new test:
   - URL: `https://your-domain.railway.app/health`
   - Test type: HTTP
   - Check rate: 5 minutes

### Built-in Statistics

The bot includes built-in statistics via `/stats` command:
- Total analyses performed
- User count and activity
- Success rates and error tracking
- Performance metrics

### External Monitoring

For production deployments, consider:
- **Uptime monitoring**: UptimeRobot (free)
- **Error tracking**: Sentry (free tier)
- **Performance monitoring**: New Relic (free tier)

## 🔒 Security Best Practices

1. **Environment Variables**
   - Never commit API keys to git
   - Use secure environment variable storage
   - Rotate keys regularly

2. **Rate Limiting**
   - Implement per-user rate limits
   - Add global rate limiting
   - Monitor for abuse

3. **Input Validation**
   - Validate all user inputs
   - Sanitize addresses
   - Implement error handling

4. **API Security**
   - Use HTTPS for all communications
   - Implement API key rotation
   - Monitor API usage

## 🎯 Next Steps

1. **Deploy to free tier** (Railway or Render)
2. **Test with real users**
3. **Monitor performance and usage**
4. **Scale when needed** (upgrade to paid plan)
5. **Add advanced features** (database, monitoring, etc.)

---

**Remember**: Start with free options to validate your MVP before investing in paid infrastructure! 🚀 