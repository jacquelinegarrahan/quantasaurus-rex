"""Aiera API client service."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class AieraService:
    """Aiera API service for financial data and analysis."""

    def __init__(self, api_key: str):
        """Initialize Aiera service."""
        self.api_key = api_key
        self.base_url = "https://premium.aiera.com/api"
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "User-Agent": "Quantasaurus-Rex/1.0"
        }
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=self.headers
        )
        # Cache for ticker to permid mapping
        self.ticker_to_permid_cache = {}

    async def _get_permid_from_ticker(self, ticker: str) -> Optional[str]:
        """Get permid for a given ticker symbol."""
        try:
            # Check cache first
            if ticker in self.ticker_to_permid_cache:
                return self.ticker_to_permid_cache[ticker]

            # Try to get permid from the equities endpoint (assuming it still supports ticker)
            url = f"{self.base_url}/equities"
            params = {
                "ticker": ticker,
                "limit": 1
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                permid = None

                # Extract permid from response - check various response formats
                if isinstance(data, list) and len(data) > 0:
                    permid = data[0].get('permid')
                elif isinstance(data, dict):
                    if data.get('data') and len(data['data']) > 0:
                        permid = data['data'][0].get('permid')
                    elif data.get('results') and len(data['results']) > 0:
                        permid = data['results'][0].get('permid')
                    elif data.get('permid'):
                        permid = data.get('permid')

                if permid:
                    # Cache the result
                    self.ticker_to_permid_cache[ticker] = permid
                    logger.debug(f"Found permid {permid} for ticker {ticker}")
                    return permid
                else:
                    logger.warning(f"No permid found for ticker {ticker} in API response")
                    return None
            else:
                logger.warning(f"Failed to fetch permid for ticker {ticker}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching permid for ticker {ticker}: {str(e)}")
            return None

    async def get_company_info(self, symbol: str) -> dict[str, Any]:
        """Get company information and analysis."""
        try:
            logger.info(f"Fetching company info for {symbol}...")

            # Get company profile
            company_data = await self._get_company_profile(symbol)

            # Get company metrics
            metrics_data = await self._get_company_metrics(symbol)

            # Get analyst ratings
            ratings_data = await self._get_analyst_ratings(symbol)

            # Combine all data
            company_info = {
                "symbol": symbol,
                "profile": company_data,
                "metrics": metrics_data,
                "ratings": ratings_data,
                "last_updated": datetime.now(UTC).isoformat()
            }

            return company_info

        except Exception as e:
            logger.error(f"Error fetching company info for {symbol}: {str(e)}")
            return {}

    async def _get_company_profile(self, symbol: str) -> dict[str, Any]:
        """Get company profile data."""
        try:
            url = f"{self.base_url}/equities"
            params = {
                "ticker": symbol,
                "limit": 1
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                # Handle both list and dict responses
                if isinstance(data, list):
                    # If API returns a list directly
                    if len(data) > 0:
                        return data[0]
                    return {}
                elif isinstance(data, dict):
                    # If API returns a dict with 'data' key
                    if data.get('data') and len(data['data']) > 0:
                        return data['data'][0]
                    # If API returns a dict with 'results' key
                    elif data.get('results') and len(data['results']) > 0:
                        return data['results'][0]
                    # If the dict itself is the data
                    elif data:
                        return data
                return {}
            else:
                logger.warning(f"Failed to fetch company profile for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {str(e)}")
            return {}

    async def _get_company_metrics(self, symbol: str) -> dict[str, Any]:
        """Get company financial metrics from alternative sources."""
        try:
            logger.debug(f"Fetching company metrics for {symbol} from alternative sources...")

            # Try to get metrics from the company profile data instead
            profile_data = await self._get_company_profile(symbol)

            # Extract financial metrics from profile if available
            metrics = {}
            if profile_data:
                # Extract any financial metrics from the profile data
                metrics.update({
                    "market_cap": profile_data.get("market_cap"),
                    "sector": profile_data.get("sector"),
                    "industry": profile_data.get("industry"),
                    "exchange": profile_data.get("exchange"),
                    "currency": profile_data.get("currency"),
                    "description": profile_data.get("description"),
                    "website": profile_data.get("website"),
                    "employees": profile_data.get("employees"),
                    "founded": profile_data.get("founded")
                })

                # Remove None values
                metrics = {k: v for k, v in metrics.items() if v is not None}

            logger.debug(f"Retrieved {len(metrics)} metrics for {symbol}")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching company metrics for {symbol}: {str(e)}")
            return {}

    async def _get_analyst_ratings(self, symbol: str) -> dict[str, Any]:
        """Get analyst ratings data."""
        try:
            # Use topics endpoint to get analyst coverage and ratings
            url = f"{self.base_url}/topics"
            params = {
                "ticker": symbol,
                "topic_type": "analyst",
                "limit": 10
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch analyst ratings for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching analyst ratings for {symbol}: {str(e)}")
            return {}

    async def get_earnings_data(self, symbol: str) -> dict[str, Any]:
        """Get earnings call data and transcripts."""
        try:
            logger.info(f"Fetching earnings data for {symbol}...")

            # Get earnings calendar
            calendar_data = await self._get_earnings_calendar(symbol)

            # Get recent earnings calls
            calls_data = await self._get_earnings_calls(symbol)

            # Get earnings transcripts
            transcripts_data = await self._get_earnings_transcripts(symbol)

            earnings_data = {
                "symbol": symbol,
                "calendar": calendar_data,
                "calls": calls_data,
                "transcripts": transcripts_data,
                "last_updated": datetime.now(UTC).isoformat()
            }

            return earnings_data

        except Exception as e:
            logger.error(f"Error fetching earnings data for {symbol}: {str(e)}")
            return {}

    async def _get_earnings_calendar(self, symbol: str) -> dict[str, Any]:
        """Get earnings calendar data."""
        try:
            url = f"{self.base_url}/calendar"
            params = {
                "ticker": symbol,
                "event_type": "earnings",
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch earnings calendar for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching earnings calendar for {symbol}: {str(e)}")
            return {}

    async def _get_earnings_calls(self, symbol: str) -> dict[str, Any]:
        """Get earnings calls data."""
        try:
            url = f"{self.base_url}/events-v2"
            params = {
                "ticker": symbol,
                "event_type": "earnings",
                "limit": 5,
                "order": "desc"
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch earnings calls for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching earnings calls for {symbol}: {str(e)}")
            return {}

    async def _get_earnings_transcripts(self, symbol: str) -> dict[str, Any]:
        """Get earnings transcripts data."""
        try:
            url = f"{self.base_url}/events-v2"
            params = {
                "ticker": symbol,
                "event_type": "earnings",
                "include_transcript": True,
                "limit": 3,
                "order": "desc"
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch earnings transcripts for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching earnings transcripts for {symbol}: {str(e)}")
            return {}

    async def get_events(self, symbol: str) -> list[dict[str, Any]]:
        """Get upcoming events for a company."""
        try:
            logger.info(f"Fetching events for {symbol}...")

            # Get corporate events
            events_data = await self._get_corporate_events(symbol)

            # Get analyst events
            analyst_events = await self._get_analyst_events(symbol)

            # Get conference events
            conference_events = await self._get_conference_events(symbol)

            # Combine all events
            all_events = []

            if events_data.get('events'):
                all_events.extend(events_data['events'])

            if analyst_events.get('events'):
                all_events.extend(analyst_events['events'])

            if conference_events.get('events'):
                all_events.extend(conference_events['events'])

            # Sort events by date
            all_events.sort(key=lambda x: x.get('date', ''))

            return all_events

        except Exception as e:
            logger.error(f"Error fetching events for {symbol}: {str(e)}")
            return []

    async def _get_corporate_events(self, symbol: str) -> dict[str, Any]:
        """Get corporate events."""
        try:
            url = f"{self.base_url}/events-v2"
            params = {
                "ticker": symbol,
                "event_type": "corporate",
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch corporate events for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching corporate events for {symbol}: {str(e)}")
            return {}

    async def _get_analyst_events(self, symbol: str) -> dict[str, Any]:
        """Get analyst events."""
        try:
            url = f"{self.base_url}/events-v2"
            params = {
                "ticker": symbol,
                "event_type": "analyst",
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch analyst events for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching analyst events for {symbol}: {str(e)}")
            return {}

    async def _get_conference_events(self, symbol: str) -> dict[str, Any]:
        """Get conference events."""
        try:
            url = f"{self.base_url}/events-v2"
            params = {
                "ticker": symbol,
                "event_type": "conference",
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch conference events for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching conference events for {symbol}: {str(e)}")
            return {}

    async def get_sentiment_data(self, symbol: str) -> dict[str, Any]:
        """Get sentiment analysis data from Aiera."""
        try:
            logger.info(f"Fetching sentiment data for {symbol}...")

            url = f"{self.base_url}/summaries"
            params = {
                "ticker": symbol,
                "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "limit": 20
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch sentiment data for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching sentiment data for {symbol}: {str(e)}")
            return {}

    async def get_news_analysis(self, symbol: str) -> dict[str, Any]:
        """Get news analysis data from Aiera."""
        try:
            logger.info(f"Fetching news analysis for {symbol}...")

            url = f"{self.base_url}/content"
            params = {
                "ticker": symbol,
                "content_type": "news",
                "start_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "limit": 20
            }
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch news analysis for {symbol}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching news analysis for {symbol}: {str(e)}")
            return {}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        _ = exc_type, exc_val, exc_tb  # Unused but required for context manager protocol
        await self.close()
