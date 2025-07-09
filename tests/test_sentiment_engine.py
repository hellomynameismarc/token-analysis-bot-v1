"""
Unit tests for the sentiment analysis engine.

Tests Pydantic data models, weighting logic, confidence calculations,
and rationale generation for Task 4.1.
"""

import pytest
from core.sentiment_engine import (
    SentimentSignal,
    TwitterPillarData,
    NansenPillarData, 
    FundamentalsPillarData,
    SentimentAnalysisResult,
    SentimentEngine,
    WeightingConfig,
    NormalizationConfig
)


class TestDataModels:
    """Test Pydantic data models for each pillar."""
    
    def test_twitter_pillar_data_quality_calculation(self):
        """Test Twitter data quality auto-calculation based on tweet count."""
        # High tweet count = excellent quality
        data = TwitterPillarData(sentiment_score=0.5, tweet_count=50)
        assert data.data_quality == 1.0
        
        # Medium tweet count = good quality
        data = TwitterPillarData(sentiment_score=0.3, tweet_count=20)
        assert data.data_quality == 0.8
        
        # Low tweet count = poor quality
        data = TwitterPillarData(sentiment_score=0.1, tweet_count=5)
        assert data.data_quality == 0.5
        
        # No tweets = no quality
        data = TwitterPillarData(sentiment_score=0.0, tweet_count=0)
        assert data.data_quality == 0.0
    
    def test_nansen_pillar_data_quality_calculation(self):
        """Test Nansen data quality based on flow volumes."""
        # High volume = high quality
        data = NansenPillarData(
            netflow_score=0.6,
            inflow_usd=15000.0,
            outflow_usd=5000.0
        )
        assert data.data_quality == 1.0
        
        # Medium volume = moderate quality
        data = NansenPillarData(
            netflow_score=0.2,
            inflow_usd=3000.0,
            outflow_usd=2000.0
        )
        assert data.data_quality == 0.7
        
        # Low volume = poor quality
        data = NansenPillarData(
            netflow_score=0.1,
            inflow_usd=500.0,
            outflow_usd=200.0
        )
        assert data.data_quality == 0.4
        
        # No volume = no quality
        data = NansenPillarData(
            netflow_score=0.0,
            inflow_usd=0.0,
            outflow_usd=0.0
        )
        assert data.data_quality == 0.0
    
    def test_fundamentals_pillar_calculations(self):
        """Test fundamentals volume ratio and data quality calculations."""
        # Large cap with high volume
        data = FundamentalsPillarData(
            market_cap_usd=500_000_000,
            volume_24h_usd=50_000_000,
            price_usd=10.0
        )
        assert data.volume_to_mcap_ratio == 0.1  # 50M / 500M
        assert data.data_quality == 1.0  # Large cap
        
        # Small cap with moderate volume
        data = FundamentalsPillarData(
            market_cap_usd=10_000_000,
            volume_24h_usd=100_000,
            price_usd=0.01
        )
        assert data.volume_to_mcap_ratio == 0.01  # 100K / 10M
        assert data.data_quality == 0.8  # Small/mid cap
        
        # Micro cap
        data = FundamentalsPillarData(
            market_cap_usd=500_000,
            volume_24h_usd=10_000,
            price_usd=0.001
        )
        assert data.volume_to_mcap_ratio == 0.02  # 10K / 500K
        assert data.data_quality == 0.5  # Micro cap


