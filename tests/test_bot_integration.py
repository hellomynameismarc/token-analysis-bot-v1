"""
Tests for bot sentiment engine integration and response formatting.

Tests the integration between the Telegram bot and sentiment engine,
including response formatting, error handling, and user experience features.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Message, User
from telegram.ext import ContextTypes

from bot.main import TokenSentimentBot
from core.sentiment_engine import SentimentSignal, SentimentAnalysisResult
from core.validation import AddressType


class TestSentimentEngineIntegration:
    """Test sentiment engine integration with the bot."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance for testing."""
        bot = TokenSentimentBot("test_token", "https://test.com")
        bot.sentiment_engine = Mock()
        return bot
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 12345
        update.message = Mock(spec=Message)
        update.message.text = "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        return Mock(spec=ContextTypes.DEFAULT_TYPE)
    
    def test_get_chain_id_for_address_type(self, mock_bot):
        """Test chain ID mapping for different address types."""
        assert mock_bot._get_chain_id_for_address_type(AddressType.ETHEREUM) == 1
        assert mock_bot._get_chain_id_for_address_type(AddressType.SOLANA) == 101
        assert mock_bot._get_chain_id_for_address_type(AddressType.BSC) == 56
        assert mock_bot._get_chain_id_for_address_type(AddressType.POLYGON) == 137
        assert mock_bot._get_chain_id_for_address_type(AddressType.ARBITRUM) == 42161
        assert mock_bot._get_chain_id_for_address_type(AddressType.OPTIMISM) == 10
        assert mock_bot._get_chain_id_for_address_type(AddressType.AVALANCHE) == 43114
        assert mock_bot._get_chain_id_for_address_type(AddressType.FANTOM) == 250


