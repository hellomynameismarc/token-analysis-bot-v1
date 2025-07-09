"""
Sentiment Analysis Engine

Aggregates data from three pillars (Twitter, Nansen, Fundamentals) with proper 
weighting (60/25/15) to compute Bullish/Neutral/Bearish signals with confidence scores.

Based on PRD requirements:
- Weight: 60% on-chain smart-money flows (Nansen), 25% Twitter sentiment, 15% fundamentals
- Output: Bullish/Neutral/Bearish with confidence % and three-bullet rationale
- Handle missing data by downgrading confidence proportionally
"""

import asyncio
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import yaml

from pydantic import BaseModel, Field, validator

from core.data_sources import (
    TwitterClient, 
    NansenClient, 
    CoinMarketCapClient,
    get_token_sentiment,
    get_nansen_netflow_score,
    get_cmc_metadata
)


class SentimentSignal(str, Enum):
    """Token sentiment signal classification."""
    BULLISH = "Bullish"
    NEUTRAL = "Neutral" 
    BEARISH = "Bearish"


# ========================= PYDANTIC DATA MODELS =========================

class TwitterPillarData(BaseModel):
    """Twitter social sentiment pillar data."""
    
    sentiment_score: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0,
        description="Compound sentiment score from -1 (bearish) to +1 (bullish)"
    )
    tweet_count: int = Field(
        ..., 
        ge=0,
        description="Number of tweets analyzed"
    )
    data_quality: float = Field(
        default=1.0,
        ge=0.0, 
        le=1.0,
        description="Data quality score (0=no data, 1=excellent data)"
    )
    
    @validator('data_quality', always=True)
    def calculate_data_quality(cls, v, values):
        """Calculate data quality based on tweet count."""
        tweet_count = values.get('tweet_count', 0)
        if tweet_count == 0:
            return 0.0
        elif tweet_count < 10:
            return 0.5  # Low data quality
        elif tweet_count < 30:
            return 0.8  # Good data quality
        else:
            return 1.0  # Excellent data quality


class NansenPillarData(BaseModel):
    """Nansen on-chain smart money flows pillar data."""
    
    netflow_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0, 
        description="Normalized netflow score from -1 (heavy outflow) to +1 (heavy inflow)"
    )
    inflow_usd: float = Field(
        ...,
        ge=0.0,
        description="Smart money inflow in USD"
    )
    outflow_usd: float = Field(
        ..., 
        ge=0.0,
        description="Smart money outflow in USD"
    )
    holder_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of token holders"
    )
    data_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Data quality score (0=no data, 1=excellent data)"
    )
    
    @validator('data_quality', always=True)
    def calculate_data_quality(cls, v, values):
        """Calculate data quality based on flow volumes."""
        inflow = values.get('inflow_usd', 0)
        outflow = values.get('outflow_usd', 0)
        total_volume = inflow + outflow
        
        if total_volume == 0:
            return 0.0  # No smart money activity
        elif total_volume < 1000:
            return 0.4  # Very low activity
        elif total_volume < 10000:
            return 0.7  # Moderate activity
        else:
            return 1.0  # High activity


class FundamentalsPillarData(BaseModel):
    """Token fundamentals pillar data (market cap, volume, price)."""
    
    market_cap_usd: float = Field(
        ...,
        gt=0,
        description="Market capitalization in USD"
    )
    volume_24h_usd: float = Field(
        ...,
        ge=0,
        description="24-hour trading volume in USD"
    )
    price_usd: float = Field(
        ...,
        gt=0,
        description="Current token price in USD"
    )
    volume_to_mcap_ratio: float = Field(
        default=0.0,
        ge=0.0,
        description="Volume to market cap ratio (indicates liquidity)"
    )
    data_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Data quality score (0=no data, 1=excellent data)"
    )
    
    @validator('volume_to_mcap_ratio', always=True)
    def calculate_volume_ratio(cls, v, values):
        """Calculate volume to market cap ratio."""
        volume = values.get('volume_24h_usd', 0)
        mcap = values.get('market_cap_usd', 1)  # Avoid division by zero
        return round(volume / mcap, 4)
    
    @validator('data_quality', always=True) 
    def calculate_data_quality(cls, v, values):
        """Calculate data quality based on market cap size."""
        mcap = values.get('market_cap_usd', 0)
        
        if mcap == 0:
            return 0.0
        elif mcap < 1_000_000:  # < $1M market cap
            return 0.5  # Micro cap, lower data quality
        elif mcap < 100_000_000:  # < $100M market cap  
            return 0.8  # Small/mid cap
        else:
            return 1.0  # Large cap, highest data quality


