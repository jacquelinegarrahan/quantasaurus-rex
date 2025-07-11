"""Tavily search client service."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Optional

from tavily import TavilyClient

logger = logging.getLogger(__name__)


class TavilyService:
    """Tavily search service for news and web search."""

    def __init__(self, api_key: str):
        """Initialize Tavily service."""
        self.api_key = api_key
        self.client = TavilyClient(api_key=api_key)

    async def search_news(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search for recent news about stocks/crypto."""
        try:
            logger.info(f"Searching news for query: {query}")

            # Search for news
            search_results = await self._search_with_filters(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=["bloomberg.com", "reuters.com", "cnbc.com", "marketwatch.com",
                                "yahoo.com", "wsj.com", "ft.com", "seekingalpha.com"],
                topic="news"
            )

            # Process and format results
            news_items = []
            for result in search_results.get('results', []):
                news_item = {
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "snippet": result.get('content', ''),
                    "published_date": self._parse_date(result.get('published_date')),
                    "source": self._extract_domain(result.get('url', '')),
                    "score": result.get('score', 0),
                    "raw_content": result.get('raw_content', '')
                }
                news_items.append(news_item)

            logger.info(f"Found {len(news_items)} news items for query: {query}")
            return news_items

        except Exception as e:
            logger.error(f"Error searching news for query '{query}': {str(e)}")
            return []

    async def search_market_sentiment(self, symbol: str, sector: str = None, industry: str = None) -> dict[str, Any]:
        """Search for market sentiment about specific assets with industry context."""
        try:
            logger.info(f"Searching market sentiment for {symbol} (sector: {sector}, industry: {industry})")

            # Create comprehensive search queries with industry context
            queries = [
                f"{symbol} stock price prediction analysis",
                f"{symbol} market sentiment analyst opinion",
                f"{symbol} bullish bearish outlook",
                f"{symbol} investment recommendation"
            ]

            # Add industry-specific queries if we have the information
            if sector:
                queries.extend([
                    f"{symbol} {sector} sector analysis outlook",
                    f"{symbol} {sector} industry trends performance"
                ])

            if industry:
                queries.extend([
                    f"{symbol} {industry} competitive position",
                    f"{symbol} {industry} market share analysis"
                ])

            all_results = []

            for query in queries:
                try:
                    # Use industry-specific domains if available
                    industry_domains = self._get_industry_domains(sector, industry)
                    base_domains = ["seekingalpha.com", "motleyfool.com", "investorplace.com",
                                  "marketwatch.com", "yahoo.com", "cnbc.com", "benzinga.com"]

                    results = await self._search_with_filters(
                        query=query,
                        search_depth="advanced",
                        max_results=5,
                        include_domains=base_domains + industry_domains,
                        topic="general"
                    )

                    all_results.extend(results.get('results', []))

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Error with query '{query}': {str(e)}")
                    continue

            # Analyze sentiment from results
            sentiment_analysis = self._analyze_sentiment_from_results(all_results, symbol)

            return sentiment_analysis

        except Exception as e:
            logger.error(f"Error searching market sentiment for {symbol}: {str(e)}")
            return {}

    async def search_company_events(self, symbol: str, company_name: str, sector: str = None, industry: str = None) -> list[dict[str, Any]]:
        """Search for company events and catalysts with industry context."""
        try:
            logger.info(f"Searching company events for {symbol} ({company_name}) - sector: {sector}, industry: {industry}")

            # Create event-focused queries
            queries = [
                f"{symbol} earnings call date",
                f"{symbol} {company_name} upcoming events",
                f"{symbol} dividend date announcement",
                f"{symbol} {company_name} conference presentation",
                f"{symbol} product launch announcement"
            ]

            # Add industry-specific event queries
            if sector:
                queries.extend([
                    f"{symbol} {sector} sector conference 2024",
                    f"{symbol} {sector} industry regulatory changes"
                ])

            if industry:
                queries.extend([
                    f"{symbol} {industry} trade show exhibition",
                    f"{symbol} {industry} industry trends forecast"
                ])

            all_events = []

            for query in queries:
                try:
                    # Use industry-specific domains for events
                    industry_domains = self._get_industry_domains(sector, industry)
                    base_domains = ["investor.com", "sec.gov", "businesswire.com",
                                  "prnewswire.com", "marketwatch.com", "yahoo.com"]

                    results = await self._search_with_filters(
                        query=query,
                        search_depth="basic",
                        max_results=3,
                        include_domains=base_domains + industry_domains,
                        topic="general"
                    )

                    # Extract event information
                    events = self._extract_events_from_results(results.get('results', []), symbol)
                    all_events.extend(events)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Error with query '{query}': {str(e)}")
                    continue

            # Deduplicate and sort events
            unique_events = self._deduplicate_events(all_events)

            logger.info(f"Found {len(unique_events)} events for {symbol}")
            return unique_events

        except Exception as e:
            logger.error(f"Error searching company events for {symbol}: {str(e)}")
            return []

    async def search_technical_analysis(self, symbol: str, sector: str = None, industry: str = None) -> dict[str, Any]:
        """Search for technical analysis and chart patterns with industry context."""
        try:
            logger.info(f"Searching technical analysis for {symbol} (sector: {sector}, industry: {industry})")

            # Create technical analysis queries
            queries = [
                f"{symbol} technical analysis chart pattern",
                f"{symbol} support resistance levels",
                f"{symbol} moving average crossover",
                f"{symbol} RSI MACD technical indicators"
            ]

            # Add industry-specific technical analysis queries
            if sector:
                queries.extend([
                    f"{symbol} {sector} sector rotation analysis",
                    f"{symbol} {sector} relative strength sector comparison"
                ])

            if industry:
                queries.extend([
                    f"{symbol} {industry} peer comparison technical analysis",
                    f"{symbol} {industry} industry breakout patterns"
                ])

            all_results = []

            for query in queries:
                try:
                    # Use industry-specific domains for technical analysis
                    industry_domains = self._get_industry_domains(sector, industry)
                    base_domains = ["tradingview.com", "stockcharts.com", "investing.com",
                                  "marketwatch.com", "yahoo.com", "seekingalpha.com"]

                    results = await self._search_with_filters(
                        query=query,
                        search_depth="basic",
                        max_results=3,
                        include_domains=base_domains + industry_domains,
                        topic="general"
                    )

                    all_results.extend(results.get('results', []))

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Error with query '{query}': {str(e)}")
                    continue

            # Extract technical insights
            technical_insights = self._extract_technical_insights(all_results, symbol)

            return technical_insights

        except Exception as e:
            logger.error(f"Error searching technical analysis for {symbol}: {str(e)}")
            return {}

    async def _search_with_filters(self, query: str, search_depth: str = "basic",
                                 max_results: int = 5, include_domains: list[str] = None,
                                 topic: str = "general") -> dict[str, Any]:
        """Perform search with filters."""
        try:
            search_params = {
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "topic": topic
            }

            if include_domains:
                search_params["include_domains"] = include_domains

            # Run search in executor to avoid blocking
            # Create a partial function with the search parameters
            def search_with_params():
                return self.client.search(**search_params)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, search_with_params)

            return result

        except Exception as e:
            logger.error(f"Error in search with filters: {str(e)}")
            return {"results": []}

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime object."""
        if not date_str:
            return None

        try:
            # Try different date formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            # If no format worked, return None
            return None

        except Exception:
            return None

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"

    def _analyze_sentiment_from_results(self, results: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
        """Analyze sentiment from search results."""
        try:
            # Simple sentiment analysis based on keywords
            positive_keywords = [
                "bullish", "buy", "strong", "positive", "growth", "upside", "rally",
                "outperform", "upgrade", "target", "beat", "exceed", "strong buy"
            ]

            negative_keywords = [
                "bearish", "sell", "weak", "negative", "decline", "downside", "fall",
                "underperform", "downgrade", "miss", "below", "weak", "strong sell"
            ]

            positive_count = 0
            negative_count = 0
            total_results = len(results)

            sentiment_items = []

            for result in results:
                content = (result.get('content', '') + ' ' + result.get('title', '')).lower()

                pos_score = sum(1 for keyword in positive_keywords if keyword in content)
                neg_score = sum(1 for keyword in negative_keywords if keyword in content)

                if pos_score > neg_score:
                    positive_count += 1
                    sentiment = "positive"
                elif neg_score > pos_score:
                    negative_count += 1
                    sentiment = "negative"
                else:
                    sentiment = "neutral"

                sentiment_items.append({
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "sentiment": sentiment,
                    "positive_score": pos_score,
                    "negative_score": neg_score,
                    "snippet": result.get('content', '')[:200]
                })

            # Calculate overall sentiment
            if positive_count > negative_count:
                overall_sentiment = "positive"
                sentiment_score = (positive_count / total_results) * 0.8 if total_results > 0 else 0
            elif negative_count > positive_count:
                overall_sentiment = "negative"
                sentiment_score = -(negative_count / total_results) * 0.8 if total_results > 0 else 0
            else:
                overall_sentiment = "neutral"
                sentiment_score = 0

            return {
                "symbol": symbol,
                "overall_sentiment": overall_sentiment,
                "sentiment_score": sentiment_score,
                "positive_mentions": positive_count,
                "negative_mentions": negative_count,
                "total_results": total_results,
                "sentiment_items": sentiment_items,
                "analysis_date": datetime.now(UTC).isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {}

    def _extract_events_from_results(self, results: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
        """Extract events from search results."""
        events = []

        try:
            for result in results:
                content = result.get('content', '').lower()
                title = result.get('title', '').lower()

                # Look for event indicators
                event_indicators = {
                    "earnings": ["earnings", "quarterly", "q1", "q2", "q3", "q4"],
                    "dividend": ["dividend", "payout", "ex-dividend"],
                    "conference": ["conference", "presentation", "investor day"],
                    "product": ["launch", "announcement", "unveil", "release"],
                    "acquisition": ["acquisition", "merger", "deal", "acquire"]
                }

                for event_type, keywords in event_indicators.items():
                    if any(keyword in content or keyword in title for keyword in keywords):
                        events.append({
                            "event_type": event_type,
                            "title": result.get('title', ''),
                            "url": result.get('url', ''),
                            "description": result.get('content', '')[:300],
                            "source": self._extract_domain(result.get('url', '')),
                            "symbol": symbol,
                            "importance": "medium",  # Default importance
                            "extracted_date": datetime.now(UTC).isoformat()
                        })
                        break  # Only assign one event type per result

            return events

        except Exception as e:
            logger.error(f"Error extracting events: {str(e)}")
            return []

    def _extract_technical_insights(self, results: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
        """Extract technical insights from search results."""
        try:
            technical_terms = {
                "support": ["support", "floor", "bottom"],
                "resistance": ["resistance", "ceiling", "top"],
                "bullish": ["bullish", "uptrend", "ascending"],
                "bearish": ["bearish", "downtrend", "descending"],
                "breakout": ["breakout", "breakthrough", "break above"],
                "breakdown": ["breakdown", "break below", "fall through"]
            }

            insights = {
                "symbol": symbol,
                "technical_signals": [],
                "chart_patterns": [],
                "key_levels": [],
                "analysis_summary": "",
                "sources": []
            }

            for result in results:
                content = (result.get('content', '') + ' ' + result.get('title', '')).lower()

                # Extract technical signals
                for signal, keywords in technical_terms.items():
                    if any(keyword in content for keyword in keywords):
                        insights["technical_signals"].append({
                            "signal": signal,
                            "source": self._extract_domain(result.get('url', '')),
                            "title": result.get('title', ''),
                            "snippet": result.get('content', '')[:200]
                        })

                insights["sources"].append({
                    "title": result.get('title', ''),
                    "url": result.get('url', ''),
                    "source": self._extract_domain(result.get('url', ''))
                })

            # Generate summary
            signal_counts = {}
            for signal in insights["technical_signals"]:
                signal_type = signal["signal"]
                signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1

            if signal_counts:
                top_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                insights["analysis_summary"] = f"Top technical signals: {', '.join([f'{signal} ({count})' for signal, count in top_signals])}"

            return insights

        except Exception as e:
            logger.error(f"Error extracting technical insights: {str(e)}")
            return {}

    def _get_industry_domains(self, sector: str = None, industry: str = None) -> list[str]:
        """Get industry-specific domains for more targeted searches."""
        industry_domains = []

        if not sector and not industry:
            return industry_domains

        # Technology sector specific domains
        if sector and "technology" in sector.lower():
            industry_domains.extend(["techcrunch.com", "arstechnica.com", "theverge.com", "wired.com"])

        # Healthcare/Biotech specific domains
        if sector and any(term in sector.lower() for term in ["healthcare", "biotech", "pharmaceutical"]):
            industry_domains.extend(["biopharmadive.com", "fiercebiotech.com", "biospace.com"])

        # Energy sector specific domains
        if sector and "energy" in sector.lower():
            industry_domains.extend(["oilprice.com", "energyvoice.com", "rigzone.com"])

        # Financial sector specific domains
        if sector and "financial" in sector.lower():
            industry_domains.extend(["americanbanker.com", "bankingdive.com", "insurancejournal.com"])

        # Retail/Consumer specific domains
        if sector and any(term in sector.lower() for term in ["retail", "consumer"]):
            industry_domains.extend(["retaildive.com", "chainstoreage.com", "nrf.com"])

        # Real Estate specific domains
        if sector and "real estate" in sector.lower():
            industry_domains.extend(["bisnow.com", "globest.com", "reit.com"])

        # Manufacturing/Industrial specific domains
        if sector and any(term in sector.lower() for term in ["manufacturing", "industrial"]):
            industry_domains.extend(["industryweek.com", "manufacturingdive.com", "plantservices.com"])

        return industry_domains

    def _deduplicate_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate events based on title similarity."""
        try:
            unique_events = []
            seen_titles = set()

            for event in events:
                title = event.get('title', '').lower()
                # Simple deduplication based on title
                title_key = ' '.join(sorted(title.split()))

                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_events.append(event)

            # Sort by extracted date
            unique_events.sort(key=lambda x: x.get('extracted_date', ''), reverse=True)

            return unique_events

        except Exception as e:
            logger.error(f"Error deduplicating events: {str(e)}")
            return events
