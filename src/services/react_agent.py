"""ReAct agent implementation for portfolio analysis."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Union

from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ..config.settings import Settings
from ..models.analysis import (
    AssetAnalysis,
    EventAnalysis,
    Recommendation,
    RiskAssessment,
    RiskLevel,
    RiskMetrics,
    SentimentAnalysis,
    SentimentLevel,
    TechnicalAnalysis,
    TechnicalIndicators,
    TrendDirection,
)
from ..models.portfolio import CryptoPosition, Portfolio, StockPosition
from ..utils.retry import RetryConfig, openai_retry
from .aiera_client import AieraService
from .robinhood_client import RobinhoodService
from .tavily_client import TavilyService

logger = logging.getLogger(__name__)


class QuantasaurusReactAgent:
    """ReAct agent for comprehensive portfolio analysis."""

    def __init__(self, settings: Settings):
        """Initialize the ReAct agent."""
        self.settings = settings

        # Initialize LLM with retry configuration
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.1,  # Lower temperature for more consistent analysis
            max_tokens=4000,
            max_retries=5,  # Built-in OpenAI retry
            request_timeout=30.0  # 30 second timeout
        )

        # Initialize services
        self.robinhood_service = None
        self.aiera_service = None
        self.tavily_service = None

        # Create tools
        self.tools = self._create_tools()

        # Create agent
        self.agent = create_react_agent(self.llm, self.tools)

        # Analysis cache
        self.analysis_cache = {}

        # Retry configuration for agent calls
        self.retry_config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            backoff_multiplier=1.5
        )

        # Parallel processing configuration from settings
        self.max_concurrent_analyses = settings.max_concurrent_analyses
        self.enable_parallel_processing = settings.enable_parallel_processing
        self.api_rate_limit_delay = settings.api_rate_limit_delay
        self.batch_delay = settings.batch_delay
        self.stagger_delay = settings.stagger_delay

    def _create_tools(self) -> list[Tool]:
        """Create LangChain tools for the agent."""
        tools = [
            Tool(
                name="technical_analysis",
                func=self._perform_technical_analysis,
                description="Analyze technical indicators and chart patterns for a stock or crypto asset. Input should be a JSON string with 'symbol', 'historical_data', and optionally 'sector' and 'industry' keys for better industry context."
            ),
            Tool(
                name="sentiment_analysis",
                func=self._analyze_sentiment,
                description="Analyze market sentiment from news and social media for a stock or crypto asset. Input should be a JSON string with 'symbol', 'company_name', and optionally 'sector' and 'industry' keys for better industry context."
            ),
            Tool(
                name="event_analysis",
                func=self._analyze_events,
                description="Analyze upcoming events and their potential impact on a stock or crypto asset. Input should be a JSON string with 'symbol', 'company_name', and optionally 'sector' and 'industry' keys for better industry context."
            ),
            Tool(
                name="risk_assessment",
                func=self._assess_risk,
                description="Assess investment risk based on various factors for a stock or crypto asset. Input should be a JSON string with 'symbol', 'position_data', and 'portfolio_context' keys."
            ),
            Tool(
                name="get_market_data",
                func=self._get_market_data,
                description="Get current market data and fundamentals for a stock or crypto asset. Input should be a JSON string with 'symbol' key."
            ),
            Tool(
                name="compare_assets",
                func=self._compare_assets,
                description="Compare multiple assets for relative analysis. Input should be a JSON string with 'symbols' list and 'comparison_type' keys."
            )
        ]

        return tools

    async def initialize_services(self, robinhood_service: RobinhoodService,
                                 aiera_service: AieraService, tavily_service: TavilyService):
        """Initialize external services."""
        self.robinhood_service = robinhood_service
        self.aiera_service = aiera_service
        self.tavily_service = tavily_service

    async def analyze_asset(self, position: Union[StockPosition, CryptoPosition]) -> AssetAnalysis:
        """Analyze a single asset and provide recommendation."""
        try:
            logger.info(f"Analyzing asset: {position.symbol}")

            # Check cache first
            cache_key = f"{position.symbol}_{datetime.now().strftime('%Y-%m-%d')}"
            if cache_key in self.analysis_cache:
                logger.info(f"Using cached analysis for {position.symbol}")
                return self.analysis_cache[cache_key]

            # Fetch company information for industry context
            company_info = {}
            sector = None
            industry = None

            if self.aiera_service and hasattr(position, 'asset_type'):
                try:
                    logger.debug(f"Fetching company information for {position.symbol}")
                    company_info = await self.aiera_service.get_company_info(position.symbol)
                    if company_info and 'metrics' in company_info:
                        sector = company_info['metrics'].get('sector')
                        industry = company_info['metrics'].get('industry')
                        logger.debug(f"Retrieved sector: {sector}, industry: {industry} for {position.symbol}")
                except Exception as e:
                    logger.warning(f"Failed to fetch company info for {position.symbol}: {str(e)}")

            # Prepare analysis context
            analysis_context = {
                "symbol": position.symbol,
                "asset_type": position.asset_type.value,
                "current_price": position.current_price,
                "market_value": position.market_value,
                "position_data": position.model_dump(),
                "analysis_date": datetime.utcnow().isoformat(),
                "company_info": company_info,
                "sector": sector,
                "industry": industry
            }

            # Create analysis prompt
            prompt = self._create_analysis_prompt(position, analysis_context)

            # Run agent analysis
            agent_response = await self._run_agent_analysis(prompt, analysis_context)

            # Parse agent response into structured analysis
            analysis = self._parse_agent_response(agent_response, position)

            # Cache the analysis
            self.analysis_cache[cache_key] = analysis

            logger.info(f"Completed analysis for {position.symbol}: {analysis.recommendation.value}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing asset {position.symbol}: {str(e)}")
            # Return default analysis on error
            return self._create_default_analysis(position)

    async def generate_portfolio_analysis(self, portfolio: Portfolio) -> list[AssetAnalysis]:
        """Analyze entire portfolio with parallel processing and generate recommendations."""
        try:
            # Check if parallel processing is enabled
            if not self.enable_parallel_processing:
                logger.info("Parallel processing disabled, using sequential analysis")
                return await self._sequential_portfolio_analysis(portfolio)

            logger.info(f"Analyzing portfolio with {portfolio.total_positions} positions using parallel processing")

            # Collect all positions for parallel processing
            all_positions = portfolio.stocks + portfolio.crypto

            if not all_positions:
                logger.warning("No positions found in portfolio")
                return []

            # Limit concurrent analyses to prevent overwhelming APIs
            if len(all_positions) > self.max_concurrent_analyses:
                logger.info(f"Portfolio has {len(all_positions)} positions, processing in batches of {self.max_concurrent_analyses}")
                return await self._batch_portfolio_analysis(portfolio, all_positions)

            # Create analysis tasks for all positions
            analysis_tasks = []
            for i, position in enumerate(all_positions):
                # Add staggered delays to prevent API rate limiting
                delay = i * self.stagger_delay  # Configurable delay between task starts
                task = self._analyze_asset_with_delay(position, delay)
                analysis_tasks.append(task)

            logger.info(f"Created {len(analysis_tasks)} parallel analysis tasks")

            # Execute all analyses concurrently using asyncio.gather()
            try:
                analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)

                # Process results and handle exceptions
                processed_analyses = []
                for i, result in enumerate(analyses):
                    position = all_positions[i]

                    if isinstance(result, Exception):
                        logger.error(f"Error analyzing asset {position.symbol}: {str(result)}")
                        processed_analyses.append(self._create_default_analysis(position))
                    elif isinstance(result, AssetAnalysis):
                        processed_analyses.append(result)
                    else:
                        logger.warning(f"Unexpected result type for {position.symbol}: {type(result)}")
                        processed_analyses.append(self._create_default_analysis(position))

                logger.info(f"Completed {len(processed_analyses)} parallel asset analyses")

                # Portfolio-level analysis
                await self._analyze_portfolio_correlations(processed_analyses, portfolio)

                logger.info(f"Completed portfolio analysis with {len(processed_analyses)} asset analyses")
                return processed_analyses

            except Exception as e:
                logger.error(f"Error during parallel analysis execution: {str(e)}")
                # Fallback to sequential processing
                logger.info("Falling back to sequential processing due to parallel execution failure")
                return await self._sequential_portfolio_analysis(portfolio)

        except Exception as e:
            logger.error(f"Error generating portfolio analysis: {str(e)}")
            return []

    def _create_analysis_prompt(self, position: Union[StockPosition, CryptoPosition],
                               context: dict[str, Any]) -> str:
        """Create analysis prompt for the agent."""
        company_name = getattr(position, 'company_name', '') or getattr(position, 'full_name', '')

        # Extract industry context
        sector = context.get("sector", "Unknown")
        industry = context.get("industry", "Unknown")

        industry_context = ""
        if sector and sector != "Unknown":
            industry_context += f"        - Sector: {sector}\n"
        if industry and industry != "Unknown":
            industry_context += f"        - Industry: {industry}\n"

        prompt = f"""
        You are a professional financial analyst tasked with providing comprehensive investment analysis.

        ASSET INFORMATION:
        - Symbol: {position.symbol}
        - Asset Type: {position.asset_type.value}
        - Company/Name: {company_name}
        - Current Price: ${position.current_price:.2f}
        - Market Value: ${position.market_value:.2f}
        - Quantity: {position.quantity}
{industry_context}

        ANALYSIS REQUIREMENTS:
        1. Technical Analysis: Use the technical_analysis tool to analyze price patterns, indicators, and trends. Include sector and industry information when available.
        2. Sentiment Analysis: Use the sentiment_analysis tool to gauge market sentiment from news and social media. Include sector and industry information when available.
        3. Event Analysis: Use the event_analysis tool to identify upcoming catalysts and events. Include sector and industry information when available.
        4. Risk Assessment: Use the risk_assessment tool to evaluate investment risks
        5. Market Data: Use the get_market_data tool to get current fundamentals and market conditions

        ANALYSIS FRAMEWORK:
        - Provide a comprehensive analysis using all available tools
        - Consider both quantitative and qualitative factors
        - Evaluate short-term (1-3 months) and medium-term (3-12 months) outlook
        - Account for current market conditions and portfolio context

        RECOMMENDATION REQUIREMENTS:
        - Provide clear BUY, SELL, or HOLD recommendation that MUST align with your reasoning
        - Include confidence level (0-100%) - THIS IS MANDATORY
        - Provide detailed reasoning that directly supports your recommendation
        - Suggest target price and stop-loss levels if applicable
        - Consider risk-reward ratio and time horizon
        - CRITICAL: Your final recommendation MUST be consistent with your analysis and reasoning

        OUTPUT FORMAT - FOLLOW THIS EXACTLY:
        Please conclude your analysis with this EXACT format:

        === INVESTMENT RECOMMENDATION ===
        Final Recommendation: [BUY/SELL/HOLD]
        Confidence Score: [X]%
        Reasoning: [Detailed explanation that directly supports your recommendation above. If you recommend BUY, explain why it's a good investment. If SELL, explain why it should be sold. If HOLD, explain why it's neither a strong buy nor sell.]
        === END RECOMMENDATION ===

        IMPORTANT: Your reasoning MUST match your recommendation. Do not say "BUY" if your reasoning suggests otherwise.

        Begin your analysis now by using the available tools systematically.
        """

        return prompt

    @openai_retry(max_retries=5, base_delay=2.0, max_delay=60.0, exponential_base=2.0, jitter=True)
    async def _run_agent_analysis(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        """Run the agent analysis with retry logic."""
        try:
            # Run the agent
            response = await self.agent.ainvoke({
                "messages": [("user", prompt)],
                "context": context
            })

            # Extract the agent's response
            if "messages" in response and response["messages"]:
                final_message = response["messages"][-1]
                if hasattr(final_message, 'content'):
                    return {"response": final_message.content, "context": context}

            return {"response": "Analysis completed", "context": context}

        except Exception as e:
            logger.error(f"Error running agent analysis: {str(e)}")

            # Graceful degradation - return basic analysis
            symbol = context.get("symbol", "UNKNOWN")
            return {
                "response": f"Basic analysis for {symbol}: Unable to perform full AI analysis due to API limitations. Using default conservative approach.",
                "context": context,
                "fallback": True
            }

    def _parse_agent_response(self, agent_response: dict[str, Any],
                            position: Union[StockPosition, CryptoPosition]) -> AssetAnalysis:
        """Parse agent response into structured analysis."""
        try:
            # Extract analysis components from agent response
            response_text = agent_response.get("response", "")

            # Create default analysis structure
            analysis = AssetAnalysis.create_analysis(
                symbol=position.symbol,
                asset_type=position.asset_type.value,
                current_price=position.current_price,
                market_value=position.market_value,
                technical_analysis=self._create_default_technical_analysis(),
                sentiment_analysis=self._create_default_sentiment_analysis(),
                event_analysis=self._create_default_event_analysis(),
                risk_assessment=self._create_default_risk_assessment(),
                recommendation=Recommendation.HOLD,
                reasoning="Default analysis with limited data"
            )

            # Enhanced parsing for structured recommendation format
            import re

            # First, try to extract from structured format
            structured_pattern = r'=== INVESTMENT RECOMMENDATION ===(.*?)=== END RECOMMENDATION ==='
            structured_match = re.search(structured_pattern, response_text, re.IGNORECASE | re.DOTALL)

            if structured_match:
                recommendation_section = structured_match.group(1)

                # Extract recommendation from structured format
                rec_pattern = r'Final Recommendation:\s*(BUY|SELL|HOLD)'
                rec_match = re.search(rec_pattern, recommendation_section, re.IGNORECASE)
                if rec_match:
                    rec_value = rec_match.group(1).upper()
                    if rec_value == "BUY":
                        analysis.recommendation = Recommendation.BUY
                    elif rec_value == "SELL":
                        analysis.recommendation = Recommendation.SELL
                    else:
                        analysis.recommendation = Recommendation.HOLD

                # Extract confidence from structured format
                conf_pattern = r'Confidence Score:\s*(\d+(?:\.\d+)?)%?'
                conf_match = re.search(conf_pattern, recommendation_section, re.IGNORECASE)
                if conf_match:
                    confidence_value = float(conf_match.group(1))
                    if confidence_value > 1:
                        confidence_value = confidence_value / 100
                    analysis.confidence = min(max(confidence_value, 0.0), 1.0)

                # Extract reasoning from structured format
                reasoning_pattern = r'Reasoning:\s*(.+)'
                reasoning_match = re.search(reasoning_pattern, recommendation_section, re.IGNORECASE | re.DOTALL)
                if reasoning_match:
                    analysis.reasoning = reasoning_match.group(1).strip()[:2500]  # Increased length for complete analysis

            else:
                # Fallback to original parsing if structured format not found
                # Parse recommendation from response
                if "BUY" in response_text.upper():
                    analysis.recommendation = Recommendation.BUY
                elif "SELL" in response_text.upper():
                    analysis.recommendation = Recommendation.SELL
                else:
                    analysis.recommendation = Recommendation.HOLD

                # Extract confidence if mentioned - enhanced pattern matching
                confidence_patterns = [
                    r'confidence[:\s]*(\d+(?:\.\d+)?)%?',
                    r'confidence[:\s]*([01](?:\.\d+)?)',
                    r'(\d+(?:\.\d+)?)%?\s*confidence',
                    r'confidence\s*score[:\s]*(\d+(?:\.\d+)?)%?',
                    r'overall\s*confidence[:\s]*(\d+(?:\.\d+)?)%?'
                ]

                confidence_value = None
                for pattern in confidence_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        confidence_value = float(match.group(1))
                        # If value is > 1, assume it's a percentage
                        if confidence_value > 1:
                            confidence_value = confidence_value / 100
                        analysis.confidence = min(max(confidence_value, 0.0), 1.0)
                        break

                # Extract reasoning
                reasoning_patterns = [
                    r'reasoning[:\s]*(.+?)(?=\n\n|$)',
                    r'recommendation[:\s]*(.+?)(?=\n\n|$)',
                    r'analysis[:\s]*(.+?)(?=\n\n|$)'
                ]

                for pattern in reasoning_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        analysis.reasoning = match.group(1).strip()[:2500]  # Increased length for complete analysis
                        break

            # If no confidence found, calculate based on recommendation strength
            if not hasattr(analysis, 'confidence') or analysis.confidence == 0:
                if analysis.recommendation == Recommendation.BUY:
                    analysis.confidence = 0.75  # High confidence for BUY
                elif analysis.recommendation == Recommendation.SELL:
                    analysis.confidence = 0.70  # High confidence for SELL
                else:
                    analysis.confidence = 0.60  # Medium confidence for HOLD

            # Validate consistency between recommendation and reasoning
            reasoning_text = analysis.reasoning.lower() if analysis.reasoning else ""
            if analysis.recommendation == Recommendation.BUY:
                # Check if reasoning actually supports a BUY recommendation
                negative_indicators = ["sell", "avoid", "negative", "decline", "drop", "risk", "concern"]
                positive_indicators = ["buy", "strong", "growth", "positive", "upside", "opportunity"]

                negative_count = sum(1 for indicator in negative_indicators if indicator in reasoning_text)
                positive_count = sum(1 for indicator in positive_indicators if indicator in reasoning_text)

                if negative_count > positive_count:
                    logger.warning(f"Potential inconsistency: BUY recommendation but reasoning seems negative for {position.symbol}")
                    # Consider adjusting confidence down
                    analysis.confidence = max(0.3, analysis.confidence - 0.2)

            elif analysis.recommendation == Recommendation.SELL:
                # Check if reasoning actually supports a SELL recommendation
                positive_indicators = ["buy", "strong", "growth", "positive", "upside", "opportunity"]
                negative_indicators = ["sell", "avoid", "negative", "decline", "drop", "risk", "concern"]

                positive_count = sum(1 for indicator in positive_indicators if indicator in reasoning_text)
                negative_count = sum(1 for indicator in negative_indicators if indicator in reasoning_text)

                if positive_count > negative_count:
                    logger.warning(f"Potential inconsistency: SELL recommendation but reasoning seems positive for {position.symbol}")
                    # Consider adjusting confidence down
                    analysis.confidence = max(0.3, analysis.confidence - 0.2)

            return analysis

        except Exception as e:
            logger.error(f"Error parsing agent response: {str(e)}")
            return self._create_default_analysis(position)

    def _perform_technical_analysis(self, input_data: str) -> str:
        """Perform technical analysis using historical data and web insights."""
        try:
            data = json.loads(input_data)
            symbol = data.get("symbol", "")
            historical_data = data.get("historical_data", [])

            if not historical_data:
                return f"No historical data available for {symbol}"

            # Calculate technical indicators from historical data
            prices = []
            for item in historical_data:
                if isinstance(item, dict) and item.get("close"):
                    try:
                        prices.append(float(item.get("close", 0)))
                    except (ValueError, TypeError):
                        continue

            if len(prices) < 20:
                return f"Insufficient data for technical analysis of {symbol}"

            # Calculate simple indicators
            current_price = prices[-1]
            sma_20 = sum(prices[-20:]) / 20
            sma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else sma_20

            # Determine trend
            if current_price > sma_20 > sma_50:
                trend = "bullish"
            elif current_price < sma_20 < sma_50:
                trend = "bearish"
            else:
                trend = "neutral"

            # Calculate volatility
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5

            # Enhanced analysis with web-based insights
            web_insights = ""
            if self.tavily_service:
                try:
                    # Create helper functions for async calls
                    def run_technical_analysis():
                        if self.tavily_service:
                            # Extract industry context if available
                            sector = data.get("sector")
                            industry = data.get("industry")
                            return asyncio.run(self.tavily_service.search_technical_analysis(symbol, sector, industry))
                        return {}

                    def run_technical_news():
                        if self.tavily_service:
                            technical_query = f"{symbol} technical analysis chart patterns support resistance"
                            return asyncio.run(self.tavily_service.search_news(technical_query, max_results=3))
                        return []

                    # Get technical analysis insights from web
                    technical_data = run_technical_analysis()

                    # Search for technical analysis news
                    technical_news = run_technical_news()

                    # Ensure technical_news is a list
                    if not isinstance(technical_news, list):
                        technical_news = []

                    # Format web insights
                    insights = []
                    if isinstance(technical_data, dict):
                        for key, value in technical_data.items():
                            if key in ["trend_analysis", "key_levels", "indicators", "recommendation"]:
                                insights.append(f"- {key.replace('_', ' ').title()}: {value}")
                    else:
                        logger.debug(f"technical_data is not a dict: {type(technical_data)}")

                    # Add news insights
                    news_insights = []
                    for news in technical_news:
                        if isinstance(news, dict) and news.get("title") and news.get("source"):
                            title = str(news.get("title", ""))
                            source = str(news.get("source", "unknown"))
                            if len(title) > 0:
                                news_insights.append(f"- {title[:80]}... ({source})")

                    if insights or news_insights:
                        web_insights = f"""