class TestSentimentEngine:
    """Test core sentiment engine functionality."""
    
    def test_weighted_score_calculation(self):
        """Test the weighting logic for different pillars."""
        engine = SentimentEngine()
        
        # Create sample data for all pillars
        twitter_data = TwitterPillarData(sentiment_score=0.8, tweet_count=50)  # quality=1.0
        nansen_data = NansenPillarData(
            netflow_score=0.6, inflow_usd=20000, outflow_usd=5000
        )  # quality=1.0
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=100_000_000, volume_24h_usd=5_000_000, price_usd=1.0
        )  # quality=1.0, volume_sentiment=0.5
        
        score = engine._compute_weighted_score(
            twitter_data, nansen_data, fundamentals_data
        )
        
        # Expected: 0.05*0.8 + 0.80*0.6 + 0.15*0.5 = 0.04 + 0.48 + 0.075 = 0.595
        assert abs(score - 0.595) < 0.01
    
    def test_confidence_calculation(self):
        """Test confidence calculation based on data availability and quality."""
        engine = SentimentEngine()
        
        # Full coverage with high quality
        twitter_data = TwitterPillarData(sentiment_score=0.5, tweet_count=50)
        nansen_data = NansenPillarData(
            netflow_score=0.3, inflow_usd=15000, outflow_usd=10000
        )
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=200_000_000, volume_24h_usd=10_000_000, price_usd=2.0
        )
        
        confidence = engine._compute_confidence(
            twitter_data, nansen_data, fundamentals_data
        )
        
        # Should be high confidence (near 1.0) with all pillars available
        assert confidence > 0.8
        
        # Partial coverage (missing fundamentals)
        confidence_partial = engine._compute_confidence(
            twitter_data, nansen_data, None
        )
        
        # Should be lower confidence
        assert confidence_partial < confidence
        assert confidence_partial > 0.5  # Still reasonable with 2/3 pillars

    def test_confidence_with_data_quality_downgrade(self):
        """Test confidence calculation with varying data quality scenarios."""
        engine = SentimentEngine()
        
        # High quality data across all pillars
        high_quality_twitter = TwitterPillarData(sentiment_score=0.6, tweet_count=50)  # quality=1.0
        high_quality_nansen = NansenPillarData(
            netflow_score=0.4, inflow_usd=20000, outflow_usd=5000  # quality=1.0
        )
        high_quality_fundamentals = FundamentalsPillarData(
            market_cap_usd=500_000_000, volume_24h_usd=50_000_000, price_usd=10.0  # quality=1.0
        )
        
        high_confidence = engine._compute_confidence(
            high_quality_twitter, high_quality_nansen, high_quality_fundamentals
        )
        
        # Low quality data across all pillars
        low_quality_twitter = TwitterPillarData(sentiment_score=0.2, tweet_count=5)  # quality=0.5
        low_quality_nansen = NansenPillarData(
            netflow_score=0.1, inflow_usd=500, outflow_usd=200  # quality=0.4
        )
        low_quality_fundamentals = FundamentalsPillarData(
            market_cap_usd=500_000, volume_24h_usd=10_000, price_usd=0.001  # quality=0.5
        )
        
        low_confidence = engine._compute_confidence(
            low_quality_twitter, low_quality_nansen, low_quality_fundamentals
        )
        
        # Low quality should result in significantly lower confidence
        assert low_confidence < high_confidence
        assert low_confidence < 0.6  # Should be notably degraded
        
        # Mixed quality scenario
        mixed_confidence = engine._compute_confidence(
            high_quality_twitter, low_quality_nansen, high_quality_fundamentals
        )
        
        # Mixed should be between high and low
        assert low_confidence < mixed_confidence < high_confidence

    def test_confidence_calculation_edge_cases(self):
        """Test confidence calculation with edge cases and missing data."""
        engine = SentimentEngine()
        
        # No data available
        no_data_confidence = engine._compute_confidence(None, None, None)
        assert no_data_confidence == 0.0
        
        # Only one pillar with high quality
        single_pillar_confidence = engine._compute_confidence(
            TwitterPillarData(sentiment_score=0.8, tweet_count=40), None, None
        )
        # Should be proportional to the weight of that pillar (0.05 for twitter)
        assert 0.04 < single_pillar_confidence < 0.06
        
        # Zero quality data (should not contribute to confidence)
        zero_quality_twitter = TwitterPillarData(sentiment_score=0.0, tweet_count=0)  # quality=0.0
        zero_quality_nansen = NansenPillarData(
            netflow_score=0.0, inflow_usd=0, outflow_usd=0  # quality=0.0
        )
        
        zero_confidence = engine._compute_confidence(
            zero_quality_twitter, zero_quality_nansen, None
        )
        assert zero_confidence == 0.0
        
        # One good pillar, one zero quality pillar
        mixed_zero_confidence = engine._compute_confidence(
            TwitterPillarData(sentiment_score=0.7, tweet_count=35),  # quality=1.0
            zero_quality_nansen, None
        )
        # Should only consider the good pillar
        assert 0.04 < mixed_zero_confidence < 0.06

    def test_confidence_proportional_to_coverage(self):
        """Test that confidence properly reflects data coverage and quality."""
        engine = SentimentEngine()
        
        # Perfect data for most important pillar (Nansen - 80% weight)
        nansen_only = engine._compute_confidence(
            None,
            NansenPillarData(netflow_score=0.5, inflow_usd=25000, outflow_usd=10000),
            None
        )
        
        # Perfect data for least important pillar (Fundamentals - 15% weight)
        fundamentals_only = engine._compute_confidence(
            None, None,
            FundamentalsPillarData(
                market_cap_usd=300_000_000, volume_24h_usd=20_000_000, price_usd=5.0
            )
        )
        
        # Nansen should give higher confidence due to higher weight
        assert nansen_only > fundamentals_only
        
        # Coverage with 2 most important pillars vs 2 least important
        major_pillars = engine._compute_confidence(
            TwitterPillarData(sentiment_score=0.4, tweet_count=30),  # 5% weight
            NansenPillarData(netflow_score=0.3, inflow_usd=15000, outflow_usd=8000),  # 80% weight
            None
        )
        
        minor_pillars = engine._compute_confidence(
            TwitterPillarData(sentiment_score=0.4, tweet_count=30),  # 5% weight
            None,
            FundamentalsPillarData(
                market_cap_usd=100_000_000, volume_24h_usd=5_000_000, price_usd=2.0
            )  # 15% weight
        )
        
        # Major pillars (85% weight) should give higher confidence than minor (20% weight)
        assert major_pillars > minor_pillars
    
    def test_rationale_generation(self):
        """Test generation of three-bullet rationale explanations."""
        engine = SentimentEngine()
        
        # Strong bullish signals
        twitter_data = TwitterPillarData(sentiment_score=0.7, tweet_count=40)
        nansen_data = NansenPillarData(
            netflow_score=0.8, inflow_usd=50000, outflow_usd=5000
        )
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=50_000_000, volume_24h_usd=15_000_000, price_usd=0.5
        )
        
        rationale = engine._generate_rationale(
            twitter_data, nansen_data, fundamentals_data, 0.6
        )
        
        assert len(rationale) == 3
        assert "Onchain: Strong smart money inflows" in rationale[0]
        assert "$55,000 total volume" in rationale[0]
        assert "Social: Very positive community sentiment" in rationale[1]
        assert "(40 tweets analyzed)" in rationale[1]
        assert "Fundamentals: very high trading activity" in rationale[2]
        assert "$50.0M market cap" in rationale[2]
        
        # Test missing data rationale
        rationale_missing = engine._generate_rationale(
            None, None, None, 0.0
        )
        
        assert len(rationale_missing) == 3
        assert "Onchain: Insufficient smart money data for analysis" in rationale_missing[0]
        assert "Social: Limited social media activity or data" in rationale_missing[1]
        assert "Fundamentals: Missing or insufficient market data" in rationale_missing[2]

    def test_enhanced_rationale_generation_scenarios(self):
        """Test enhanced rationale generation with various data scenarios."""
        engine = SentimentEngine()
        
        # Test bearish scenario
        twitter_data = TwitterPillarData(sentiment_score=-0.6, tweet_count=15)
        nansen_data = NansenPillarData(
            netflow_score=-0.7, inflow_usd=2000, outflow_usd=20000
        )
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=800_000, volume_24h_usd=5000, price_usd=0.001
        )
        
        rationale = engine._generate_rationale(
            twitter_data, nansen_data, fundamentals_data, -0.5
        )
        
        assert "Heavy smart money outflows" in rationale[0]
        assert "$22,000 volume" in rationale[0]
        assert "Very negative community sentiment" in rationale[1]
        assert "(15 tweets analyzed)" in rationale[1]
        assert "low trading activity" in rationale[2]
        assert "$800K market cap" in rationale[2]
        
        # Test neutral scenario with moderate activity
        twitter_data = TwitterPillarData(sentiment_score=0.1, tweet_count=25)
        nansen_data = NansenPillarData(
            netflow_score=-0.1, inflow_usd=8000, outflow_usd=10000
        )
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=75_000_000, volume_24h_usd=2_000_000, price_usd=1.5
        )
        
        rationale = engine._generate_rationale(
            twitter_data, nansen_data, fundamentals_data, 0.05
        )
        
        assert "Balanced smart money flows" in rationale[0]
        assert "$18,000 volume" in rationale[0]
        assert "Neutral community sentiment" in rationale[1]
        assert "(25 tweets analyzed)" in rationale[1]
        assert "moderate trading activity" in rationale[2]
        assert "$75.0M market cap" in rationale[2]

    def test_market_cap_formatting(self):
        """Test market cap formatting for different scales."""
        engine = SentimentEngine()
        
        # Test thousands
        assert engine._format_market_cap(500_000) == "$500K"
        assert engine._format_market_cap(999_999) == "$1000K"
        
        # Test millions
        assert engine._format_market_cap(1_500_000) == "$1.5M"
        assert engine._format_market_cap(50_000_000) == "$50.0M"
        assert engine._format_market_cap(999_999_999) == "$1000.0M"
        
        # Test billions
        assert engine._format_market_cap(1_200_000_000) == "$1.2B"
        assert engine._format_market_cap(15_500_000_000) == "$15.5B"

    def test_rationale_activity_level_classification(self):
        """Test classification of trading activity levels in fundamentals."""
        engine = SentimentEngine()
        
        # Very high activity (>15% volume/mcap ratio)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=10_000_000, volume_24h_usd=2_000_000, price_usd=1.0  # 20% ratio
        )
        rationale = engine._generate_rationale(None, None, fundamentals_data, 0.0)
        assert "very high trading activity" in rationale[2]
        
        # High activity (5-15% volume/mcap ratio)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=10_000_000, volume_24h_usd=800_000, price_usd=1.0  # 8% ratio
        )
        rationale = engine._generate_rationale(None, None, fundamentals_data, 0.0)
        assert "high trading activity" in rationale[2]
        
        # Moderate activity (1-5% volume/mcap ratio)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=10_000_000, volume_24h_usd=300_000, price_usd=1.0  # 3% ratio
        )
        rationale = engine._generate_rationale(None, None, fundamentals_data, 0.0)
        assert "moderate trading activity" in rationale[2]
        
        # Low activity (<1% volume/mcap ratio)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=10_000_000, volume_24h_usd=50_000, price_usd=1.0  # 0.5% ratio
        )
        rationale = engine._generate_rationale(None, None, fundamentals_data, 0.0)
        assert "low trading activity" in rationale[2]

    def test_rationale_sentiment_score_classification(self):
        """Test classification of sentiment scores in social rationale."""
        engine = SentimentEngine()
        
        # Very positive (>0.4)
        twitter_data = TwitterPillarData(sentiment_score=0.8, tweet_count=30)
        rationale = engine._generate_rationale(twitter_data, None, None, 0.0)
        assert "Very positive community sentiment" in rationale[1]
        
        # Positive (0.2-0.4)
        twitter_data = TwitterPillarData(sentiment_score=0.3, tweet_count=30)
        rationale = engine._generate_rationale(twitter_data, None, None, 0.0)
        assert "Positive community sentiment" in rationale[1]
        
        # Neutral (-0.2 to 0.2)
        twitter_data = TwitterPillarData(sentiment_score=0.1, tweet_count=30)
        rationale = engine._generate_rationale(twitter_data, None, None, 0.0)
        assert "Neutral community sentiment" in rationale[1]
        
        # Negative (-0.4 to -0.2)
        twitter_data = TwitterPillarData(sentiment_score=-0.3, tweet_count=30)
        rationale = engine._generate_rationale(twitter_data, None, None, 0.0)
        assert "Negative community sentiment" in rationale[1]
        
        # Very negative (<-0.4)
        twitter_data = TwitterPillarData(sentiment_score=-0.7, tweet_count=30)
        rationale = engine._generate_rationale(twitter_data, None, None, 0.0)
        assert "Very negative community sentiment" in rationale[1]

    def test_rationale_netflow_score_classification(self):
        """Test classification of netflow scores in onchain rationale."""
        engine = SentimentEngine()
        
        # Strong inflows (>0.5)
        nansen_data = NansenPillarData(netflow_score=0.8, inflow_usd=40000, outflow_usd=5000)
        rationale = engine._generate_rationale(None, nansen_data, None, 0.0)
        assert "Onchain: Strong smart money inflows" in rationale[0]
        assert "$45,000 total volume" in rationale[0]
        
        # Moderate inflows (0.2-0.5)
        nansen_data = NansenPillarData(netflow_score=0.3, inflow_usd=15000, outflow_usd=8000)
        rationale = engine._generate_rationale(None, nansen_data, None, 0.0)
        assert "Onchain: Moderate smart money inflows" in rationale[0]
        assert "$23,000 volume" in rationale[0]
        
        # Balanced (-0.2 to 0.2)
        nansen_data = NansenPillarData(netflow_score=0.1, inflow_usd=12000, outflow_usd=10000)
        rationale = engine._generate_rationale(None, nansen_data, None, 0.0)
        assert "Onchain: Balanced smart money flows" in rationale[0]
        
        # Moderate outflows (-0.5 to -0.2)
        nansen_data = NansenPillarData(netflow_score=-0.3, inflow_usd=5000, outflow_usd=15000)
        rationale = engine._generate_rationale(None, nansen_data, None, 0.0)
        assert "Onchain: Moderate smart money outflows" in rationale[0]
        
        # Heavy outflows (<-0.5)
        nansen_data = NansenPillarData(netflow_score=-0.8, inflow_usd=2000, outflow_usd=25000)
        rationale = engine._generate_rationale(None, nansen_data, None, 0.0)
        assert "Onchain: Heavy smart money outflows" in rationale[0]

    def test_sentiment_signal_classification(self):
        """Test signal classification from overall scores."""
        # Test bullish classification
        assert SentimentSignal.BULLISH == "Bullish"
        assert SentimentSignal.NEUTRAL == "Neutral"
        assert SentimentSignal.BEARISH == "Bearish"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_zero_weight_scenarios(self):
        """Test behavior when all data has zero quality."""
        engine = SentimentEngine()
        
        # No data available
        score = engine._compute_weighted_score(None, None, None)
        assert score == 0.0
        
        confidence = engine._compute_confidence(None, None, None)
        assert confidence == 0.0
    
    def test_partial_data_scenarios(self):
        """Test behavior with only some pillars available."""
        engine = SentimentEngine()
        
        # Only Twitter data
        twitter_data = TwitterPillarData(sentiment_score=0.6, tweet_count=25)
        score = engine._compute_weighted_score(twitter_data, None, None)
        assert score == 0.6  # Should equal the Twitter score
        
        # Only Nansen data
        nansen_data = NansenPillarData(
            netflow_score=-0.4, inflow_usd=2000, outflow_usd=8000
        )
        score = engine._compute_weighted_score(None, nansen_data, None)
        assert abs(score - (-0.4)) < 0.01  # Should equal the Nansen score (normalized)