class SentimentAnalysisResult(BaseModel):
    """Complete sentiment analysis result with all pillars."""
    
    # Input data from each pillar
    twitter_data: Optional[TwitterPillarData] = None
    nansen_data: Optional[NansenPillarData] = None
    fundamentals_data: Optional[FundamentalsPillarData] = None
    
    # Computed results
    overall_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Weighted overall sentiment score from -1 to +1"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the analysis (0-1, based on data quality)"
    )
    signal: SentimentSignal = Field(
        ...,
        description="Final sentiment signal: Bullish/Neutral/Bearish"
    )
    
    # Explanation
    rationale: List[str] = Field(
        default_factory=list,
        description="Three-bullet explanation of the analysis"
    )
    
    # Metadata
    token_address: str = Field(..., description="Token contract address analyzed")
    analysis_timestamp: float = Field(..., description="Unix timestamp of analysis")
    



# ========================= SENTIMENT ENGINE CLASS =========================

@dataclass
class WeightingConfig:
    """Configuration for pillar weighting in sentiment analysis."""
    nansen_weight: float = 0.80      # 80% - on-chain smart money flows
    twitter_weight: float = 0.05     # 5% - social sentiment  
    fundamentals_weight: float = 0.15  # 15% - token fundamentals
    
    @staticmethod
    def from_yaml(path: str = "config.yaml"):
        try:
            with open(path, "r") as f:
                config = yaml.safe_load(f)
            weights = config.get("weights", {})
            return WeightingConfig(
                nansen_weight=weights.get("onchain", 0.80),
                twitter_weight=weights.get("social", 0.05),
                fundamentals_weight=weights.get("fundamentals", 0.15),
            )
        except Exception:
            return WeightingConfig()
    
    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = self.nansen_weight + self.twitter_weight + self.fundamentals_weight
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass  
class NormalizationConfig:
    """Configuration for normalization thresholds and parameters."""
    # Signal classification thresholds
    bullish_threshold: float = 0.2    # Score > 0.2 = Bullish
    bearish_threshold: float = -0.2   # Score < -0.2 = Bearish
    
    # Fundamentals normalization
    volume_sentiment_multiplier: float = 10.0  # Convert volume ratio to sentiment
    max_volume_sentiment: float = 1.0          # Cap volume sentiment
    
    # Data quality thresholds
    min_twitter_tweets_good: int = 30          # Excellent quality threshold
    min_twitter_tweets_fair: int = 10          # Good quality threshold
    min_nansen_volume_high: float = 10000.0    # High activity threshold
    min_nansen_volume_medium: float = 1000.0   # Moderate activity threshold
    min_fundamentals_large_cap: float = 100_000_000  # Large cap threshold 
    min_fundamentals_mid_cap: float = 1_000_000      # Mid cap threshold


