"""
Tavily API Client

Handles news and sentiment data collection from Tavily including:
- Recent financial news
- Market sentiment analysis
- Crypto and stock-specific news
"""

from typing import Dict, Any, List
from tavily import TavilyClient as TavilyAPI
import structlog

from quantasaurus.utils.config import Config
from quantasaurus.utils.exceptions import DataCollectionError

logger = structlog.get_logger()


class TavilyClient:
    """Client for interacting with Tavily API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = TavilyAPI(api_key=config.tavily_api_key)
    
    def get_news_data(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get news data for portfolio positions.
        
        Args:
            positions: List of portfolio positions
            
        Returns:
            News data dictionary
        """
        try:
            logger.info("Collecting news data from Tavily")
            
            news_data = {
                "stock_news": [],
                "crypto_news": [],
                "market_news": []
            }
            
            # Get stock-specific news
            stock_positions = [pos for pos in positions if pos["type"] == "stock"]
            for position in stock_positions:
                symbol = position["symbol"]
                stock_news = self._get_stock_news(symbol)
                news_data["stock_news"].extend(stock_news)
            
            # Get crypto-specific news
            crypto_positions = [pos for pos in positions if pos["type"] == "crypto"]
            for position in crypto_positions:
                symbol = position["symbol"]
                crypto_news = self._get_crypto_news(symbol)
                news_data["crypto_news"].extend(crypto_news)
            
            # Get general market news
            market_news = self._get_market_news()
            news_data["market_news"].extend(market_news)
            
            logger.info("Tavily news collection completed",
                       stock_news=len(news_data["stock_news"]),
                       crypto_news=len(news_data["crypto_news"]),
                       market_news=len(news_data["market_news"]))
            
            return news_data
            
        except Exception as e:
            logger.error("Failed to collect Tavily news data", error=str(e))
            raise DataCollectionError(f"Failed to collect news data: {str(e)}", "TAVILY_DATA_FAILED")
    
    def _get_stock_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get news for a specific stock symbol."""
        try:
            query = f"{symbol} stock earnings financials analysis"
            response = self.client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                days=7
            )
            
            news_items = []
            for result in response.get("results", []):
                news_items.append({
                    "symbol": symbol,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "published_date": result.get("published_date", ""),
                    "source": "tavily"
                })
            
            return news_items
            
        except Exception as e:
            logger.warning("Failed to get stock news", symbol=symbol, error=str(e))
            return []
    
    def _get_crypto_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get news for a specific crypto symbol."""
        try:
            query = f"{symbol} cryptocurrency bitcoin ethereum crypto market"
            response = self.client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                days=7
            )
            
            news_items = []
            for result in response.get("results", []):
                news_items.append({
                    "symbol": symbol,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "published_date": result.get("published_date", ""),
                    "source": "tavily"
                })
            
            return news_items
            
        except Exception as e:
            logger.warning("Failed to get crypto news", symbol=symbol, error=str(e))
            return []
    
    def _get_market_news(self) -> List[Dict[str, Any]]:
        """Get general market news."""
        try:
            query = "stock market financial news economy fed rates inflation"
            response = self.client.search(
                query=query,
                search_depth="basic",
                max_results=10,
                days=3
            )
            
            news_items = []
            for result in response.get("results", []):
                news_items.append({
                    "symbol": "MARKET",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "published_date": result.get("published_date", ""),
                    "source": "tavily"
                })
            
            return news_items
            
        except Exception as e:
            logger.warning("Failed to get market news", error=str(e))
            return []