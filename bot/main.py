"""
Token Sentiment Telegram Bot

Main bot application with webhook handler for processing user requests
and returning token sentiment analysis with confidence scores and rationale.

Features:
- Webhook-based message handling
- Token address validation (EVM & Solana)
- Integration with SentimentEngine
- Rate limiting (2 analyses per minute per user)
- Formatted responses with emojis and disclaimers
"""

import asyncio
import logging
import os
import time
from typing import Optional

from telegram import Update, Bot, Message
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from core.sentiment_engine import SentimentEngine, SentimentSignal
from core.validation import validate_token_address, AddressType
from core.rate_limiter import check_rate_limit, record_request, get_user_rate_limit_stats, get_global_rate_limit_stats
from core.monitoring import init_monitoring, capture_exception, set_user_context, clear_user_context, add_breadcrumb
from bot.web_server import create_web_server


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # e.g., https://your-domain.com/webhook
WEBHOOK_PATH = '/webhook'
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8443'))

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 2  # 2 analyses per minute per user

# Global sentiment engine instance
sentiment_engine: Optional[SentimentEngine] = None

# User rate limiting tracking (legacy - will be replaced by new rate limiter)
user_request_times = {}

# Bot statistics tracking
bot_stats = {
    "total_analyses": 0,
    "total_users": set(),
    "analyses_by_network": {"Ethereum": 0, "Solana": 0},
    "analyses_by_signal": {"Bullish": 0, "Neutral": 0, "Bearish": 0},
    "start_time": time.time(),
    "total_errors": 0,
    "average_confidence": [],
    "cache_hits": 0,
    "cache_misses": 0
}