class SentimentEngine:
    """
    Core sentiment analysis engine that aggregates data from three pillars
    and computes weighted sentiment signals with confidence scores.
    
    Enhanced with configurable weighting and normalization logic.
    """
    
    def __init__(self, 
                 twitter_client: Optional[TwitterClient] = None,
                 nansen_client: Optional[NansenClient] = None, 
                 cmc_client: Optional[CoinMarketCapClient] = None,
                 *,
                 weighting_config: Optional[WeightingConfig] = None,
                 normalization_config: Optional[NormalizationConfig] = None):
        """Initialize with optional pre-configured API clients and configs."""
        self.twitter_client = twitter_client
        self.nansen_client = nansen_client
        self.cmc_client = cmc_client
        # Load weights from config.yaml if present, else use default
        self.weights = weighting_config or WeightingConfig.from_yaml()
        self.norms = normalization_config or NormalizationConfig()
    
    async def analyze_token(self, 
                          token_address: str, 
                          token_symbol: Optional[str] = None,
                          *,
                          chain_id: int = 1) -> SentimentAnalysisResult:
        """
        Perform complete sentiment analysis for a token.
        
        Args:
            token_address: Contract address (e.g., "0x1234...") 
            token_symbol: Token symbol for Twitter search (e.g., "ETH")
            chain_id: Blockchain ID (1=Ethereum, 56=BSC, etc.)
            
        Returns:
            Complete sentiment analysis with signal and confidence
        """
        import time
        
        # Gather data from all three pillars in parallel
        twitter_data, nansen_data, fundamentals_data = await asyncio.gather(
            self._fetch_twitter_data(token_symbol),
            self._fetch_nansen_data(token_address, chain_id),
            self._fetch_fundamentals_data(token_symbol),
            return_exceptions=True
        )
        
        # Handle exceptions gracefully - ensure proper types
        twitter_result = twitter_data if isinstance(twitter_data, (TwitterPillarData, type(None))) else None
        nansen_result = nansen_data if isinstance(nansen_data, (NansenPillarData, type(None))) else None  
        fundamentals_result = fundamentals_data if isinstance(fundamentals_data, (FundamentalsPillarData, type(None))) else None
            
        # Compute weighted score and confidence
        overall_score = self._compute_weighted_score(
            twitter_result, nansen_result, fundamentals_result
        )
        confidence = self._compute_confidence(
            twitter_result, nansen_result, fundamentals_result
        )
        
        # Generate rationale
        rationale = self._generate_rationale(
            twitter_result, nansen_result, fundamentals_result, overall_score
        )
        
        # Determine signal from overall score using configurable thresholds
        if overall_score > self.norms.bullish_threshold:
            signal = SentimentSignal.BULLISH
        elif overall_score < self.norms.bearish_threshold:
            signal = SentimentSignal.BEARISH
        else:
            signal = SentimentSignal.NEUTRAL
        
        return SentimentAnalysisResult(
            twitter_data=twitter_result,
            nansen_data=nansen_result, 
            fundamentals_data=fundamentals_result,
            overall_score=overall_score,
            confidence=confidence,
            signal=signal,
            rationale=rationale,
            token_address=token_address,
            analysis_timestamp=time.time()
        )
    
    async def _fetch_twitter_data(self, token_symbol: Optional[str]) -> Optional[TwitterPillarData]:
        """Fetch and process Twitter sentiment data."""
        if not token_symbol:
            return None
            
        try:
            if self.twitter_client:
                result = await self.twitter_client.sentiment_for_token(token_symbol)
            else:
                result = await get_token_sentiment(token_symbol)
                
            return TwitterPillarData(
                sentiment_score=result['score'],
                tweet_count=result['tweet_count']
            )
        except Exception:
            return None
    
    async def _fetch_nansen_data(self, token_address: str, chain_id: int) -> Optional[NansenPillarData]:
        """Fetch and process Nansen smart money data."""
        try:
            if self.nansen_client:
                flows = await self.nansen_client.smart_money_netflow(
                    token_address, chain_id=chain_id
                )
                netflow_score_data = await self.nansen_client.netflow_score(
                    token_address, chain_id=chain_id  
                )
                holder_count = await self.nansen_client.holder_count(
                    token_address, chain_id=chain_id
                )
            else:
                netflow_score_data = await get_nansen_netflow_score(
                    token_address, chain_id=chain_id
                )
                flows = {
                    'inflow_usd': netflow_score_data['inflow_usd'],
                    'outflow_usd': netflow_score_data['outflow_usd']
                }
                holder_count = None  # Would need separate function call
                
            return NansenPillarData(
                netflow_score=netflow_score_data['score'],
                inflow_usd=flows['inflow_usd'],
                outflow_usd=flows['outflow_usd'],
                holder_count=holder_count
            )
        except Exception:
            return None
    
    async def _fetch_fundamentals_data(self, token_symbol: Optional[str]) -> Optional[FundamentalsPillarData]:
        """Fetch and process token fundamentals data."""
        if not token_symbol:
            return None
            
        try:
            if self.cmc_client:
                result = await self.cmc_client.token_quote(token_symbol)
            else:
                result = await get_cmc_metadata(token_symbol)
                
            return FundamentalsPillarData(
                market_cap_usd=result['market_cap_usd'],
                volume_24h_usd=result['volume_24h_usd'],
                price_usd=result['price_usd']
            )
        except Exception:
            return None
    
    def _compute_weighted_score(self, 
                              twitter_data: Optional[TwitterPillarData],
                              nansen_data: Optional[NansenPillarData], 
                              fundamentals_data: Optional[FundamentalsPillarData]) -> float:
        """
        Compute weighted sentiment score from available pillar data.
        
        Uses configurable weights and normalization parameters.
        Handles missing data gracefully by redistributing weights.
        """
        weighted_sum = 0.0
        total_weight = 0.0
        
        # Twitter pillar - configurable weight
        if twitter_data and twitter_data.data_quality > 0:
            effective_weight = self.weights.twitter_weight * twitter_data.data_quality
            weighted_sum += twitter_data.sentiment_score * effective_weight
            total_weight += effective_weight
        
        # Nansen pillar - configurable weight 
        if nansen_data and nansen_data.data_quality > 0:
            effective_weight = self.weights.nansen_weight * nansen_data.data_quality
            weighted_sum += nansen_data.netflow_score * effective_weight
            total_weight += effective_weight
            
        # Fundamentals pillar - convert volume ratio to sentiment using config
        if fundamentals_data and fundamentals_data.data_quality > 0:
            # Normalize volume/mcap ratio to sentiment score using configurable parameters
            volume_sentiment = min(
                fundamentals_data.volume_to_mcap_ratio * self.norms.volume_sentiment_multiplier,
                self.norms.max_volume_sentiment
            )
            # Clamp to [-1, 1] range for consistency
            volume_sentiment = max(-1.0, min(1.0, volume_sentiment))
            
            effective_weight = self.weights.fundamentals_weight * fundamentals_data.data_quality
            weighted_sum += volume_sentiment * effective_weight
            total_weight += effective_weight
        
        # Avoid division by zero
        if total_weight == 0:
            return 0.0
            
        return weighted_sum / total_weight
    
    def _compute_confidence(self,
                          twitter_data: Optional[TwitterPillarData],
                          nansen_data: Optional[NansenPillarData],
                          fundamentals_data: Optional[FundamentalsPillarData]) -> float:
        """
        Compute confidence score based on data availability and quality.
        
        Uses configurable weights to determine coverage and quality.
        """
        total_possible_weight = (self.weights.twitter_weight + 
                               self.weights.nansen_weight + 
                               self.weights.fundamentals_weight)
        actual_weight = 0.0
        quality_weighted_sum = 0.0
        
        # Add weight and quality for each available pillar
        if twitter_data:
            weight = self.weights.twitter_weight * twitter_data.data_quality
            actual_weight += weight
            quality_weighted_sum += weight * twitter_data.data_quality
            
        if nansen_data:
            weight = self.weights.nansen_weight * nansen_data.data_quality  
            actual_weight += weight
            quality_weighted_sum += weight * nansen_data.data_quality
            
        if fundamentals_data:
            weight = self.weights.fundamentals_weight * fundamentals_data.data_quality
            actual_weight += weight  
            quality_weighted_sum += weight * fundamentals_data.data_quality
        
        if actual_weight == 0:
            return 0.0
            
        # Confidence = (actual coverage / possible coverage) * average data quality
        coverage = actual_weight / total_possible_weight
        avg_quality = quality_weighted_sum / actual_weight if actual_weight > 0 else 0
        
        return round(coverage * avg_quality, 3)
    
    def _generate_rationale(self,
                          twitter_data: Optional[TwitterPillarData],
                          nansen_data: Optional[NansenPillarData], 
                          fundamentals_data: Optional[FundamentalsPillarData],
                          overall_score: float) -> List[str]:
        """
        Generate three-bullet rationale explaining the analysis.
        
        Provides specific, data-driven explanations for each pillar's contribution
        to the overall sentiment with contextual metrics when available.
        """
        rationale = []
        
        # Onchain rationale (Nansen) - Most important pillar (60% weight)
        if nansen_data and nansen_data.data_quality > 0:
            flow_total = nansen_data.inflow_usd + nansen_data.outflow_usd
            if nansen_data.netflow_score > 0.5:
                rationale.append(f"• Onchain: Strong smart money inflows (${flow_total:,.0f} total volume)")
            elif nansen_data.netflow_score > 0.2:
                rationale.append(f"• Onchain: Moderate smart money inflows (${flow_total:,.0f} volume)")
            elif nansen_data.netflow_score > -0.2:
                rationale.append(f"• Onchain: Balanced smart money flows (${flow_total:,.0f} volume)")
            elif nansen_data.netflow_score > -0.5:
                rationale.append(f"• Onchain: Moderate smart money outflows (${flow_total:,.0f} volume)")
            else:
                rationale.append(f"• Onchain: Heavy smart money outflows (${flow_total:,.0f} volume)")
        else:
            rationale.append("• Onchain: Insufficient smart money data for analysis")
            
        # Social rationale (Twitter) - Second pillar (25% weight)
        if twitter_data and twitter_data.data_quality > 0:
            tweet_context = f"({twitter_data.tweet_count} tweets analyzed)"
            if twitter_data.sentiment_score > 0.4:
                rationale.append(f"• Social: Very positive community sentiment {tweet_context}")
            elif twitter_data.sentiment_score > 0.2:
                rationale.append(f"• Social: Positive community sentiment {tweet_context}")
            elif twitter_data.sentiment_score > -0.2:
                rationale.append(f"• Social: Neutral community sentiment {tweet_context}")
            elif twitter_data.sentiment_score > -0.4:
                rationale.append(f"• Social: Negative community sentiment {tweet_context}")
            else:
                rationale.append(f"• Social: Very negative community sentiment {tweet_context}")
        else:
            rationale.append("• Social: Limited social media activity or data")
            
        # Fundamentals rationale (15% weight)
        if fundamentals_data and fundamentals_data.data_quality > 0:
            mcap_formatted = self._format_market_cap(fundamentals_data.market_cap_usd)
            volume_ratio = fundamentals_data.volume_to_mcap_ratio
            
            if volume_ratio > 0.15:
                activity_level = "very high"
            elif volume_ratio > 0.05:
                activity_level = "high"
            elif volume_ratio > 0.01:
                activity_level = "moderate"
            else:
                activity_level = "low"
                
            rationale.append(f"• Fundamentals: {activity_level} trading activity ({mcap_formatted} market cap)")
        else:
            rationale.append("• Fundamentals: Missing or insufficient market data")
            
        return rationale[:3]  # Ensure exactly 3 bullets
    
    def _format_market_cap(self, market_cap_usd: float) -> str:
        """Format market cap for display in rationale."""
        if market_cap_usd >= 1_000_000_000:
            return f"${market_cap_usd / 1_000_000_000:.1f}B"
        elif market_cap_usd >= 1_000_000:
            return f"${market_cap_usd / 1_000_000:.1f}M"
        else:
            return f"${market_cap_usd / 1_000:.0f}K"
    
    def update_weighting_config(self, config: WeightingConfig) -> None:
        """Update the weighting configuration."""
        self.weights = config
        
    def update_normalization_config(self, config: NormalizationConfig) -> None:
        """Update the normalization configuration."""
        self.norms = config
        
    def get_current_weights(self) -> Dict[str, float]:
        """Get current pillar weights as a dictionary."""
        return {
            "nansen": self.weights.nansen_weight,
            "twitter": self.weights.twitter_weight, 
            "fundamentals": self.weights.fundamentals_weight
        } 