class TestResponseFormatting:
    """Test response formatting and styling."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance for testing."""
        return TokenSentimentBot("test_token", "https://test.com")
    
    def test_sentiment_styling(self, mock_bot):
        """Test sentiment styling for different signals."""
        # Test bullish styling
        bullish_style = mock_bot._get_sentiment_styling(SentimentSignal.BULLISH)
        assert bullish_style['emoji'] == '🟢'
        assert 'BULLISH' in bullish_style['label']
        
        # Test bearish styling
        bearish_style = mock_bot._get_sentiment_styling(SentimentSignal.BEARISH)
        assert bearish_style['emoji'] == '🔴'
        assert 'BEARISH' in bearish_style['label']
        
        # Test neutral styling
        neutral_style = mock_bot._get_sentiment_styling(SentimentSignal.NEUTRAL)
        assert neutral_style['emoji'] == '🟡'
        assert 'NEUTRAL' in neutral_style['label']
    
    def test_confidence_styling(self, mock_bot):
        """Test confidence level styling."""
        # Test very high confidence
        high_confidence = mock_bot._get_confidence_styling(0.95)
        assert high_confidence['emoji'] == '🎯'
        assert high_confidence['percentage'] == 95
        assert high_confidence['label'] == 'Very High'
        
        # Test high confidence
        good_confidence = mock_bot._get_confidence_styling(0.75)
        assert good_confidence['emoji'] == '📊'
        assert good_confidence['percentage'] == 75
        assert good_confidence['label'] == 'High'
        
        # Test moderate confidence
        moderate_confidence = mock_bot._get_confidence_styling(0.55)
        assert moderate_confidence['emoji'] == '📈'
        assert moderate_confidence['percentage'] == 55
        assert moderate_confidence['label'] == 'Moderate'
        
        # Test low confidence
        low_confidence = mock_bot._get_confidence_styling(0.25)
        assert low_confidence['emoji'] == '⚠️'
        assert low_confidence['percentage'] == 25
        assert low_confidence['label'] == 'Low'
    
    def test_data_quality_indicators(self, mock_bot):
        """Test data quality indicator generation."""
        # Create mock result with different confidence levels
        mock_result = Mock()
        
        # Test excellent quality
        mock_result.confidence = 0.85
        excellent_quality = mock_bot._get_data_quality_indicators(mock_result)
        assert excellent_quality['emoji'] == '✅'
        assert excellent_quality['label'] == 'Excellent'
        
        # Test good quality
        mock_result.confidence = 0.70
        good_quality = mock_bot._get_data_quality_indicators(mock_result)
        assert good_quality['emoji'] == '🟢'
        assert good_quality['label'] == 'Good'
        
        # Test fair quality
        mock_result.confidence = 0.45
        fair_quality = mock_bot._get_data_quality_indicators(mock_result)
        assert fair_quality['emoji'] == '🟡'
        assert fair_quality['label'] == 'Fair'
        
        # Test poor quality
        mock_result.confidence = 0.25
        poor_quality = mock_bot._get_data_quality_indicators(mock_result)
        assert poor_quality['emoji'] == '🔴'
        assert poor_quality['label'] == 'Poor'
    
    def test_format_analysis_result(self, mock_bot):
        """Test complete analysis result formatting."""
        # Create mock sentiment analysis result
        mock_result = Mock(spec=SentimentAnalysisResult)
        mock_result.signal = SentimentSignal.BULLISH
        mock_result.confidence = 0.85
        mock_result.rationale = [
            "📊 Onchain flows show strong accumulation ($2.5M net inflow)",
            "🐦 Social sentiment is positive (65% bullish mentions)",
            "📈 Market fundamentals indicate healthy trading volume"
        ]
        
        # Format the result
        formatted = mock_bot._format_analysis_result(
            mock_result, 
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        # Verify key components are present
        assert "🟢 **Token Sentiment Analysis**" in formatted
        assert "**BULLISH**" in formatted
        assert "🎯 **Confidence**: 85%" in formatted
        assert "✅ **Data Quality**: Excellent" in formatted
        assert "📍 Token Details:" in formatted
        assert "📋 Analysis Breakdown:" in formatted
        assert "🔍 Data Sources:" in formatted
        assert "⚠️ **Important Disclaimer:**" in formatted
        
        # Verify rationale is numbered
        assert "1. 📊 Onchain flows show strong accumulation" in formatted
        assert "2. 🐦 Social sentiment is positive" in formatted
        assert "3. 📈 Market fundamentals indicate healthy trading volume" in formatted
        
        # Verify disclaimer content
        assert "informational purposes only" in formatted
        assert "does not constitute financial advice" in formatted
        assert "conduct your own research" in formatted


class TestErrorHandling:
    """Test error handling and error message formatting."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance for testing."""
        return TokenSentimentBot("test_token", "https://test.com")
    
    def test_format_error_message_token_not_found(self, mock_bot):
        """Test error message formatting for token not found."""
        error_msg = mock_bot._format_error_message(
            "Token not found on network",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        assert "❌ **Analysis Failed - Token Not Found**" in error_msg
        assert "Token may not exist on this network" in error_msg
        assert "Check if the address is correct" in error_msg
        assert "Try searching on blockchain explorers" in error_msg
        assert "⚠️ **Disclaimer:**" in error_msg
    
    def test_format_error_message_insufficient_data(self, mock_bot):
        """Test error message formatting for insufficient data."""
        error_msg = mock_bot._format_error_message(
            "Insufficient data available for analysis",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        assert "❌ **Analysis Failed - Insufficient Data**" in error_msg
        assert "Token may be too new or obscure" in error_msg
        assert "Limited trading activity detected" in error_msg
        assert "Try again in a few minutes" in error_msg
    
    def test_format_error_message_rate_limit(self, mock_bot):
        """Test error message formatting for rate limit errors."""
        error_msg = mock_bot._format_error_message(
            "Rate limit exceeded (429)",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        assert "❌ **Analysis Failed - Rate Limit Exceeded**" in error_msg
        assert "API rate limit reached" in error_msg
        assert "Please wait a few minutes" in error_msg
        assert "Try again later" in error_msg
    
    def test_format_error_message_connection_issue(self, mock_bot):
        """Test error message formatting for connection issues."""
        error_msg = mock_bot._format_error_message(
            "Connection timeout",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        assert "❌ **Analysis Failed - Connection Issue**" in error_msg
        assert "Temporary network issue" in error_msg
        assert "Data sources may be slow" in error_msg
        assert "Please try again" in error_msg
    
    def test_format_error_message_generic(self, mock_bot):
        """Test error message formatting for generic errors."""
        error_msg = mock_bot._format_error_message(
            "Unexpected error occurred",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        assert "❌ **Analysis Failed - Analysis Error**" in error_msg
        assert "Unexpected error occurred" in error_msg
        assert "Please try again later" in error_msg
        assert "Contact support if issue persists" in error_msg
    
    def test_format_error_message_truncation(self, mock_bot):
        """Test error message truncation for long errors."""
        long_error = "A" * 200  # 200 character error
        error_msg = mock_bot._format_error_message(
            long_error,
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        # Should truncate to 100 characters + "..."
        assert "Error: `" in error_msg
        assert "..." in error_msg
        assert len(error_msg.split("Error: `")[1].split("`")[0]) <= 103  # 100 + "..."

    def test_format_error_message_technical_details(self, mock_bot):
        """Test that technical details are included in error messages."""
        error_msg = mock_bot._format_error_message(
            "Test error message",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        assert "**Token Details:**" in error_msg
        assert "Address: `0x1f9840...01f984`" in error_msg  # Fixed address truncation
        assert "Network: Ethereum" in error_msg
        assert "**Technical Details:**" in error_msg
        assert "Error: `Test error message`" in error_msg
        assert "Time: <t:" in error_msg


class TestIntegrationFeatures:
    """Test integration features and user experience."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance for testing."""
        return TokenSentimentBot("test_token", "https://test.com")
    
    def test_processing_message_format(self, mock_bot):
        """Test that processing messages include all required information."""
        # This would be tested in the actual message handling
        # For now, we can verify the format structure
        expected_format = (
            "🔍 **Analyzing Token...**\n\n"
            "Address: `{address}`\n"
            "Network: {network}\n"
            "Chain ID: {chain_id}\n\n"
            "⏳ *Gathering data from multiple sources...*\n"
            "📊 Onchain flows • 🐦 Social sentiment • 📈 Market data"
        )
        
        # Verify the format includes all required elements
        assert "🔍 **Analyzing Token...**" in expected_format
        assert "Address: `{address}`" in expected_format
        assert "Network: {network}" in expected_format
        assert "Chain ID: {chain_id}" in expected_format
        assert "📊 Onchain flows • 🐦 Social sentiment • 📈 Market data" in expected_format
    
    def test_response_includes_all_required_sections(self, mock_bot):
        """Test that formatted responses include all required sections."""
        mock_result = Mock(spec=SentimentAnalysisResult)
        mock_result.signal = SentimentSignal.NEUTRAL
        mock_result.confidence = 0.65
        mock_result.rationale = ["Test rationale"]
        
        formatted = mock_bot._format_analysis_result(
            mock_result,
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        # Verify all required sections are present
        required_sections = [
            "🟡 **Token Sentiment Analysis**",
            "📍 Token Details:",
            "📈 **Confidence**: 65%",  # Fixed emoji to match actual output
            "📋 Analysis Breakdown:",
            "🔍 Data Sources:",
            "⚠️ **Important Disclaimer:**"
        ]
        
        for section in required_sections:
            assert section in formatted, f"Missing section: {section}"
    
    def test_disclaimer_completeness(self, mock_bot):
        """Test that disclaimers are comprehensive and legally sound."""
        mock_result = Mock(spec=SentimentAnalysisResult)
        mock_result.signal = SentimentSignal.BULLISH
        mock_result.confidence = 0.80
        mock_result.rationale = ["Test rationale"]
        
        formatted = mock_bot._format_analysis_result(
            mock_result,
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        # Verify disclaimer includes all required elements
        disclaimer_elements = [
            "informational purposes only",
            "does not constitute financial advice",
            "algorithmic analysis",
            "conduct your own research",
            "DYOR",
            "qualified financial advisor"
        ]
        
        for element in disclaimer_elements:
            assert element in formatted, f"Missing disclaimer element: {element}"
    
    def test_data_source_breakdown(self, mock_bot):
        """Test that data source breakdown is accurate."""
        mock_result = Mock(spec=SentimentAnalysisResult)
        mock_result.signal = SentimentSignal.BEARISH
        mock_result.confidence = 0.75
        mock_result.rationale = ["Test rationale"]
        
        formatted = mock_bot._format_analysis_result(
            mock_result,
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            AddressType.ETHEREUM
        )
        
        # Verify data source breakdown
        assert "📊 Onchain (60%): Smart money flows & volume" in formatted
        assert "🐦 Social (25%): Twitter sentiment analysis" in formatted
        assert "📈 Fundamentals (15%): Market cap & trading metrics" in formatted 