# Monitoring Setup Guide

This guide covers setting up comprehensive monitoring for the Token Sentiment Bot using free tools and services.

## 🎯 Overview

The bot includes built-in monitoring capabilities:
- **Health checks** at `/health`, `/ready`, `/metrics`
- **Error tracking** with Sentry integration
- **Performance monitoring** with custom metrics
- **Uptime monitoring** with external services

## 📊 Health Check Endpoints

### Basic Health Check
```bash
curl https://your-domain.railway.app/health
# Returns: OK or UNHEALTHY
```

### Readiness Check
```bash
curl https://your-domain.railway.app/ready
# Returns: READY or NOT_READY
```

### Detailed Metrics
```bash
curl https://your-domain.railway.app/metrics
# Returns: JSON with system metrics
```

### Service Information
```bash
curl https://your-domain.railway.app/
# Returns: JSON with service details
```

## 🚀 UptimeRobot Setup (Recommended)

### Step 1: Create Account
1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Sign up for a free account
3. Verify your email

### Step 2: Create Monitor
1. Click "Add New Monitor"
2. Configure settings:
   - **Monitor Type**: HTTP(s)
   - **URL**: `https://your-domain.railway.app/health`
   - **Friendly Name**: "Token Sentiment Bot Health"
   - **Interval**: 5 minutes
   - **Alert Contacts**: Add your email
   - **Expected Response**: `OK`

### Step 3: Advanced Settings
- **Keyword Type**: Response contains
- **Keyword Value**: `OK`
- **Port**: 443
- **Timeout**: 30 seconds

### Step 4: Automated Setup (Optional)
```bash
# Install monitoring setup script
python monitoring/setup_monitoring.py your-domain.railway.app --uptimerobot-api-key YOUR_KEY
```

## 🐛 Sentry Error Tracking Setup

### Step 1: Create Sentry Account
1. Go to [sentry.io](https://sentry.io)
2. Sign up for a free account
3. Create a new organization

### Step 2: Create Project
1. Click "Create Project"
2. Select "Python" as platform
3. Choose "Generic" project type
4. Name: "Token Sentiment Bot"

### Step 3: Get DSN
1. Copy the DSN (Data Source Name)
2. Format: `https://xxxxx@xxxxx.ingest.sentry.io/xxxxx`

### Step 4: Configure Environment Variables
```bash
# For Railway
railway variables set SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
railway variables set ENVIRONMENT=production
railway variables set VERSION=1.0.0

# For Render
# Add in environment variables section:
# SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
# ENVIRONMENT=production
# VERSION=1.0.0
```

### Step 5: Verify Integration
1. Deploy your bot
2. Check Sentry dashboard for events
3. Test error tracking by triggering an error

## 📈 Alternative Monitoring Services

### Pingdom (Free Tier)
- **URL**: [pingdom.com](https://www.pingdom.com)
- **Free Plan**: 1 check, 1-minute intervals
- **Setup**: Similar to UptimeRobot

### StatusCake (Free Tier)
- **URL**: [statuscake.com](https://www.statuscake.com)
- **Free Plan**: 10 tests, 5-minute intervals
- **Setup**: Similar to UptimeRobot

### New Relic (Free Tier)
- **URL**: [newrelic.com](https://newrelic.com)
- **Free Plan**: 100GB data/month
- **Setup**: More complex, requires agent installation

## 🔧 Monitoring Configuration

### Environment Variables
```bash
# Required for Sentry
SENTRY_DSN=https://xxxxx@xxxxx.ingest.sentry.io/xxxxx
ENVIRONMENT=production
VERSION=1.0.0

# Optional
SENTRY_DEBUG=false
```

### Configuration File
The bot uses `monitoring/uptime_config.yaml` for monitoring settings:
```yaml
health_checks:
  basic:
    url: "/health"
    expected_response: "OK"
    interval_seconds: 60

alerts:
  response_time:
    warning_threshold_ms: 5000
    critical_threshold_ms: 10000
```

## 📊 Monitoring Dashboard

### Key Metrics to Monitor
1. **Uptime**: Should be >99%
2. **Response Time**: Should be <7 seconds
3. **Error Rate**: Should be <1%
4. **Memory Usage**: Should be <500MB
5. **Rate Limiting**: Track user activity

### Alert Thresholds
- **Critical**: Bot down for >5 minutes
- **Warning**: Response time >10 seconds
- **Info**: Error rate >5%

## 🛠️ Troubleshooting

### Health Check Fails
1. Check if bot is running
2. Verify webhook configuration
3. Check logs for errors
4. Verify environment variables

### Sentry Not Working
1. Verify SENTRY_DSN is set correctly
2. Check network connectivity
3. Verify Python dependencies
4. Check Sentry dashboard for events

### UptimeRobot Alerts
1. Verify monitor URL is correct
2. Check expected response format
3. Verify SSL certificate
4. Check bot logs for errors

## 📱 Mobile Monitoring

### UptimeRobot Mobile App
- Download from App Store/Google Play
- Receive push notifications
- View status on the go

### Sentry Mobile App
- Download from App Store/Google Play
- View error reports
- Monitor performance

## 🔄 Automated Monitoring

### Health Check Script
```bash
#!/bin/bash
# health_check.sh
HEALTH_URL="https://your-domain.railway.app/health"

if curl -f -s "$HEALTH_URL" | grep -q "OK"; then
    echo "✅ Bot is healthy"
    exit 0
else
    echo "❌ Bot is unhealthy"
    exit 1
fi
```

### Cron Job Setup
```bash
# Check every 5 minutes
*/5 * * * * /path/to/health_check.sh
```

## 📊 Performance Monitoring

### Built-in Metrics
- Request count and rate
- Error count and rate
- Memory usage
- Uptime duration
- Cache hit ratio

### Custom Metrics
- User activity patterns
- Network usage distribution
- Sentiment analysis accuracy
- API response times

## 🔒 Security Considerations

### Monitoring Security
- Use HTTPS for all health checks
- Don't expose sensitive data in metrics
- Rotate API keys regularly
- Monitor for unusual activity

### Data Privacy
- Sentry captures user IDs (anonymized)
- No personal data in health checks
- Logs contain minimal PII
- GDPR compliant by default

## 📚 Additional Resources

### Documentation
- [UptimeRobot API](https://uptimerobot.com/api)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [Health Check Standards](https://tools.ietf.org/html/rfc7231)

### Community
- [UptimeRobot Community](https://uptimerobot.com/forum)
- [Sentry Community](https://forum.sentry.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## 🎉 Success Metrics

### Monitoring Success Indicators
- ✅ 99%+ uptime achieved
- ✅ <7 second response times
- ✅ <1% error rate
- ✅ Real-time alerts working
- ✅ Error tracking functional

### Next Steps
1. Set up additional monitors for different endpoints
2. Configure custom alert thresholds
3. Set up performance dashboards
4. Implement automated recovery procedures 