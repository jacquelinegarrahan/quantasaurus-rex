"""
AI Analysis Engine

Handles AI-powered investment analysis using:
- LangChain framework for workflow orchestration
- OpenAI o3-2025-04-16 for high-reasoning analysis
- Multi-factor investment analysis and recommendations
"""

from typing import Dict, Any, List
import structlog
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from quantasaurus.utils.config import Config
from quantasaurus.utils.exceptions import AnalysisError
from quantasaurus.ai_analysis.prompts.investment_analysis import INVESTMENT_ANALYSIS_PROMPT

logger = structlog.get_logger()


class AnalysisEngine:
    """AI-powered investment analysis engine."""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm = OpenAI(
            openai_api_key=config.openai_api_key,
            model_name="o3-2025-04-16",
            temperature=0.1,
            max_tokens=2000
        )
        
        self.analysis_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate.from_template(INVESTMENT_ANALYSIS_PROMPT),
            verbose=config.debug
        )
    
    def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze portfolio positions and generate recommendations.
        
        Args:
            portfolio_data: Combined portfolio and market data
            
        Returns:
            List of investment recommendations
        """
        try:
            logger.info("Starting AI portfolio analysis")
            
            recommendations = []
            
            for position in portfolio_data["positions"]:
                try:
                    recommendation = self._analyze_position(position, portfolio_data)
                    if recommendation:
                        recommendations.append(recommendation)
                except Exception as e:
                    logger.warning("Failed to analyze position", 
                                 symbol=position["symbol"], 
                                 error=str(e))
            
            # Filter recommendations by confidence threshold
            filtered_recommendations = [
                rec for rec in recommendations 
                if rec["confidence"] >= self.config.confidence_threshold
            ]
            
            # Sort by confidence and limit results
            filtered_recommendations.sort(key=lambda x: x["confidence"], reverse=True)
            final_recommendations = filtered_recommendations[:self.config.max_recommendations]
            
            logger.info("AI analysis completed", 
                       total_analyzed=len(recommendations),
                       filtered_recommendations=len(final_recommendations))
            
            return final_recommendations
            
        except Exception as e:
            logger.error("Portfolio analysis failed", error=str(e))
            raise AnalysisError(f"Failed to analyze portfolio: {str(e)}", "ANALYSIS_FAILED")
    
    def _analyze_position(self, position: Dict[str, Any], portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single position and generate recommendation.
        
        Args:
            position: Position data
            portfolio_data: Full portfolio context
            
        Returns:
            Investment recommendation
        """
        try:
            symbol = position["symbol"]
            
            # Gather relevant data for this position
            position_news = self._get_position_news(symbol, portfolio_data)
            position_events = self._get_position_events(symbol, portfolio_data)
            position_fundamentals = self._get_position_fundamentals(symbol, portfolio_data)
            
            # Prepare analysis context
            analysis_context = {
                "symbol": symbol,
                "position": position,
                "news": position_news,
                "events": position_events,
                "fundamentals": position_fundamentals,
                "portfolio_context": {
                    "total_value": portfolio_data["portfolio"]["total_value"],
                    "position_weight": position["market_value"] / portfolio_data["portfolio"]["total_value"]
                }
            }
            
            # Generate recommendation using AI
            result = self.analysis_chain.run(analysis_context)
            
            # Parse and structure the recommendation
            recommendation = self._parse_recommendation(result, position)
            
            return recommendation
            
        except Exception as e:
            logger.warning("Failed to analyze position", symbol=position["symbol"], error=str(e))
            return None
    
    def _get_position_news(self, symbol: str, portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get news relevant to a specific position."""
        all_news = []
        
        # Get stock news
        stock_news = portfolio_data.get("news", {}).get("stock_news", [])
        all_news.extend([news for news in stock_news if news["symbol"] == symbol])
        
        # Get crypto news
        crypto_news = portfolio_data.get("news", {}).get("crypto_news", [])
        all_news.extend([news for news in crypto_news if news["symbol"] == symbol])
        
        # Include some market news for context
        market_news = portfolio_data.get("news", {}).get("market_news", [])
        all_news.extend(market_news[:3])  # Top 3 market news items
        
        return all_news
    
    def _get_position_events(self, symbol: str, portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get events relevant to a specific position."""
        all_events = portfolio_data.get("events", [])
        return [event for event in all_events if event.get("symbol") == symbol]
    
    def _get_position_fundamentals(self, symbol: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get fundamental data for a specific position."""
        equities = portfolio_data.get("fundamentals", {}).get("equities", [])
        
        for equity in equities:
            if equity.get("ticker") == symbol or equity.get("local_ticker") == symbol:
                return equity
        
        return {}
    
    def _parse_recommendation(self, ai_result: str, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse AI recommendation result into structured format.
        
        Args:
            ai_result: Raw AI analysis result
            position: Position data
            
        Returns:
            Structured recommendation
        """
        # This is a simplified parser - in production, you'd want more robust parsing
        lines = ai_result.strip().split('\n')
        
        recommendation = {
            "symbol": position["symbol"],
            "type": position["type"],
            "current_value": position["market_value"],
            "recommendation": "HOLD",  # Default
            "confidence": 50,  # Default
            "reasoning": [],
            "key_factors": [],
            "risk_assessment": "MEDIUM",
            "price_target": None,
            "time_horizon": "3-6 months"
        }
        
        # Parse the AI result (simplified parsing logic)
        for line in lines:
            line = line.strip()
            if line.startswith("RECOMMENDATION:"):
                rec = line.split(":")[-1].strip().upper()
                if rec in ["BUY", "SELL", "HOLD"]:
                    recommendation["recommendation"] = rec
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.split(":")[-1].strip().rstrip('%'))
                    recommendation["confidence"] = confidence
                except:
                    pass
            elif line.startswith("RISK:"):
                risk = line.split(":")[-1].strip().upper()
                if risk in ["LOW", "MEDIUM", "HIGH"]:
                    recommendation["risk_assessment"] = risk
            elif line.startswith("REASONING:"):
                reasoning = line.split(":")[-1].strip()
                recommendation["reasoning"].append(reasoning)
        
        return recommendation