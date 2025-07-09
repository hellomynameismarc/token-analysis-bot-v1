#!/bin/bash

# Token Sentiment Bot Starter Script

echo "🚀 Starting Token Sentiment Bot..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy env.example to .env and configure your API keys:"
    echo "   cp env.example .env"
    echo "   Then edit .env with your actual API keys"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not found in .env file"
    exit 1
fi

echo "✅ Environment configured"
echo "🤖 Starting bot..."

# Run the bot
python run_bot.py 