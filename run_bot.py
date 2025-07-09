#!/usr/bin/env python3
"""
Token Sentiment Bot Runner
A simple script to run the Token Sentiment Telegram Bot
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Patch event loop if already running (for Jupyter/VSCode/interactive shells)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.main import TokenSentimentBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot"""
    try:
        # Check if .env file exists
        if not os.path.exists('.env'):
            logger.error("❌ .env file not found!")
            logger.info("📝 Please copy env.example to .env and configure your API keys:")
            logger.info("   cp env.example .env")
            logger.info("   Then edit .env with your actual API keys")
            return

        # Check required environment variables
        required_vars = ['TELEGRAM_BOT_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.info("📝 Please check your .env file and ensure all required variables are set")
            return

        logger.info("🚀 Starting Token Sentiment Bot...")
        logger.info("📊 Bot will analyze token sentiment using:")
        logger.info("   • Onchain data (60%)")
        logger.info("   • Social sentiment (25%)") 
        logger.info("   • Fundamentals (15%)")
        
        # Import and run the bot's main function
        from bot.main import main as bot_main
        
        logger.info("🤖 Starting bot...")
        logger.info("💡 Send a token address to your bot on Telegram to test it!")
        
        # Run the bot using its own main function
        await bot_main()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Error running bot: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Fallback for already running event loop
        logger.warning(f"Event loop error detected: {e}. Using nest_asyncio workaround.")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main()) 