class TestEdgeCasesAndNoDataScenarios:
    """Comprehensive tests for edge cases and no-data scenarios for Task 4.5."""
    
    def test_boundary_value_sentiment_scores(self):
        """Test sentiment scores at exact boundary values."""
        engine = SentimentEngine()
        
        # Test exact boundary values for sentiment classification
        boundary_scores = [-1.0, -0.4, -0.2, 0.0, 0.2, 0.4, 1.0]
        
        for score in boundary_scores:
            twitter_data = TwitterPillarData(sentiment_score=score, tweet_count=30)
            rationale = engine._generate_rationale(twitter_data, None, None, 0.0)
            
            # Should always generate valid rationale
            assert len(rationale) == 3
            assert "Social:" in rationale[1]
            assert "(30 tweets analyzed)" in rationale[1]
    
    def test_boundary_value_netflow_scores(self):
        """Test netflow scores at exact boundary values."""
        engine = SentimentEngine()
        
        # Test exact boundary values for netflow classification
        boundary_scores = [-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0]
        
        for score in boundary_scores:
            nansen_data = NansenPillarData(
                netflow_score=score, inflow_usd=10000, outflow_usd=5000
            )
            rationale = engine._generate_rationale(None, nansen_data, None, 0.0)
            
            # Should always generate valid rationale
            assert len(rationale) == 3
            assert "Onchain:" in rationale[0]
            assert "$15,000" in rationale[0]
    
    def test_extreme_volume_ratios(self):
        """Test extreme volume to market cap ratios."""
        engine = SentimentEngine()
        
        # Very low volume ratio (approaching zero)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=1_000_000_000, volume_24h_usd=1, price_usd=100.0  # 0.000000001 ratio
        )
        rationale = engine._generate_rationale(None, None, fundamentals_data, 0.0)
        assert "low trading activity" in rationale[2]
        
        # Extremely high volume ratio (>100%)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=1_000_000, volume_24h_usd=5_000_000, price_usd=1.0  # 500% ratio
        )
        rationale = engine._generate_rationale(None, None, fundamentals_data, 0.0)
        assert "very high trading activity" in rationale[2]
    
    def test_zero_quality_data_handling(self):
        """Test handling of data with zero quality scores."""
        engine = SentimentEngine()
        
        # Zero quality Twitter data (0 tweets)
        twitter_data = TwitterPillarData(sentiment_score=0.5, tweet_count=0)
        assert twitter_data.data_quality == 0.0
        
        # Zero quality Nansen data (no flows)
        nansen_data = NansenPillarData(netflow_score=0.3, inflow_usd=0, outflow_usd=0)
        assert nansen_data.data_quality == 0.0
        
        # Zero quality fundamentals (no market cap)
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=0.1, volume_24h_usd=0, price_usd=0.001  # Below minimum validation
        )
        
        # These should not contribute to weighted score
        score = engine._compute_weighted_score(twitter_data, nansen_data, None)
        assert score == 0.0  # No contribution due to zero quality
        
        confidence = engine._compute_confidence(twitter_data, nansen_data, None)
        assert confidence == 0.0  # No confidence due to zero quality
    
    def test_mixed_quality_scenarios(self):
        """Test scenarios with mixed data quality levels."""
        engine = SentimentEngine()
        
        # High quality Twitter, low quality Nansen, missing fundamentals
        high_twitter = TwitterPillarData(sentiment_score=0.7, tweet_count=50)  # quality=1.0
        low_nansen = NansenPillarData(netflow_score=0.2, inflow_usd=300, outflow_usd=200)  # quality=0.4
        
        score = engine._compute_weighted_score(high_twitter, low_nansen, None)
        confidence = engine._compute_confidence(high_twitter, low_nansen, None)
        
        # Score should be weighted by quality
        expected_twitter_contrib = 0.7 * 0.05 * 1.0  # score * weight * quality
        expected_nansen_contrib = 0.2 * 0.80 * 0.4   # score * weight * quality
        total_weight = 0.05 * 1.0 + 0.80 * 0.4
        expected_score = (expected_twitter_contrib + expected_nansen_contrib) / total_weight
        
        assert abs(score - expected_score) < 0.01
        assert 0.0 < confidence < 1.0  # Should have partial confidence
    
    def test_extreme_market_cap_values(self):
        """Test extreme market cap values for formatting and classification."""
        engine = SentimentEngine()
        
        # Very small market cap
        assert engine._format_market_cap(1000) == "$1K"
        assert engine._format_market_cap(999) == "$1K"
        
        # Very large market cap
        assert engine._format_market_cap(1_000_000_000_000) == "$1000.0B"
        
        # Test data quality with extreme values
        micro_cap = FundamentalsPillarData(
            market_cap_usd=100_000, volume_24h_usd=1000, price_usd=0.0001  # $100K cap
        )
        assert micro_cap.data_quality == 0.5  # Micro cap quality
        
        mega_cap = FundamentalsPillarData(
            market_cap_usd=2_000_000_000_000, volume_24h_usd=10_000_000_000, price_usd=1000.0  # $2T cap
        )
        assert mega_cap.data_quality == 1.0  # Large cap quality
    
    def test_single_pillar_analysis(self):
        """Test analysis with only one pillar available."""
        engine = SentimentEngine()
        
        # Only Twitter pillar
        twitter_only = TwitterPillarData(sentiment_score=0.8, tweet_count=40)
        score = engine._compute_weighted_score(twitter_only, None, None)
        confidence = engine._compute_confidence(twitter_only, None, None)
        rationale = engine._generate_rationale(twitter_only, None, None, score)
        
        assert abs(score - 0.8) < 0.01  # Should equal the Twitter score (normalized)
        assert confidence == 0.05  # Should equal Twitter weight (5%)
        assert "Very positive community sentiment" in rationale[1]
        assert "Insufficient smart money data" in rationale[0]
        assert "Missing or insufficient market data" in rationale[2]
        
        # Only Nansen pillar
        nansen_only = NansenPillarData(netflow_score=-0.6, inflow_usd=2000, outflow_usd=15000)
        score = engine._compute_weighted_score(None, nansen_only, None)
        confidence = engine._compute_confidence(None, nansen_only, None)
        
        assert abs(score - (-0.6)) < 0.01  # Should equal the Nansen score (normalized)
        assert confidence == 0.80  # Should equal Nansen weight (80%)
    
    def test_weighted_score_edge_cases(self):
        """Test weighted score calculation edge cases."""
        engine = SentimentEngine()
        
        # All pillars with maximum positive scores
        max_twitter = TwitterPillarData(sentiment_score=1.0, tweet_count=100)
        max_nansen = NansenPillarData(netflow_score=1.0, inflow_usd=100000, outflow_usd=0)
        max_fundamentals = FundamentalsPillarData(
            market_cap_usd=1_000_000_000, volume_24h_usd=200_000_000, price_usd=50.0  # 20% ratio -> clamped to 1.0
        )
        
        score = engine._compute_weighted_score(max_twitter, max_nansen, max_fundamentals)
        # Should be close to 1.0 due to high scores and clamping
        assert 0.9 <= score <= 1.0
        
        # All pillars with maximum negative scores
        min_twitter = TwitterPillarData(sentiment_score=-1.0, tweet_count=100)
        min_nansen = NansenPillarData(netflow_score=-1.0, inflow_usd=0, outflow_usd=100000)
        # Fundamentals can't be negative, so we use zero volume
        min_fundamentals = FundamentalsPillarData(
            market_cap_usd=1_000_000_000, volume_24h_usd=0, price_usd=50.0  # 0% ratio
        )
        
        score = engine._compute_weighted_score(min_twitter, min_nansen, min_fundamentals)
        # Should be very negative
        assert score <= -0.8
    
    def test_confidence_calculation_edge_cases(self):
        """Test confidence calculation with edge case scenarios."""
        engine = SentimentEngine()
        
        # Maximum confidence scenario (all high quality data)
        perfect_twitter = TwitterPillarData(sentiment_score=0.5, tweet_count=100)
        perfect_nansen = NansenPillarData(netflow_score=0.3, inflow_usd=100000, outflow_usd=50000)
        perfect_fundamentals = FundamentalsPillarData(
            market_cap_usd=5_000_000_000, volume_24h_usd=100_000_000, price_usd=100.0
        )
        
        confidence = engine._compute_confidence(perfect_twitter, perfect_nansen, perfect_fundamentals)
        assert confidence == 1.0  # Perfect coverage and quality
        
        # Minimum non-zero confidence (lowest quality data)
        poor_twitter = TwitterPillarData(sentiment_score=0.1, tweet_count=5)  # quality=0.5
        poor_nansen = NansenPillarData(netflow_score=0.05, inflow_usd=300, outflow_usd=400)  # quality=0.4
        poor_fundamentals = FundamentalsPillarData(
            market_cap_usd=200_000, volume_24h_usd=1000, price_usd=0.001  # quality=0.5
        )
        
        confidence = engine._compute_confidence(poor_twitter, poor_nansen, poor_fundamentals)
        # Should be low but non-zero
        assert 0.1 <= confidence <= 0.6
    
    def test_rationale_consistency(self):
        """Test that rationale generation is consistent and always produces 3 bullets."""
        engine = SentimentEngine()
        
        test_cases = [
            # Various combinations of present/missing data
            (None, None, None),  # All missing
            (TwitterPillarData(sentiment_score=0.5, tweet_count=20), None, None),  # Twitter only
            (None, NansenPillarData(netflow_score=0.3, inflow_usd=8000, outflow_usd=5000), None),  # Nansen only
            (None, None, FundamentalsPillarData(market_cap_usd=50_000_000, volume_24h_usd=2_000_000, price_usd=1.0)),  # Fundamentals only
        ]
        
        for twitter_data, nansen_data, fundamentals_data in test_cases:
            rationale = engine._generate_rationale(twitter_data, nansen_data, fundamentals_data, 0.0)
            
            # Always exactly 3 bullets
            assert len(rationale) == 3
            
            # Each bullet should start with the expected prefix
            assert rationale[0].startswith("• Onchain:")
            assert rationale[1].startswith("• Social:")
            assert rationale[2].startswith("• Fundamentals:")
            
            # Each bullet should be non-empty and informative
            for bullet in rationale:
                assert len(bullet) > 20  # Reasonable minimum length
                assert ":" in bullet  # Should have category prefix
    
    def test_data_validation_edge_cases(self):
        """Test data validation at the model level."""
        
        # Test Twitter data validation
        with pytest.raises(ValueError):
            TwitterPillarData(sentiment_score=1.5, tweet_count=10)  # Score too high
            
        with pytest.raises(ValueError):
            TwitterPillarData(sentiment_score=-1.5, tweet_count=10)  # Score too low
            
        with pytest.raises(ValueError):
            TwitterPillarData(sentiment_score=0.5, tweet_count=-1)  # Negative tweets
        
        # Test Nansen data validation
        with pytest.raises(ValueError):
            NansenPillarData(netflow_score=2.0, inflow_usd=1000, outflow_usd=500)  # Score too high
            
        with pytest.raises(ValueError):
            NansenPillarData(netflow_score=0.5, inflow_usd=-1000, outflow_usd=500)  # Negative inflow
        
        # Test Fundamentals data validation
        with pytest.raises(ValueError):
            FundamentalsPillarData(market_cap_usd=0, volume_24h_usd=1000, price_usd=1.0)  # Zero market cap
            
        with pytest.raises(ValueError):
            FundamentalsPillarData(market_cap_usd=1000000, volume_24h_usd=-500, price_usd=1.0)  # Negative volume 