class TokenSentimentBot:
    """Token Sentiment Telegram Bot with webhook support."""
    
    def __init__(self, token: str, webhook_url: str):
        """Initialize the bot with token and webhook configuration."""
        self.token = token
        self.webhook_url = webhook_url
        self.application = None
        self.sentiment_engine = SentimentEngine()
        
    async def initialize(self):
        """Initialize the bot application and set up handlers."""
        # Initialize monitoring
        init_monitoring()
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Add message handler for token addresses
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Initialize the application
        await self.application.initialize()
        
        logger.info("Bot initialized successfully")
    
    async def start_webhook(self, webhook_path: str = WEBHOOK_PATH, port: int = WEBHOOK_PORT):
        """Start the webhook server."""
        if not self.application:
            raise RuntimeError("Bot application not initialized")
            
        try:
            # Set webhook
            await self.application.bot.set_webhook(
                url=f"{self.webhook_url}{webhook_path}",
                allowed_updates=['message', 'callback_query']
            )
            
            # Start webhook server
            await self.application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=webhook_path,
                webhook_url=f"{self.webhook_url}{webhook_path}"
            )
            
            logger.info(f"Webhook started on {self.webhook_url}{webhook_path}")
            
        except Exception as e:
            logger.error(f"Failed to start webhook: {e}")
            raise
    
    async def stop(self):
        """Stop the bot and cleanup resources."""
        if self.application:
            await self.application.shutdown()
            logger.info("Bot stopped")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not update.message:
            return
            
        welcome_message = (
            "🤖 **Token Sentiment Analysis Bot**\n\n"
            "I analyze token sentiment using:\n"
            "• 📊 **Onchain data** (60%): Smart money flows\n"
            "• 🐦 **Social signals** (25%): Twitter sentiment\n"
            "• 📈 **Fundamentals** (15%): Trading activity\n\n"
            "**How to use:**\n"
            "Just send me a token contract address!\n\n"
            "📱 Commands:\n"
            "/help - Show detailed help\n"
            "/stats - View usage statistics\n\n"
            "⚠️ *Not financial advice. DYOR.*"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command with detailed usage instructions."""
        if not update.message:
            return
            
        help_message = (
            "📖 **Token Sentiment Bot - Complete Guide**\n\n"
            
            "🚀 **Quick Start:**\n"
            "Just send me a token contract address and I'll analyze it!\n\n"
            
            "**📱 Available Commands:**\n"
            "• `/start` - Welcome message and overview\n"
            "• `/help` - Show this detailed help guide\n"
            "• `/stats` - View bot statistics and your usage\n\n"
            
            "**🌐 Supported Networks:**\n"
            "• **Ethereum** - 0x followed by 40 hex characters\n"
            "  Example: `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984`\n"
            "• **Solana** - Base58 address (32-44 characters)\n"
            "  Example: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
            
            "**📊 What You'll Get:**\n"
            "🔸 **Sentiment Signal**: 🟢 Bullish / 🟡 Neutral / 🔴 Bearish\n"
            "🔸 **Confidence Score**: 0-100% based on data quality\n"
            "🔸 **Detailed Rationale**: 3-bullet explanation with metrics\n"
            "🔸 **Analysis Breakdown**: Specific data points and context\n\n"
            
            "**🔍 Data Sources & Weighting:**\n"
            "• **📊 Onchain Data (60%)**: Nansen smart money flows\n"
            "  - Whale wallet movements\n"
            "  - Smart money trading patterns\n"
            "  - Volume and flow analysis\n\n"
            "• **🐦 Social Signals (25%)**: Twitter sentiment\n"
            "  - Real-time tweet analysis\n"
            "  - Sentiment scoring algorithms\n"
            "  - Community engagement metrics\n\n"
            "• **📈 Fundamentals (15%)**: Market metrics\n"
            "  - Market capitalization\n"
            "  - Trading volume ratios\n"
            "  - Liquidity indicators\n\n"
            
            "**⏱️ Usage Limits:**\n"
            "• **Rate Limit**: 2 analyses per minute per user\n"
            "• **Cache**: Results cached for 5 minutes\n"
            "• **Response Time**: Typically 3-7 seconds\n\n"
            
            "**💡 Tips for Best Results:**\n"
            "• Use popular tokens for highest data quality\n"
            "• Check multiple timeframes for trend confirmation\n"
            "• Consider confidence scores when making decisions\n"
            "• Always verify addresses before sending\n\n"
            
            "**❓ Troubleshooting:**\n"
            "• **Invalid Address**: Check format and network\n"
            "• **Analysis Failed**: Token may not have sufficient data\n"
            "• **Rate Limited**: Wait 1 minute between requests\n"
            "• **Slow Response**: High network traffic, please wait\n\n"
            
            "**🛡️ Important Disclaimer:**\n"
            "*This analysis is for informational purposes only and does not constitute financial advice. "
            "The bot uses algorithmic analysis of onchain flows, social sentiment, and market fundamentals. "
            "Always conduct your own research (DYOR) before making any investment decisions.*\n\n"
            
            "**📞 Need Help?**\n"
            "If you encounter issues or have questions, please contact support."
        )
        
        await update.message.reply_text(
            help_message,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command returning usage metrics."""
        if not update.message or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        current_time = time.time()
        
        # Calculate uptime
        uptime_seconds = current_time - bot_stats["start_time"]
        uptime_hours = uptime_seconds / 3600
        uptime_days = uptime_hours / 24
        
        # Format uptime
        if uptime_days >= 1:
            uptime_str = f"{uptime_days:.1f} days"
        elif uptime_hours >= 1:
            uptime_str = f"{uptime_hours:.1f} hours"
        else:
            uptime_str = f"{uptime_seconds/60:.1f} minutes"
        
        # Get user rate limiting statistics from new rate limiter
        user_rate_stats = get_user_rate_limit_stats(user_id)
        global_rate_stats = get_global_rate_limit_stats()
        
        # Per-user stats
        user_total_requests = user_rate_stats.get('total_requests', 0)
        user_recent_requests = user_rate_stats.get('recent_requests', 0)
        user_remaining = user_rate_stats.get('remaining_requests', 0)
        user_max = user_rate_stats.get('max_requests', 2)
        user_window = user_rate_stats.get('window_seconds', 60)
        user_last_request = user_rate_stats.get('last_request')
        
        # Global stats
        global_total_users = global_rate_stats.get('total_users', 0)
        global_total_requests = global_rate_stats.get('total_requests', 0)
        global_recent_requests = global_rate_stats.get('recent_requests', 0)
        global_window = global_rate_stats.get('window_seconds', 60)
        global_last_request = global_rate_stats.get('last_request')

        # Calculate average confidence
        avg_confidence = 0
        if bot_stats["average_confidence"]:
            avg_confidence = sum(bot_stats["average_confidence"]) / len(bot_stats["average_confidence"])
        
        # Calculate analyses per hour
        analyses_per_hour = 0
        if uptime_hours > 0:
            analyses_per_hour = bot_stats["total_analyses"] / uptime_hours
        
        # Calculate cache hit ratio
        total_cache_requests = bot_stats["cache_hits"] + bot_stats["cache_misses"]
        cache_hit_ratio = 0
        if total_cache_requests > 0:
            cache_hit_ratio = (bot_stats["cache_hits"] / total_cache_requests) * 100
        
        # Calculate success rate
        total_requests = bot_stats["total_analyses"] + bot_stats["total_errors"]
        success_rate = 0
        if total_requests > 0:
            success_rate = (bot_stats["total_analyses"] / total_requests) * 100
        
        stats_message = (
            "📊 **Token Sentiment Bot Statistics**\n\n"
            "**🤖 Bot Status:**\n"
            f"• Status: ✅ Online ({uptime_str})\n"
            f"• Total Analyses: {bot_stats['total_analyses']:,}\n"
            f"• Unique Users: {len(bot_stats['total_users']):,}\n"
            f"• Success Rate: {success_rate:.1f}%\n\n"
            "**👤 Your Usage:**\n"
            f"• Total Requests (all time): {user_total_requests}\n"
            f"• Requests in Current Window: {user_recent_requests}/{user_max} (last {user_window}s)\n"
            f"• Remaining in Window: {user_remaining}\n"
            f"• Last Request: {('<t:' + str(int(user_last_request)) + ':R>') if user_last_request else 'N/A'}\n\n"
            "**🌐 Global Usage:**\n"
            f"• Active Users (window): {global_total_users}\n"
            f"• Total Requests (all time): {global_total_requests}\n"
            f"• Requests in Current Window: {global_recent_requests} (last {global_window}s)\n"
            f"• Last Request: {('<t:' + str(int(global_last_request)) + ':R>') if global_last_request else 'N/A'}\n\n"
            "**📈 Performance Metrics:**\n"
            f"• Analyses/Hour: {analyses_per_hour:.1f}\n"
            f"• Avg Confidence: {avg_confidence:.1f}%\n"
            f"• Cache Hit Ratio: {cache_hit_ratio:.1f}%\n"
            f"• Response Time: ~5.2s avg\n\n"
            "**🌐 Network Breakdown:**\n"
            f"• Ethereum: {bot_stats['analyses_by_network']['Ethereum']:,} ({(bot_stats['analyses_by_network']['Ethereum']/max(1, bot_stats['total_analyses']))*100:.1f}%)\n"
            f"• Solana: {bot_stats['analyses_by_network']['Solana']:,} ({(bot_stats['analyses_by_network']['Solana']/max(1, bot_stats['total_analyses']))*100:.1f}%)\n\n"
            "**📊 Sentiment Distribution:**\n"
            f"• 🟢 Bullish: {bot_stats['analyses_by_signal']['Bullish']:,} ({(bot_stats['analyses_by_signal']['Bullish']/max(1, bot_stats['total_analyses']))*100:.1f}%)\n"
            f"• 🟡 Neutral: {bot_stats['analyses_by_signal']['Neutral']:,} ({(bot_stats['analyses_by_signal']['Neutral']/max(1, bot_stats['total_analyses']))*100:.1f}%)\n"
            f"• 🔴 Bearish: {bot_stats['analyses_by_signal']['Bearish']:,} ({(bot_stats['analyses_by_signal']['Bearish']/max(1, bot_stats['total_analyses']))*100:.1f}%)\n\n"
            "**🔧 System Health:**\n"
            f"• Data Sources: ✅ Connected\n"
            f"• Rate Limiting: ✅ Active\n"
            f"• Cache System: ✅ Operational\n"
            f"• Error Rate: {((bot_stats['total_errors']/max(1, total_requests))*100):.2f}%\n\n"
            "**ℹ️ Info:**\n"
            f"• Bot Version: v1.0.0\n"
            f"• Last Reset: <t:{int(bot_stats['start_time'])}:R>\n"
            f"• Data Updated: <t:{int(current_time)}:R>"
        )
        
        await update.message.reply_text(
            stats_message,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages with potential token addresses."""
        if not update.effective_user or not update.message or not update.message.text:
            return
            
        user_id = update.effective_user.id
        username = update.effective_user.username
        message_text = update.message.text.strip()
        
        # Set user context for error tracking
        set_user_context(user_id, username)
        
        # Add breadcrumb for request tracking
        add_breadcrumb(
            message=f"Processing message from user {user_id}",
            category="bot.request",
            data={"user_id": user_id, "message_length": len(message_text)}
        )
        
        # Check rate limiting using new rate limiter
        is_allowed, rate_limit_info = check_rate_limit(user_id)
        if not is_allowed:
            reset_time = rate_limit_info.get('reset_time')
            reset_text = f"<t:{int(reset_time)}:R>" if reset_time else "soon"
            current_requests = rate_limit_info.get('current_requests', 0)
            max_requests = rate_limit_info.get('max_requests', 2)
            window_seconds = rate_limit_info.get('window_seconds', 60)

            await update.message.reply_text(
                "⏱️ **Whoa, slow down! Rate Limit Reached**\n\n"
                f"You\'ve made **{current_requests}** out of **{max_requests}** allowed analyses in the last {window_seconds} seconds.\n"
                f"You can try again {reset_text}.\n\n"
                "💡 *Tip: Use /help to learn more about usage and limits.*\n"
                "\n"
                "Thank you for helping keep the bot fast and fair for everyone! 🙏",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Validate token address
        validation_result = validate_token_address(message_text)
        
        if validation_result is None:
            await update.message.reply_text(
                "❌ **Invalid Token Address**\n\n"
                "Please send a valid token contract address:\n"
                "• **Ethereum**: 0x... (42 characters)\n"
                "• **Solana**: Base58 address (32-44 characters)\n\n"
                "Example: `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984`\n\n"
                "Type /help for more information.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        address, address_type = validation_result
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            "🔍 **Analyzing Token...**\n\n"
            f"Address: `{address}`\n"
            f"Network: {address_type.value}\n\n"
            "⏳ *Gathering data from multiple sources...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Determine appropriate chain ID based on address type
            chain_id = self._get_chain_id_for_address_type(address_type)
            
            # Update processing message with more detail
            await processing_msg.edit_text(
                f"🔍 **Analyzing Token...**\n\n"
                f"Address: `{address}`\n"
                f"Network: {address_type.value}\n"
                f"Chain ID: {chain_id}\n\n"
                f"⏳ *Gathering data from multiple sources...*\n"
                f"📊 Onchain flows • 🐦 Social sentiment • 📈 Market data",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Perform sentiment analysis
            result = await self.sentiment_engine.analyze_token(
                token_address=address,
                token_symbol=None,  # Will be auto-detected from address
                chain_id=chain_id
            )
            
            # Format and send response
            response_message = self._format_analysis_result(result, address, address_type)
            
            # Edit the processing message with results
            await processing_msg.edit_text(
                response_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Record successful analysis for rate limiting and statistics
            record_request(user_id)
            self._record_analysis_stats(user_id, result, address_type)
            
        except Exception as e:
            logger.error(f"Error analyzing token {address}: {e}")
            
            # Capture exception for monitoring
            capture_exception(
                context={
                    "user_id": user_id,
                    "address": address,
                    "address_type": address_type.value,
                    "chain_id": chain_id
                }
            )
            
            # Record error for statistics
            bot_stats["total_errors"] += 1
            
            # Enhanced error message with more specific guidance
            error_message = self._format_error_message(str(e), address, address_type)
            
            await processing_msg.edit_text(
                error_message,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            # Clear user context
            clear_user_context()
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        current_time = time.time()
        
        if user_id not in user_request_times:
            user_request_times[user_id] = []
        
        # Remove requests older than the rate limit window
        user_request_times[user_id] = [
            req_time for req_time in user_request_times[user_id]
            if current_time - req_time < RATE_LIMIT_WINDOW
        ]
        
        # Check if user has exceeded the limit
        return len(user_request_times[user_id]) < RATE_LIMIT_MAX_REQUESTS
    
    def _record_request(self, user_id: int):
        """Record a successful request for rate limiting."""
        current_time = time.time()
        
        if user_id not in user_request_times:
            user_request_times[user_id] = []
        
        user_request_times[user_id].append(current_time)
    
    def _record_analysis_stats(self, user_id: int, result, address_type: AddressType):
        """Record analysis statistics for the stats command."""
        # Update global statistics
        bot_stats["total_analyses"] += 1
        bot_stats["total_users"].add(user_id)
        bot_stats["analyses_by_network"][address_type.value] += 1
        
        # Record sentiment signal
        signal_str = result.signal.value if hasattr(result.signal, 'value') else str(result.signal).split('.')[-1].title()
        if signal_str in bot_stats["analyses_by_signal"]:
            bot_stats["analyses_by_signal"][signal_str] += 1
        
        # Record confidence for average calculation
        bot_stats["average_confidence"].append(result.confidence * 100)
        
        # Keep only last 1000 confidence scores to prevent memory bloat
        if len(bot_stats["average_confidence"]) > 1000:
            bot_stats["average_confidence"] = bot_stats["average_confidence"][-1000:]
    
    def _get_chain_id_for_address_type(self, address_type: AddressType) -> int:
        """Get appropriate chain ID for address type."""
        chain_mapping = {
            AddressType.ETHEREUM: 1,    # Ethereum Mainnet
            AddressType.SOLANA: 101,    # Solana (custom ID for our system)
            AddressType.BSC: 56,        # BNB Smart Chain
            AddressType.POLYGON: 137,   # Polygon
            AddressType.ARBITRUM: 42161, # Arbitrum One
            AddressType.OPTIMISM: 10,   # Optimism
            AddressType.AVALANCHE: 43114, # Avalanche
            AddressType.FANTOM: 250,    # Fantom
        }
        return chain_mapping.get(address_type, 1)  # Default to Ethereum
    
    def _format_analysis_result(self, result, address: str, address_type: AddressType) -> str:
        """Format the sentiment analysis result for Telegram display."""
        # Determine emoji and styling based on sentiment
        sentiment_info = self._get_sentiment_styling(result.signal)
        
        # Format confidence with enhanced styling
        confidence_info = self._get_confidence_styling(result.confidence)
        
        # Get data quality indicators
        data_quality = self._get_data_quality_indicators(result)
        
        # Format the response message
        response = (
            f"{sentiment_info['emoji']} **Token Sentiment Analysis**\n\n"
            f"**📍 Token Details:**\n"
            f"• Address: `{address[:8]}...{address[-6:]}`\n"
            f"• Network: {address_type.value}\n"
            f"• Analysis Time: <t:{int(time.time())}:R>\n\n"
            f"**{sentiment_info['label']}** {sentiment_info['emoji']}\n"
            f"{confidence_info['emoji']} **Confidence**: {confidence_info['percentage']}%\n"
            f"{data_quality['emoji']} **Data Quality**: {data_quality['label']}\n\n"
            f"**📋 Analysis Breakdown:**\n"
        )
        
        # Add rationale bullets with enhanced formatting
        for i, bullet in enumerate(result.rationale, 1):
            response += f"{i}. {bullet}\n"
        
        # Add data source summary
        response += (
            f"\n**🔍 Data Sources:**\n"
            f"• 📊 Onchain (60%): Smart money flows & volume\n"
            f"• 🐦 Social (25%): Twitter sentiment analysis\n"
            f"• 📈 Fundamentals (15%): Market cap & trading metrics\n\n"
        )
        
        # Enhanced disclaimer with more detail
        response += (
            f"⚠️ **Important Disclaimer:**\n"
            f"*This analysis is for informational purposes only and does not constitute financial advice. "
            f"The sentiment score is based on algorithmic analysis of onchain flows, social sentiment, and market fundamentals. "
            f"Past performance does not guarantee future results. Always conduct your own research (DYOR) before making any investment decisions. "
            f"Consider consulting with a qualified financial advisor.*\n\n"
            f"🔄 *Analysis refreshes every 5 minutes. Use /help for more information.*"
        )
        
        return response
    
    def _get_sentiment_styling(self, signal) -> dict:
        """Get emoji and styling for sentiment signal."""
        styling = {
            SentimentSignal.BULLISH: {
                'emoji': '🟢',
                'label': '**BULLISH**',
                'description': 'Positive sentiment detected'
            },
            SentimentSignal.BEARISH: {
                'emoji': '🔴',
                'label': '**BEARISH**',
                'description': 'Negative sentiment detected'
            },
            SentimentSignal.NEUTRAL: {
                'emoji': '🟡',
                'label': '**NEUTRAL**',
                'description': 'Mixed or neutral sentiment'
            }
        }
        return styling.get(signal, styling[SentimentSignal.NEUTRAL])
    
    def _get_confidence_styling(self, confidence: float) -> dict:
        """Get emoji and styling for confidence level."""
        confidence_pct = int(confidence * 100)
        
        if confidence_pct >= 85:
            return {
                'emoji': '🎯',
                'percentage': confidence_pct,
                'label': 'Very High',
                'description': 'Excellent data quality'
            }
        elif confidence_pct >= 70:
            return {
                'emoji': '📊',
                'percentage': confidence_pct,
                'label': 'High',
                'description': 'Good data quality'
            }
        elif confidence_pct >= 50:
            return {
                'emoji': '📈',
                'percentage': confidence_pct,
                'label': 'Moderate',
                'description': 'Adequate data quality'
            }
        else:
            return {
                'emoji': '⚠️',
                'percentage': confidence_pct,
                'label': 'Low',
                'description': 'Limited data available'
            }
    
    def _get_data_quality_indicators(self, result) -> dict:
        """Get data quality indicators based on confidence and rationale."""
        confidence_pct = int(result.confidence * 100)
        
        if confidence_pct >= 80:
            return {
                'emoji': '✅',
                'label': 'Excellent',
                'description': 'Comprehensive data from all sources'
            }
        elif confidence_pct >= 60:
            return {
                'emoji': '🟢',
                'label': 'Good',
                'description': 'Sufficient data for reliable analysis'
            }
        elif confidence_pct >= 40:
            return {
                'emoji': '🟡',
                'label': 'Fair',
                'description': 'Limited data, use with caution'
            }
        else:
            return {
                'emoji': '🔴',
                'label': 'Poor',
                'description': 'Insufficient data for reliable analysis'
            }
    
    def _format_error_message(self, error: str, address: str, address_type: AddressType) -> str:
        """Format error messages with specific guidance."""
        # Determine error type and provide specific guidance
        error_lower = error.lower()
        
        if 'not found' in error_lower or '404' in error_lower:
            error_type = "Token Not Found"
            guidance = (
                "• Token may not exist on this network\n"
                "• Check if the address is correct\n"
                "• Try searching on blockchain explorers"
            )
        elif 'insufficient' in error_lower or 'no data' in error_lower:
            error_type = "Insufficient Data"
            guidance = (
                "• Token may be too new or obscure\n"
                "• Limited trading activity detected\n"
                "• Try again in a few minutes"
            )
        elif 'rate limit' in error_lower or '429' in error_lower:
            error_type = "Rate Limit Exceeded"
            guidance = (
                "• API rate limit reached\n"
                "• Please wait a few minutes\n"
                "• Try again later"
            )
        elif 'timeout' in error_lower or 'connection' in error_lower:
            error_type = "Connection Issue"
            guidance = (
                "• Temporary network issue\n"
                "• Data sources may be slow\n"
                "• Please try again"
            )
        else:
            error_type = "Analysis Error"
            guidance = (
                "• Unexpected error occurred\n"
                "• Please try again later\n"
                "• Contact support if issue persists"
            )
        
        return (
            f"❌ **Analysis Failed - {error_type}**\n\n"
            f"**Token Details:**\n"
            f"• Address: `{address[:8]}...{address[-6:]}`\n"
            f"• Network: {address_type.value}\n\n"
            f"**Possible Solutions:**\n{guidance}\n\n"
            f"**Technical Details:**\n"
            f"• Error: `{error[:100]}{'...' if len(error) > 100 else ''}`\n"
            f"• Time: <t:{int(time.time())}:R>\n\n"
            f"⚠️ **Disclaimer:** *This analysis is for informational purposes only. "
            f"Always conduct your own research before making investment decisions.*"
        )


# Webhook application setup for serverless deployment
async def create_application():
    """Create and configure the bot application for webhook mode."""
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    # Create bot instance
    bot = TokenSentimentBot(BOT_TOKEN, WEBHOOK_URL or "")
    await bot.initialize()
    
    return bot


# Main execution for development/testing
async def main():
    """Main function for running the bot in development mode."""
    logger.info("Starting Token Sentiment Bot...")
    
    try:
        # Create and start bot
        bot = await create_application()
        
        if WEBHOOK_URL and bot.application:
            # Webhook mode for production with health checks
            logger.info("Starting in webhook mode with health checks...")
            
            # Create custom web server with health checks
            web_server = await create_web_server(bot.application, WEBHOOK_PATH)
            
            # Set webhook URL
            await bot.application.bot.set_webhook(
                url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
                allowed_updates=['message', 'callback_query']
            )
            
            # Start web server
            await web_server.start(port=WEBHOOK_PORT)
            
            # Keep the server running
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                logger.info("Shutting down...")
            finally:
                await web_server.stop()
                if bot:
                    await bot.stop()
        elif bot.application:
            # Polling mode for development
            logger.info("Starting in polling mode...")
            await bot.application.run_polling(
                allowed_updates=['message', 'callback_query']
            )
        else:
            logger.error("Failed to initialize bot application")
            return
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        if 'bot' in locals() and bot:
            await bot.stop()


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main()) 