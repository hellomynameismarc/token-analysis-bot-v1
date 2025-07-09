#!/bin/bash

# Token Sentiment Bot Deployment Script
# This script helps deploy the bot to Railway or Render

set -e

echo "🚀 Token Sentiment Bot Deployment Script"
echo "========================================"

# Check if required environment variables are set
check_env_vars() {
    local required_vars=(
        "TELEGRAM_BOT_TOKEN"
        "NANSEN_API_KEY"
        "TWITTER_BEARER_TOKEN"
        "COINGECKO_API_KEY"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "❌ Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "   - $var"
        done
        echo ""
        echo "Please set these variables before deploying:"
        echo "export TELEGRAM_BOT_TOKEN=your_bot_token"
        echo "export NANSEN_API_KEY=your_nansen_key"
        echo "export TWITTER_BEARER_TOKEN=your_twitter_token"
        echo "export COINGECKO_API_KEY=your_coingecko_key"
        exit 1
    fi
    
    echo "✅ All required environment variables are set"
}

# Deploy to Railway
deploy_railway() {
    echo ""
    echo "🚂 Deploying to Railway..."
    
    # Check if Railway CLI is installed
    if ! command -v railway &> /dev/null; then
        echo "❌ Railway CLI not found. Please install it first:"
        echo "npm install -g @railway/cli"
        exit 1
    fi
    
    # Check if logged in
    if ! railway whoami &> /dev/null; then
        echo "❌ Not logged in to Railway. Please login first:"
        echo "railway login"
        exit 1
    fi
    
    # Set environment variables
    echo "📝 Setting environment variables..."
    railway variables set TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN"
    railway variables set NANSEN_API_KEY="$NANSEN_API_KEY"
    railway variables set TWITTER_BEARER_TOKEN="$TWITTER_BEARER_TOKEN"
    railway variables set COINGECKO_API_KEY="$COINGECKO_API_KEY"
    railway variables set USE_REDIS="false"
    
    # Deploy
    echo "🚀 Deploying application..."
    railway up
    
    # Get domain
    echo "🌐 Getting webhook URL..."
    DOMAIN=$(railway domain)
    echo "✅ Your bot is deployed at: $DOMAIN"
    
    # Set webhook
    echo "🔗 Setting Telegram webhook..."
    curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
         -H "Content-Type: application/json" \
         -d "{\"url\": \"$DOMAIN/webhook\"}"
    
    echo ""
    echo "🎉 Deployment complete!"
    echo "Your bot should now be responding to messages."
}

# Deploy to Render
deploy_render() {
    echo ""
    echo "🎨 Deploying to Render..."
    echo ""
    echo "⚠️  For Render deployment:"
    echo "1. Go to https://render.com"
    echo "2. Connect your GitHub repository"
    echo "3. Create a new Web Service"
    echo "4. Set the following environment variables:"
    echo "   - TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
    echo "   - NANSEN_API_KEY=$NANSEN_API_KEY"
    echo "   - TWITTER_BEARER_TOKEN=$TWITTER_BEARER_TOKEN"
    echo "   - COINGECKO_API_KEY=$COINGECKO_API_KEY"
    echo "   - USE_REDIS=false"
    echo "5. Set Build Command: pip install -r requirements.txt"
    echo "6. Set Start Command: python -m bot.main"
    echo ""
    echo "After deployment, set the webhook URL in Telegram."
}

# Main script
main() {
    check_env_vars
    
    echo ""
    echo "Choose deployment platform:"
    echo "1) Railway (Recommended - Free tier)"
    echo "2) Render (Free tier)"
    echo "3) Exit"
    echo ""
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            deploy_railway
            ;;
        2)
            deploy_render
            ;;
        3)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice. Please run the script again."
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 