@pytest.mark.asyncio
async def test_sentiment_analysis_result_creation():
    """Test creating a complete SentimentAnalysisResult."""
    # This would require actual API calls, so we'll test with mock data
    twitter_data = TwitterPillarData(sentiment_score=0.3, tweet_count=15)
    nansen_data = NansenPillarData(
        netflow_score=0.2, inflow_usd=8000, outflow_usd=6000
    )
    fundamentals_data = FundamentalsPillarData(
        market_cap_usd=25_000_000, volume_24h_usd=1_000_000, price_usd=0.25
    )
    
    import time
    result = SentimentAnalysisResult(
        twitter_data=twitter_data,
        nansen_data=nansen_data,
        fundamentals_data=fundamentals_data,
        overall_score=0.25,
        confidence=0.75,
        signal=SentimentSignal.BULLISH,
        rationale=[
            "• Onchain: balanced smart-money flows",
            "• Social: positive community sentiment", 
            "• Fundamentals: moderate trading volume"
        ],
        token_address="0x1234567890abcdef",
        analysis_timestamp=time.time()
    )
    
    assert result.signal == SentimentSignal.BULLISH
    assert result.confidence == 0.75
    assert len(result.rationale) == 3
    assert result.token_address == "0x1234567890abcdef"


class TestWeightingAndNormalization:
    """Test enhanced weighting and normalization configuration."""
    
    def test_weighting_config_validation(self):
        """Test that weighting config validates sum to 1.0."""
        # Valid config
        valid_config = WeightingConfig(
            nansen_weight=0.50,
            twitter_weight=0.30,
            fundamentals_weight=0.20
        )
        assert valid_config.nansen_weight == 0.50
        
        # Invalid config (doesn't sum to 1.0)
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            WeightingConfig(
                nansen_weight=0.50,
                twitter_weight=0.30,
                fundamentals_weight=0.30  # Sum = 1.1
            )
    
    def test_normalization_config_defaults(self):
        """Test normalization config default values."""
        config = NormalizationConfig()
        
        assert config.bullish_threshold == 0.2
        assert config.bearish_threshold == -0.2
        assert config.volume_sentiment_multiplier == 10.0
        assert config.max_volume_sentiment == 1.0
        assert config.min_twitter_tweets_good == 30
        assert config.min_nansen_volume_high == 10000.0
        
    def test_custom_weighting_configuration(self):
        """Test sentiment engine with custom weighting."""
        # Create custom weights (emphasis on Twitter)
        custom_weights = WeightingConfig(
            nansen_weight=0.40,      # Reduced from 0.60
            twitter_weight=0.50,     # Increased from 0.25  
            fundamentals_weight=0.10 # Reduced from 0.15
        )
        
        engine = SentimentEngine(weighting_config=custom_weights)
        weights = engine.get_current_weights()
        
        assert weights["nansen"] == 0.40
        assert weights["twitter"] == 0.50
        assert weights["fundamentals"] == 0.10
        
    def test_custom_normalization_fundamentals(self):
        """Test custom normalization for fundamentals calculation."""
        # More aggressive volume sentiment multiplier
        custom_norms = NormalizationConfig(
            volume_sentiment_multiplier=20.0,  # Double the default
            max_volume_sentiment=1.5           # Allow higher sentiment  
        )
        
        engine = SentimentEngine(normalization_config=custom_norms)
        
        # Test volume sentiment calculation with custom config
        fundamentals_data = FundamentalsPillarData(
            market_cap_usd=10_000_000,
            volume_24h_usd=100_000,  # 0.01 ratio
            price_usd=1.0
        )
        
        # With custom multiplier: 0.01 * 20 = 0.2 (vs 0.1 with default)
        score = engine._compute_weighted_score(None, None, fundamentals_data)
        assert abs(score - 0.2) < 0.01
        
    def test_config_update_methods(self):
        """Test dynamic configuration updates."""
        engine = SentimentEngine()
        
        # Update weighting config
        new_weights = WeightingConfig(
            nansen_weight=0.30,
            twitter_weight=0.60,
            fundamentals_weight=0.10
        )
        engine.update_weighting_config(new_weights)
        
        weights = engine.get_current_weights()
        assert weights["twitter"] == 0.60
        
        # Update normalization config
        new_norms = NormalizationConfig(
            bullish_threshold=0.3,
            bearish_threshold=-0.3
        )
        engine.update_normalization_config(new_norms)
        
        assert engine.norms.bullish_threshold == 0.3
        assert engine.norms.bearish_threshold == -0.3 