Web-Based Technical Insights:
{chr(10).join(insights) if insights else ""}
{chr(10).join(news_insights) if news_insights else ""}
"""
                except Exception as e:
                    logger.warning(f"Could not fetch web-based technical insights: {str(e)}")

            analysis = f"""
Technical Analysis for {symbol}:
- Current Price: ${current_price:.2f}
- 20-day SMA: ${sma_20:.2f}
- 50-day SMA: ${sma_50:.2f}
- Trend: {trend.capitalize()}
- Volatility: {volatility:.4f}
- Support Level: ${min(prices[-20:]):.2f}
- Resistance Level: ${max(prices[-20:]):.2f}
- Price vs SMA20: {"Above" if current_price > sma_20 else "Below"} ({((current_price - sma_20) / sma_20 * 100):+.1f}%)
- Price vs SMA50: {"Above" if current_price > sma_50 else "Below"} ({((current_price - sma_50) / sma_50 * 100):+.1f}%)
{web_insights}
"""

            return analysis

        except Exception as e:
            logger.error(f"Error in technical analysis: {str(e)}")
            return f"Error performing technical analysis: {str(e)}"

    def _analyze_sentiment(self, input_data: str) -> str:
        """Analyze market sentiment from news and social media."""
        try:
            data = json.loads(input_data)
            symbol = data.get("symbol", "")
            company_name = data.get("company_name", "")

            if not self.tavily_service:
                return f"Sentiment analysis for {symbol}: Neutral (no data source available)"

            # Call Tavily service for actual sentiment analysis
            try:
                # Create a new event loop for sync context
                def run_sentiment_analysis():
                    if self.tavily_service:
                        # Extract industry context if available
                        sector = data.get("sector")
                        industry = data.get("industry")
                        return asyncio.run(self.tavily_service.search_market_sentiment(symbol, sector, industry))
                    return {}

                def run_news_search():
                    if self.tavily_service:
                        news_query = f"{symbol} {company_name} stock news sentiment"
                        return asyncio.run(self.tavily_service.search_news(news_query, max_results=5))
                    return []

                # Run both searches
                sentiment_data = run_sentiment_analysis()
                news_results = run_news_search()

                # Ensure proper data types
                if not isinstance(news_results, list):
                    news_results = []

                # Process results - ensure sentiment_data is a dict
                if not isinstance(sentiment_data, dict):
                    sentiment_data = {}

                sentiment_score = sentiment_data.get("sentiment_score", 0.0)
                overall_sentiment = sentiment_data.get("overall_sentiment", "neutral")
                positive_mentions = sentiment_data.get("positive_mentions", 0)
                negative_mentions = sentiment_data.get("negative_mentions", 0)

                # Format news snippets - ensure news_results is a list and each item is a dict
                news_summary = []
                if isinstance(news_results, list):
                    for news in news_results[:3]:  # Top 3 news items
                        if isinstance(news, dict) and news.get("title") and news.get("source"):
                            title = str(news.get("title", ""))
                            source = str(news.get("source", "unknown"))
                            news_summary.append(f"- {title[:100]}... (Source: {source})")

                return f"""
