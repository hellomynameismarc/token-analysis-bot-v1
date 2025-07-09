# Deployment

## Overview

The Token Sentiment Bot is designed for easy deployment with multiple options ranging from free MVP hosting to production-ready infrastructure.

## Deployment Options

### 🆓 Free MVP Options

#### 1. Local Development
```bash
# Run bot in polling mode (no webhook needed)
python -m bot.main
```
**Cost**: $0/month  
**Pros**: No setup, immediate testing  
**Cons**: Requires your computer to be running

#### 2. Railway.app (Free Tier)
```bash
# Deploy to Railway (free tier: 500 hours/month)
railway login
railway init
railway up
```
**Cost**: $0/month (500 hours free)  
**Pros**: Easy deployment, automatic HTTPS  
**Cons**: Limited hours, may sleep after inactivity

#### 3. Render.com (Free Tier)
```bash
# Deploy to Render (free tier: 750 hours/month)
# Connect GitHub repo and deploy automatically
```
**Cost**: $0/month (750 hours free)  
**Pros**: Easy setup, good documentation  
**Cons**: Sleeps after 15 minutes of inactivity

### 💰 Paid Production Options

#### 1. Railway.app (Paid)
- **Starter**: $5/month (unlimited hours)
- **Pro**: $20/month (better performance)

#### 2. Render.com (Paid)
- **Starter**: $7/month (always on)
- **Standard**: $25/month (better performance)

#### 3. DigitalOcean App Platform
- **Basic**: $5/month (512MB RAM)
- **Professional**: $12/month (1GB RAM)

## Environment Configuration

### Required Environment Variables
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Data Sources
NANSEN_API_KEY=your_nansen_api_key
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
COINGECKO_API_KEY=your_coingecko_api_key

# Optional: Redis (for production scaling)
REDIS_URL=redis://localhost:6379
USE_REDIS=true  # Set to false for in-memory only
```

### Optional Configuration
```bash
# Webhook settings (for production)
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PORT=8443

# Bot settings
RATE_LIMIT_WINDOW=60
RATE_LIMIT_MAX_REQUESTS=2
```

## Deployment Steps

### 1. Prepare Your Bot
```bash
# Clone repository
git clone https://github.com/yourusername/token-sentiment-bot.git
cd token-sentiment-bot

# Install dependencies
pip install -r requirements.txt

# Test locally
python -m pytest tests/ -v
```

### 2. Set Up Environment Variables
Create a `.env` file or set environment variables in your hosting platform:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Deploy to Your Chosen Platform

#### Railway.app
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Render.com
1. Connect your GitHub repository
2. Create a new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python -m bot.main`
5. Add environment variables

#### DigitalOcean App Platform
1. Create a new App
2. Connect your GitHub repository
3. Configure as Python app
4. Set environment variables
5. Deploy

### 4. Configure Webhook (Production)
```python
# Set webhook URL in your bot
WEBHOOK_URL = "https://your-domain.com"
```

## Monitoring and Maintenance

### Health Checks
- **Uptime Monitoring**: Use UptimeRobot (free)
- **Error Tracking**: Use Sentry (free tier available)
- **Performance Monitoring**: Built-in `/stats` command

### Logs and Debugging
```bash
# View logs
railway logs  # Railway
render logs   # Render
doctl apps logs  # DigitalOcean
```

### Scaling Considerations
- **Memory**: 512MB minimum, 1GB recommended
- **CPU**: 0.5 vCPU minimum, 1 vCPU recommended
- **Storage**: 1GB minimum for logs and cache

## Security Best Practices

1. **API Key Management**: Use environment variables, never commit to code
2. **HTTPS**: Always use HTTPS in production
3. **Rate Limiting**: Configure appropriate rate limits
4. **Input Validation**: All user inputs are validated
5. **Error Handling**: No sensitive data in error messages

## Troubleshooting

### Common Issues
1. **Bot Not Responding**: Check TELEGRAM_BOT_TOKEN
2. **API Errors**: Verify API keys and quotas
3. **Memory Issues**: Increase memory allocation
4. **Timeout Errors**: Check network connectivity

### Debug Mode
```bash
# Run with debug logging
python -m bot.main --debug
```

## Performance Optimization

### Caching Strategy
- **MVP**: In-memory caching (no additional cost)
- **Production**: Redis caching for better performance

### Rate Limiting
- **Default**: 2 analyses per minute per user
- **Configurable**: Adjust based on your needs

### Response Time
- **Target**: <7 seconds median
- **Optimization**: Parallel API calls, caching 