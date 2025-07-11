"""
Data Collection Orchestrator

Coordinates data collection from all sources:
- Robinhood API
- Aiera API  
- Tavily API
"""

from typing import Dict, Any
import structlog

from quantasaurus.utils.config import Config
from quantasaurus.utils.exceptions import DataCollectionError
from quantasaurus.data_collection.robinhood.client import RobinhoodClient
from quantasaurus.data_collection.aiera.client import AieraClient
from quantasaurus.data_collection.tavily.client import TavilyClient

logger = structlog.get_logger()


class DataCollectionOrchestrator:
    """Orchestrates data collection from multiple sources."""
    
    def __init__(self, config: Config):
        self.config = config
        self.robinhood_client = RobinhoodClient(config)
        self.aiera_client = AieraClient(config)
        self.tavily_client = TavilyClient(config)
    
    def collect_all_data(self) -> Dict[str, Any]:
        """
        Collect data from all sources and combine into unified structure.
        
        Returns:
            Combined portfolio and market data
        """
        logger.info("Starting comprehensive data collection")
        
        try:
            # Collect portfolio data from Robinhood
            portfolio_data = self.robinhood_client.get_portfolio_data()
            
            # Collect fundamental data from Aiera
            aiera_data = self.aiera_client.get_equity_data(portfolio_data["positions"])
            
            # Collect news data from Tavily
            news_data = self.tavily_client.get_news_data(portfolio_data["positions"])
            
            # Combine all data
            combined_data = {
                "portfolio": portfolio_data,
                "fundamentals": aiera_data,
                "news": news_data,
                "positions": portfolio_data["positions"],
                "events": aiera_data.get("events", [])
            }
            
            logger.info("Data collection completed successfully")
            return combined_data
            
        except Exception as e:
            logger.error("Data collection failed", error=str(e))
            raise DataCollectionError(f"Failed to collect data: {str(e)}", "DATA_COLLECTION_FAILED")