Sentiment Analysis for {symbol}:
- Overall Sentiment: {overall_sentiment.capitalize()} (Score: {sentiment_score:.2f})
- Positive Mentions: {positive_mentions}
- Negative Mentions: {negative_mentions}
- Total Sources Analyzed: {len(news_results)}

Recent News Summary:
{chr(10).join(news_summary)}

Analysis: Based on recent news and market sentiment, {symbol} shows {overall_sentiment} sentiment with a score of {sentiment_score:.2f}.
"""
            except Exception as e:
                logger.error(f"Error calling Tavily service for sentiment analysis: {str(e)}")
                return f"Sentiment analysis for {symbol}: Unable to fetch current sentiment data (Error: {str(e)})"

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return f"Error performing sentiment analysis: {str(e)}"

    def _analyze_events(self, input_data: str) -> str:
        """Analyze upcoming events and their potential impact."""
        try:
            data = json.loads(input_data)
            symbol = data.get("symbol", "")
            company_name = data.get("company_name", "")

            if not self.tavily_service:
                return f"Event analysis for {symbol}: No data source available"

            # Call Tavily service for actual event analysis
            try:
                # Create helper functions for async calls
                def run_events_search():
                    if self.tavily_service:
                        # Extract industry context if available
                        sector = data.get("sector")
                        industry = data.get("industry")
                        return asyncio.run(self.tavily_service.search_company_events(symbol, company_name, sector, industry))
                    return []

                def run_events_news_search():
                    if self.tavily_service:
                        events_query = f"{symbol} {company_name} earnings events announcements"
                        return asyncio.run(self.tavily_service.search_news(events_query, max_results=5))
                    return []

                # Search for company events using Tavily
                events_data = run_events_search()

                # Also search for general financial events and earnings news
                news_results = run_events_news_search()

                # Ensure proper data types
                if not isinstance(events_data, list):
                    events_data = []
                if not isinstance(news_results, list):
                    news_results = []

                # Process events data
                upcoming_events = []
                for event in events_data[:5]:  # Top 5 events
                    if isinstance(event, dict):
                        event_info = {
                            "title": str(event.get("title", "")),
                            "description": str(event.get("description", "")),
                            "date": str(event.get("date", "")),
                            "importance": str(event.get("importance", "medium")),
                            "source": str(event.get("source", ""))
                        }
                        upcoming_events.append(event_info)

                # Format event summary
                event_summary = []
                for event in upcoming_events:
                    if isinstance(event, dict):
                        title = str(event.get('title', 'Unknown Event'))
                        importance = str(event.get('importance', 'medium'))
                        event_summary.append(f"- {title[:80]}... (Importance: {importance})")

                # Format news about events
                news_summary = []
                for news in news_results[:3]:  # Top 3 news items
                    if isinstance(news, dict) and news.get("title") and news.get("source"):
                        title = str(news.get("title", ""))
                        source = str(news.get("source", "unknown"))
                        news_summary.append(f"- {title[:100]}... (Source: {source})")

                return f"""
