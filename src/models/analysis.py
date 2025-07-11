"""Analysis result models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class Recommendation(str, Enum):
    """Investment recommendation."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TrendDirection(str, Enum):
    """Trend direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RiskLevel(str, Enum):
    """Risk level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class SentimentLevel(str, Enum):
    """Sentiment level."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class TechnicalIndicators(BaseModel):
    """Technical analysis indicators."""
    
    # Moving averages
    sma_20: Optional[float] = Field(None, description="20-day Simple Moving Average")
    sma_50: Optional[float] = Field(None, description="50-day Simple Moving Average")
    sma_200: Optional[float] = Field(None, description="200-day Simple Moving Average")
    
    # RSI
    rsi: Optional[float] = Field(None, ge=0, le=100, description="Relative Strength Index")
    
    # MACD
    macd: Optional[float] = Field(None, description="MACD line")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    
    # Bollinger Bands
    bb_upper: Optional[float] = Field(None, description="Upper Bollinger Band")
    bb_middle: Optional[float] = Field(None, description="Middle Bollinger Band")
    bb_lower: Optional[float] = Field(None, description="Lower Bollinger Band")
    
    # Volume
    volume_avg: Optional[float] = Field(None, description="Average volume")
    volume_ratio: Optional[float] = Field(None, description="Current volume ratio")
    
    # Volatility
    volatility: Optional[float] = Field(None, description="Historical volatility")


class TechnicalAnalysis(BaseModel):
    """Technical analysis results."""
    
    indicators: TechnicalIndicators = Field(..., description="Technical indicators")
    trend: TrendDirection = Field(..., description="Overall trend direction")
    
    # Support and resistance
    support_level: Optional[float] = Field(None, description="Support level")
    resistance_level: Optional[float] = Field(None, description="Resistance level")
    
    # Patterns
    chart_patterns: List[str] = Field(default_factory=list, description="Identified chart patterns")
    
    # Signals
    buy_signals: List[str] = Field(default_factory=list, description="Buy signals")
    sell_signals: List[str] = Field(default_factory=list, description="Sell signals")
    
    # Overall technical score
    technical_score: float = Field(..., ge=0, le=1, description="Technical analysis score")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in analysis")
    
    summary: str = Field(..., description="Technical analysis summary")


class NewsItem(BaseModel):
    """News item model."""
    
    title: str = Field(..., description="News title")
    url: str = Field(..., description="News URL")
    published_date: datetime = Field(..., description="Publication date")
    source: str = Field(..., description="News source")
    snippet: Optional[str] = Field(None, description="News snippet")
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1, description="Sentiment score")


class SentimentAnalysis(BaseModel):
    """Sentiment analysis results."""
    
    sentiment_level: SentimentLevel = Field(..., description="Overall sentiment level")
    sentiment_score: float = Field(..., ge=-1, le=1, description="Sentiment score (-1 to 1)")
    
    # News sentiment
    news_sentiment: SentimentLevel = Field(..., description="News sentiment")
    news_count: int = Field(default=0, description="Number of news articles analyzed")
    recent_news: List[NewsItem] = Field(default_factory=list, description="Recent news items")
    
    # Social sentiment (if available)
    social_sentiment: Optional[SentimentLevel] = Field(None, description="Social media sentiment")
    social_mentions: Optional[int] = Field(None, description="Social media mentions")
    
    confidence: float = Field(..., ge=0, le=1, description="Confidence in analysis")
    summary: str = Field(..., description="Sentiment analysis summary")


class EventItem(BaseModel):
    """Event item model."""
    
    event_type: str = Field(..., description="Type of event")
    event_date: datetime = Field(..., description="Event date")
    description: str = Field(..., description="Event description")
    importance: str = Field(..., description="Event importance level")
    potential_impact: str = Field(..., description="Potential market impact")


class EventAnalysis(BaseModel):
    """Event analysis results."""
    
    upcoming_events: List[EventItem] = Field(default_factory=list, description="Upcoming events")
    earnings_date: Optional[datetime] = Field(None, description="Next earnings date")
    dividend_date: Optional[datetime] = Field(None, description="Next dividend date")
    
    # Event impact assessment
    positive_catalysts: List[str] = Field(default_factory=list, description="Positive catalysts")
    negative_catalysts: List[str] = Field(default_factory=list, description="Negative catalysts")
    
    overall_impact: str = Field(..., description="Overall event impact assessment")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in analysis")


class RiskMetrics(BaseModel):
    """Risk assessment metrics."""
    
    # Volatility measures
    price_volatility: Optional[float] = Field(None, description="Price volatility")
    beta: Optional[float] = Field(None, description="Beta coefficient")
    
    # Drawdown measures
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    current_drawdown: Optional[float] = Field(None, description="Current drawdown")
    
    # Liquidity measures
    avg_volume: Optional[float] = Field(None, description="Average trading volume")
    bid_ask_spread: Optional[float] = Field(None, description="Bid-ask spread")
    
    # Correlation measures
    market_correlation: Optional[float] = Field(None, description="Market correlation")
    sector_correlation: Optional[float] = Field(None, description="Sector correlation")


class RiskAssessment(BaseModel):
    """Risk assessment results."""
    
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    risk_score: float = Field(..., ge=0, le=1, description="Risk score (0-1)")
    
    metrics: RiskMetrics = Field(..., description="Risk metrics")
    
    # Risk factors
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    mitigation_strategies: List[str] = Field(
        default_factory=list, description="Risk mitigation strategies"
    )
    
    # Portfolio context
    portfolio_weight: Optional[float] = Field(None, description="Weight in portfolio")
    diversification_impact: Optional[str] = Field(None, description="Diversification impact")
    
    summary: str = Field(..., description="Risk assessment summary")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in assessment")


class AssetAnalysis(BaseModel):
    """Complete analysis for a single asset."""
    
    # Asset identification
    symbol: str = Field(..., description="Asset symbol")
    asset_type: str = Field(..., description="Asset type (stock/crypto)")
    current_price: float = Field(..., gt=0, description="Current price")
    market_value: float = Field(..., gt=0, description="Market value in portfolio")
    
    # Analysis components
    technical_analysis: TechnicalAnalysis = Field(..., description="Technical analysis")
    sentiment_analysis: SentimentAnalysis = Field(..., description="Sentiment analysis")
    event_analysis: EventAnalysis = Field(..., description="Event analysis")
    risk_assessment: RiskAssessment = Field(..., description="Risk assessment")
    
    # Final recommendation
    recommendation: Recommendation = Field(..., description="Investment recommendation")
    target_price: Optional[float] = Field(None, description="Target price")
    stop_loss: Optional[float] = Field(None, description="Stop loss level")
    time_horizon: Optional[str] = Field(None, description="Investment time horizon")
    
    # Overall metrics
    overall_score: float = Field(..., ge=0, le=1, description="Overall analysis score")
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence")
    
    # Reasoning
    reasoning: str = Field(..., description="Detailed reasoning for recommendation")
    key_factors: List[str] = Field(default_factory=list, description="Key decision factors")
    
    # Analysis metadata
    analysis_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Analysis timestamp"
    )
    
    @field_validator('overall_score')
    @classmethod
    def calculate_overall_score(cls, v: float) -> float:
        """Calculate overall score from component analyses."""
        # Note: In V2, we can't access other field values during validation
        # This calculation will be handled in the service layer instead
        return v
    
    @field_validator('confidence')
    @classmethod
    def calculate_overall_confidence(cls, v: float) -> float:
        """Calculate overall confidence from component analyses."""
        # Note: In V2, we can't access other field values during validation
        # This calculation will be handled in the service layer instead
        return v
    
    @classmethod
    def create_analysis(
        cls,
        symbol: str,
        asset_type: str,
        current_price: float,
        market_value: float,
        technical_analysis: TechnicalAnalysis,
        sentiment_analysis: SentimentAnalysis,
        event_analysis: EventAnalysis,
        risk_assessment: RiskAssessment,
        recommendation: Recommendation,
        reasoning: str,
        **kwargs
    ) -> "AssetAnalysis":
        """Create an asset analysis with auto-calculated scores."""
        # Calculate overall score
        tech_score = technical_analysis.technical_score
        sentiment_score = (sentiment_analysis.sentiment_score + 1) / 2  # Normalize -1,1 to 0,1
        risk_score = 1 - risk_assessment.risk_score  # Invert risk (lower risk = higher score)
        
        # Weighted average (can be adjusted based on strategy)
        overall_score = (tech_score * 0.4 + sentiment_score * 0.3 + risk_score * 0.3)
        overall_score = max(0, min(1, overall_score))
        
        # Calculate overall confidence
        confidences = [
            technical_analysis.confidence,
            sentiment_analysis.confidence,
            risk_assessment.confidence
        ]
        overall_confidence = sum(confidences) / len(confidences)
        
        return cls(
            symbol=symbol,
            asset_type=asset_type,
            current_price=current_price,
            market_value=market_value,
            technical_analysis=technical_analysis,
            sentiment_analysis=sentiment_analysis,
            event_analysis=event_analysis,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
            overall_score=overall_score,
            confidence=overall_confidence,
            reasoning=reasoning,
            **kwargs
        )