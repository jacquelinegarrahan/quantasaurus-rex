"""
Aiera API Client

Handles fundamental analysis data collection from Aiera including:
- Corporate events and earnings calls
- Financial news and SEC filings
- Company fundamentals and market data
"""

from typing import Dict, Any, List
import requests
import structlog

from quantasaurus.utils.config import Config
from quantasaurus.utils.exceptions import DataCollectionError

logger = structlog.get_logger()


class AieraClient:
    """Client for interacting with Aiera API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.aiera_api_url
        self.api_key = config.aiera_api_key
        self.timeout = config.aiera_api_timeout
    
    def get_equity_data(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get equity data for portfolio positions.
        
        Args:
            positions: List of portfolio positions
            
        Returns:
            Equity data dictionary
        """
        try:
            logger.info("Collecting equity data from Aiera")
            
            # Filter stock positions only
            stock_positions = [pos for pos in positions if pos["type"] == "stock"]
            
            equity_data = {
                "equities": [],
                "events": [],
                "news": [],
                "filings": []
            }
            
            for position in stock_positions:
                symbol = position["symbol"]
                
                # Get equity information
                equity_info = self._get_equity_info(symbol)
                if equity_info:
                    equity_data["equities"].append(equity_info)
                
                # Get corporate events
                events = self._get_corporate_events(symbol)
                equity_data["events"].extend(events)
                
                # Get news
                news = self._get_equity_news(symbol)
                equity_data["news"].extend(news)
                
                # Get filings
                filings = self._get_equity_filings(symbol)
                equity_data["filings"].extend(filings)
            
            logger.info("Aiera data collection completed", 
                       equities=len(equity_data["equities"]),
                       events=len(equity_data["events"]),
                       news=len(equity_data["news"]),
                       filings=len(equity_data["filings"]))
            
            return equity_data
            
        except Exception as e:
            logger.error("Failed to collect Aiera data", error=str(e))
            raise DataCollectionError(f"Failed to collect Aiera data: {str(e)}", "AIERA_DATA_FAILED")
    
    def _get_equity_info(self, symbol: str) -> Dict[str, Any]:
        """Get equity information for a symbol."""
        try:
            response = requests.get(
                f"{self.base_url}/equities/",
                params={"ticker": symbol},
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            logger.warning("Failed to get equity info", symbol=symbol, error=str(e))
            return None
    
    def _get_corporate_events(self, symbol: str) -> List[Dict[str, Any]]:
        """Get corporate events for a symbol."""
        try:
            response = requests.get(
                f"{self.base_url}/events/",
                params={"ticker": symbol},
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Failed to get corporate events", symbol=symbol, error=str(e))
            return []
    
    def _get_equity_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get news for a symbol."""
        try:
            response = requests.get(
                f"{self.base_url}/content/news/",
                params={"ticker": symbol},
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Failed to get equity news", symbol=symbol, error=str(e))
            return []
    
    def _get_equity_filings(self, symbol: str) -> List[Dict[str, Any]]:
        """Get SEC filings for a symbol."""
        try:
            response = requests.get(
                f"{self.base_url}/content/filings/",
                params={"ticker": symbol},
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Failed to get equity filings", symbol=symbol, error=str(e))
            return []