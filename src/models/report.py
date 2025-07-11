"""Report models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from .portfolio import Portfolio
from .analysis import AssetAnalysis, Recommendation


class ReportSummary(BaseModel):
    """Report summary statistics."""
    
    total_portfolio_value: float = Field(..., gt=0, description="Total portfolio value")
    total_positions: int = Field(..., ge=0, description="Total number of positions")
    stocks_count: int = Field(..., ge=0, description="Number of stock positions")
    crypto_count: int = Field(..., ge=0, description="Number of crypto positions")
    
    # Recommendations summary
    buy_recommendations: int = Field(default=0, description="Number of BUY recommendations")
    sell_recommendations: int = Field(default=0, description="Number of SELL recommendations")
    hold_recommendations: int = Field(default=0, description="Number of HOLD recommendations")
    
    # Portfolio allocation
    stocks_percentage: float = Field(..., ge=0, le=100, description="Percentage in stocks")
    crypto_percentage: float = Field(..., ge=0, le=100, description="Percentage in crypto")
    
    # Performance metrics
    total_gain_loss: Optional[float] = Field(None, description="Total unrealized P&L")
    total_gain_loss_percent: Optional[float] = Field(None, description="Total unrealized P&L %")
    
    # Risk metrics
    average_confidence: float = Field(..., ge=0, le=1, description="Average analysis confidence")
    high_risk_positions: int = Field(default=0, description="Number of high-risk positions")
    
    # Market sentiment
    overall_sentiment: str = Field(..., description="Overall market sentiment")
    
    @field_validator('buy_recommendations', 'sell_recommendations', 'hold_recommendations')
    @classmethod
    def validate_recommendation_counts(cls, v: int) -> int:
        """Validate recommendation counts."""
        return max(0, v)


class TopPosition(BaseModel):
    """Top position summary."""
    
    symbol: str = Field(..., description="Asset symbol")
    asset_type: str = Field(..., description="Asset type")
    market_value: float = Field(..., gt=0, description="Market value")
    percentage_of_portfolio: float = Field(..., ge=0, le=100, description="Portfolio percentage")
    recommendation: Recommendation = Field(..., description="Recommendation")
    confidence: float = Field(..., ge=0, le=1, description="Analysis confidence")
    key_insight: str = Field(..., description="Key insight")


class MarketHighlight(BaseModel):
    """Market highlight or news item."""
    
    title: str = Field(..., description="Highlight title")
    description: str = Field(..., description="Highlight description")
    impact: str = Field(..., description="Market impact")
    relevance: str = Field(..., description="Portfolio relevance")
    source: Optional[str] = Field(None, description="Information source")


class Report(BaseModel):
    """Complete portfolio analysis report."""
    
    # Report metadata
    report_id: str = Field(..., description="Unique report ID")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Report generation timestamp"
    )
    
    # Portfolio data
    portfolio: Portfolio = Field(..., description="Portfolio snapshot")
    
    # Analysis results
    analyses: List[AssetAnalysis] = Field(..., description="Asset analyses")
    
    # Report summary
    summary: ReportSummary = Field(..., description="Report summary")
    
    # Highlights
    top_positions: List[TopPosition] = Field(
        default_factory=list, description="Top positions by value"
    )
    
    key_recommendations: List[str] = Field(
        default_factory=list, description="Key recommendations"
    )
    
    market_highlights: List[MarketHighlight] = Field(
        default_factory=list, description="Market highlights"
    )
    
    # Risk assessment
    portfolio_risk_level: str = Field(..., description="Overall portfolio risk level")
    risk_summary: str = Field(..., description="Risk assessment summary")
    
    # Performance tracking
    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Performance metrics"
    )
    
    # Execution summary
    execution_time: Optional[float] = Field(None, description="Analysis execution time (seconds)")
    data_sources_used: List[str] = Field(
        default_factory=list, description="Data sources used in analysis"
    )
    
    # Report configuration
    analysis_config: Dict[str, Any] = Field(
        default_factory=dict, description="Analysis configuration used"
    )
    
    @field_validator('summary')
    @classmethod
    def generate_summary(cls, v: ReportSummary) -> ReportSummary:
        """Generate or validate report summary."""
        # Note: In V2, we can't access other field values during validation
        # This validation will be handled in the service layer instead
        return v
            
    
    @field_validator('top_positions')
    @classmethod
    def generate_top_positions(cls, v: List[TopPosition]) -> List[TopPosition]:
        """Generate top positions summary."""
        # Note: In V2, we can't access other field values during validation
        # This validation will be handled in the service layer instead
        return v
    
    @field_validator('key_recommendations')
    @classmethod
    def generate_key_recommendations(cls, v: List[str]) -> List[str]:
        """Generate key recommendations."""
        # Note: In V2, we can't access other field values during validation
        # This validation will be handled in the service layer instead
        return v
    
    @property
    def total_analyses(self) -> int:
        """Total number of analyses performed."""
        return len(self.analyses)
    
    @property
    def has_high_confidence_recommendations(self) -> bool:
        """Check if report has high-confidence recommendations."""
        return any(a.confidence > 0.8 for a in self.analyses)
    
    def get_analysis_by_symbol(self, symbol: str) -> Optional[AssetAnalysis]:
        """Get analysis by symbol."""
        for analysis in self.analyses:
            if analysis.symbol.upper() == symbol.upper():
                return analysis
        return None
    
    def get_recommendations_by_type(self, recommendation: Recommendation) -> List[AssetAnalysis]:
        """Get analyses by recommendation type."""
        return [a for a in self.analyses if a.recommendation == recommendation]
    
    @classmethod
    def create_report(
        cls,
        report_id: str,
        portfolio: Portfolio,
        analyses: List[AssetAnalysis],
        portfolio_risk_level: str,
        risk_summary: str,
        **kwargs
    ) -> "Report":
        """Create a report with auto-generated summary and highlights."""
        # Generate summary
        buy_count = sum(1 for a in analyses if a.recommendation == Recommendation.BUY)
        sell_count = sum(1 for a in analyses if a.recommendation == Recommendation.SELL)
        hold_count = sum(1 for a in analyses if a.recommendation == Recommendation.HOLD)
        
        avg_confidence = sum(a.confidence for a in analyses) / len(analyses) if analyses else 0
        high_risk_count = sum(1 for a in analyses if a.risk_assessment.risk_level in ['high', 'very_high'])
        
        sentiment_scores = [a.sentiment_analysis.sentiment_score for a in analyses]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        if avg_sentiment > 0.2:
            overall_sentiment = "positive"
        elif avg_sentiment < -0.2:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        summary = ReportSummary(
            total_portfolio_value=portfolio.total_value,
            total_positions=portfolio.total_positions,
            stocks_count=len(portfolio.stocks),
            crypto_count=len(portfolio.crypto),
            buy_recommendations=buy_count,
            sell_recommendations=sell_count,
            hold_recommendations=hold_count,
            stocks_percentage=portfolio.stocks_percentage,
            crypto_percentage=portfolio.crypto_percentage,
            total_gain_loss=portfolio.total_gain_loss,
            total_gain_loss_percent=portfolio.total_gain_loss_percent,
            average_confidence=avg_confidence,
            high_risk_positions=high_risk_count,
            overall_sentiment=overall_sentiment
        )
        
        # Generate top positions
        analysis_lookup = {a.symbol: a for a in analyses}
        top_positions = []
        for position in portfolio.get_top_positions(5):
            analysis = analysis_lookup.get(position.symbol)
            if analysis:
                top_positions.append(TopPosition(
                    symbol=position.symbol,
                    asset_type=position.asset_type.value,
                    market_value=position.market_value,
                    percentage_of_portfolio=(position.market_value / portfolio.total_value) * 100,
                    recommendation=analysis.recommendation,
                    confidence=analysis.confidence,
                    key_insight=analysis.reasoning
                ))
        
        # Generate key recommendations
        high_confidence_analyses = [a for a in analyses if a.confidence > 0.8]
        high_confidence_analyses.sort(key=lambda a: a.overall_score, reverse=True)
        
        key_recommendations = []
        for analysis in high_confidence_analyses[:5]:  # Top 5
            rec_text = f"{analysis.recommendation.value} {analysis.symbol}: {analysis.reasoning}"
            key_recommendations.append(rec_text)
        
        return cls(
            report_id=report_id,
            portfolio=portfolio,
            analyses=analyses,
            summary=summary,
            top_positions=top_positions,
            key_recommendations=key_recommendations,
            portfolio_risk_level=portfolio_risk_level,
            risk_summary=risk_summary,
            **kwargs
        )