Event Analysis for {symbol}:
- Total Events Found: {len(upcoming_events)}
- Recent Event-Related News: {len(news_results)}

Upcoming Events:
{chr(10).join(event_summary) if event_summary else "- No specific events found"}

Recent Event-Related News:
{chr(10).join(news_summary) if news_summary else "- No recent event news found"}

Analysis: Based on available data, {symbol} has {len(upcoming_events)} upcoming events that could impact the stock price. Recent news coverage suggests {'high' if len(news_results) > 3 else 'moderate'} market attention.
"""
            except Exception as e:
                logger.error(f"Error calling Tavily service for event analysis: {str(e)}")
                return f"Event analysis for {symbol}: Unable to fetch current event data (Error: {str(e)})"

        except Exception as e:
            logger.error(f"Error in event analysis: {str(e)}")
            return f"Error performing event analysis: {str(e)}"

    def _assess_risk(self, input_data: str) -> str:
        """Assess investment risk based on various factors."""
        try:
            data = json.loads(input_data)
            symbol = data.get("symbol", "")
            position_data = data.get("position_data", {})
            portfolio_context = data.get("portfolio_context", {})

            # Simplified risk assessment
            market_value = position_data.get("market_value", 0)

            # Calculate position size risk
            total_portfolio_value = portfolio_context.get("total_value", market_value)
            position_weight = (market_value / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0

            # Determine risk level
            if position_weight > 20:
                risk_level = "high"
            elif position_weight > 10:
                risk_level = "medium"
            else:
                risk_level = "low"

            analysis = f"""
            Risk Assessment for {symbol}:
            - Position Weight: {position_weight:.1f}%
            - Risk Level: {risk_level}
            - Concentration Risk: {'High' if position_weight > 15 else 'Low'}
            - Liquidity Risk: Low (public market)
            - Volatility Risk: Medium
            """

            return analysis

        except Exception as e:
            logger.error(f"Error in risk assessment: {str(e)}")
            return f"Error assessing risk: {str(e)}"

    def _get_market_data(self, input_data: str) -> str:
        """Get current market data and fundamentals."""
        try:
            data = json.loads(input_data)
            symbol = data.get("symbol", "")

            # Simplified market data
            # In a real implementation, this would use the Robinhood service
            market_data = f"""
            Market Data for {symbol}:
            - Current Price: Available from position data
            - Market Cap: Not available
            - Volume: Not available
            - P/E Ratio: Not available
            - 52-Week High/Low: Not available
            - Beta: Not available
            """

            return market_data

        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return f"Error getting market data: {str(e)}"

    def _compare_assets(self, input_data: str) -> str:
        """Compare multiple assets for relative analysis."""
        try:
            data = json.loads(input_data)
            symbols = data.get("symbols", [])
            comparison_type = data.get("comparison_type", "performance")

            # Simplified comparison
            comparison = f"""
            Asset Comparison ({comparison_type}):
            - Symbols: {', '.join(symbols)}
            - Comparison Type: {comparison_type}
            - Analysis: Relative performance data not available
            """

            return comparison

        except Exception as e:
            logger.error(f"Error comparing assets: {str(e)}")
            return f"Error comparing assets: {str(e)}"

    def _create_default_technical_analysis(self) -> TechnicalAnalysis:
        """Create default technical analysis."""
        return TechnicalAnalysis(
            indicators=TechnicalIndicators(),
            trend=TrendDirection.NEUTRAL,
            technical_score=0.5,
            confidence=0.6,
            summary="Technical analysis completed with limited data"
        )

    def _create_default_sentiment_analysis(self) -> SentimentAnalysis:
        """Create default sentiment analysis."""
        return SentimentAnalysis(
            sentiment_level=SentimentLevel.NEUTRAL,
            sentiment_score=0.0,
            news_sentiment=SentimentLevel.NEUTRAL,
            confidence=0.6,
            summary="Sentiment analysis completed with limited data"
        )

    def _create_default_event_analysis(self) -> EventAnalysis:
        """Create default event analysis."""
        return EventAnalysis(
            overall_impact="neutral",
            confidence=0.6
        )

    def _create_default_risk_assessment(self) -> RiskAssessment:
        """Create default risk assessment."""
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            risk_score=0.5,
            metrics=RiskMetrics(),
            summary="Risk assessment completed with limited data",
            confidence=0.6
        )

    def _create_default_analysis(self, position: Union[StockPosition, CryptoPosition]) -> AssetAnalysis:
        """Create default analysis for error cases."""
        return AssetAnalysis.create_analysis(
            symbol=position.symbol,
            asset_type=position.asset_type.value,
            current_price=position.current_price,
            market_value=position.market_value,
            technical_analysis=self._create_default_technical_analysis(),
            sentiment_analysis=self._create_default_sentiment_analysis(),
            event_analysis=self._create_default_event_analysis(),
            risk_assessment=self._create_default_risk_assessment(),
            recommendation=Recommendation.HOLD,
            reasoning="Default analysis due to processing error"
        )

    async def _analyze_portfolio_correlations(self, analyses: list[AssetAnalysis],
                                           portfolio: Portfolio):
        """Analyze portfolio-level correlations and diversification."""
        try:
            # Simplified portfolio analysis
            # In a real implementation, this would analyze correlations between assets
            logger.info("Analyzing portfolio correlations...")

            # Update risk assessments with portfolio context
            for analysis in analyses:
                position = portfolio.get_position_by_symbol(analysis.symbol)
                if position:
                    weight = (position.market_value / portfolio.total_value) * 100
                    analysis.risk_assessment.portfolio_weight = weight

                    # Adjust risk level based on concentration
                    if weight > 20:
                        analysis.risk_assessment.risk_level = RiskLevel.HIGH
                    elif weight > 10:
                        analysis.risk_assessment.risk_level = RiskLevel.MEDIUM
                    else:
                        analysis.risk_assessment.risk_level = RiskLevel.LOW

        except Exception as e:
            logger.error(f"Error analyzing portfolio correlations: {str(e)}")

    async def _analyze_asset_with_delay(self, position: Union[StockPosition, CryptoPosition],
                                       delay: float = 0.0) -> AssetAnalysis:
        """Analyze a single asset with an optional delay for rate limiting."""
        try:
            # Add staggered delay to prevent API rate limiting
            if delay > 0:
                await asyncio.sleep(delay)

            # Rate limiting - add base delay between API calls
            await asyncio.sleep(self.api_rate_limit_delay)  # Configurable delay between requests

            return await self.analyze_asset(position)

        except Exception as e:
            logger.error(f"Error in delayed analysis for {position.symbol}: {str(e)}")
            return self._create_default_analysis(position)

    async def _batch_portfolio_analysis(self, portfolio: Portfolio,
                                       all_positions: list[Union[StockPosition, CryptoPosition]]) -> list[AssetAnalysis]:
        """Process portfolio analysis in batches for large portfolios."""
        try:
            logger.info(f"Processing {len(all_positions)} positions in batches of {self.max_concurrent_analyses}")

            all_analyses = []

            # Process positions in batches
            for i in range(0, len(all_positions), self.max_concurrent_analyses):
                batch_positions = all_positions[i:i + self.max_concurrent_analyses]
                batch_num = (i // self.max_concurrent_analyses) + 1
                total_batches = (len(all_positions) + self.max_concurrent_analyses - 1) // self.max_concurrent_analyses

                logger.info(f"Processing batch {batch_num}/{total_batches} with {len(batch_positions)} positions")

                # Create tasks for this batch
                batch_tasks = []
                for j, position in enumerate(batch_positions):
                    delay = j * self.stagger_delay  # Configurable delay between task starts within batch
                    task = self._analyze_asset_with_delay(position, delay)
                    batch_tasks.append(task)

                # Execute batch concurrently
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Process batch results
                for k, result in enumerate(batch_results):
                    position = batch_positions[k]

                    if isinstance(result, Exception):
                        logger.error(f"Error analyzing asset {position.symbol}: {str(result)}")
                        all_analyses.append(self._create_default_analysis(position))
                    elif isinstance(result, AssetAnalysis):
                        all_analyses.append(result)
                    else:
                        logger.warning(f"Unexpected result type for {position.symbol}: {type(result)}")
                        all_analyses.append(self._create_default_analysis(position))

                # Add delay between batches to prevent API rate limiting
                if i + self.max_concurrent_analyses < len(all_positions):
                    await asyncio.sleep(self.batch_delay)  # Configurable delay between batches

            logger.info(f"Completed batch processing with {len(all_analyses)} asset analyses")

            # Portfolio-level analysis
            await self._analyze_portfolio_correlations(all_analyses, portfolio)

            return all_analyses

        except Exception as e:
            logger.error(f"Error in batch portfolio analysis: {str(e)}")
            # Fallback to sequential processing
            logger.info("Falling back to sequential processing due to batch processing failure")
            return await self._sequential_portfolio_analysis(portfolio)

    async def _sequential_portfolio_analysis(self, portfolio: Portfolio) -> list[AssetAnalysis]:
        """Fallback method for sequential portfolio analysis."""
        try:
            logger.info(f"Running sequential analysis for {portfolio.total_positions} positions")

            analyses = []

            # Process stocks sequentially
            for stock in portfolio.stocks:
                try:
                    analysis = await self.analyze_asset(stock)
                    analyses.append(analysis)
                except Exception as e:
                    logger.error(f"Error analyzing stock {stock.symbol}: {str(e)}")
                    analyses.append(self._create_default_analysis(stock))

            # Process crypto sequentially
            for crypto in portfolio.crypto:
                try:
                    analysis = await self.analyze_asset(crypto)
                    analyses.append(analysis)
                except Exception as e:
                    logger.error(f"Error analyzing crypto {crypto.symbol}: {str(e)}")
                    analyses.append(self._create_default_analysis(crypto))

            # Portfolio-level analysis
            await self._analyze_portfolio_correlations(analyses, portfolio)

            return analyses

        except Exception as e:
            logger.error(f"Error in sequential portfolio analysis: {str(e)}")
            return []

    def disable_parallel_processing(self):
        """Disable parallel processing for debugging or API rate limiting."""
        self.enable_parallel_processing = False
        logger.info("Parallel processing disabled")

    def enable_parallel_processing_feature(self):
        """Enable parallel processing."""
        self.enable_parallel_processing = True
        logger.info("Parallel processing enabled")

    def set_max_concurrent_analyses(self, max_concurrent: int):
        """Set the maximum number of concurrent asset analyses."""
        self.max_concurrent_analyses = max(1, min(50, max_concurrent))  # Limit between 1-50
        logger.info(f"Max concurrent analyses set to {self.max_concurrent_analyses}")
