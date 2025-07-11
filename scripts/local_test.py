#!/usr/bin/env python3
"""Local testing script for Quantasaurus Rex."""

# Suppress warnings early
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*langchain_core.pydantic_v1.*")
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")

import asyncio
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print("⚠️  No .env file found, using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.lambda_handler import QuantasaurusLambdaHandler
from src.config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress LangChain Pydantic deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*langchain_core.pydantic_v1.*")

logger = logging.getLogger(__name__)


class MockRobinhoodService:
    """Mock Robinhood service for testing."""
    
    def __init__(self, config):
        self.config = config
        self.authenticated = False
    
    async def authenticate(self) -> bool:
        """Mock authentication."""
        logger.info("Mock: Authenticating with Robinhood...")
        await asyncio.sleep(1)  # Simulate API call
        self.authenticated = True
        return True
    
    async def get_portfolio(self):
        """Mock portfolio data."""
        logger.info("Mock: Fetching portfolio data...")
        await asyncio.sleep(1)
        
        # Import models after path is set
        from src.models.portfolio import Portfolio, StockPosition, CryptoPosition
        
        # Create mock portfolio
        stocks = [
            StockPosition(
                symbol="AAPL",
                quantity=10,
                current_price=150.00,
                market_value=1500.00,
                company_name="Apple Inc."
            ),
            StockPosition(
                symbol="GOOGL",
                quantity=5,
                current_price=2800.00,
                market_value=14000.00,
                company_name="Alphabet Inc."
            )
        ]
        
        crypto = [
            CryptoPosition(
                symbol="BTC",
                quantity=0.1,
                current_price=50000.00,
                market_value=5000.00,
                full_name="Bitcoin"
            )
        ]
        
        portfolio = Portfolio.create_portfolio(
            stocks=stocks,
            crypto=crypto
        )
        
        return portfolio
    
    async def get_stock_fundamentals(self, symbols):
        """Mock fundamentals data."""
        logger.info(f"Mock: Fetching fundamentals for {symbols}")
        return {symbol: {"pe_ratio": 25.0, "market_cap": 2000000000} for symbol in symbols}
    
    async def get_historical_data(self, symbols):
        """Mock historical data."""
        logger.info(f"Mock: Fetching historical data for {symbols}")
        return {symbol: {"data": [{"close": 100.0}, {"close": 105.0}]} for symbol in symbols}
    
    async def logout(self):
        """Mock logout."""
        logger.info("Mock: Logging out from Robinhood...")
        self.authenticated = False


class MockAieraService:
    """Mock Aiera service for testing."""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    async def get_company_info(self, symbol):
        """Mock company info."""
        logger.info(f"Mock: Fetching company info for {symbol}")
        return {"symbol": symbol, "sector": "Technology", "industry": "Software"}
    
    async def close(self):
        """Mock close."""
        pass


class MockTavilyService:
    """Mock Tavily service for testing."""
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    async def search_news(self, query, max_results=10):
        """Mock news search."""
        logger.info(f"Mock: Searching news for {query}")
        return [
            {
                "title": f"News about {query}",
                "url": "https://example.com/news",
                "snippet": "Mock news content",
                "published_date": "2024-01-01T00:00:00Z",
                "source": "mock-source"
            }
        ]
    
    async def search_market_sentiment(self, symbol):
        """Mock sentiment search."""
        logger.info(f"Mock: Searching sentiment for {symbol}")
        return {
            "symbol": symbol,
            "overall_sentiment": "positive",
            "sentiment_score": 0.7,
            "confidence": 0.8
        }


class MockEmailService:
    """Mock email service that saves emails to files."""
    
    def __init__(self, settings):
        self.settings = settings
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_html_report(self, portfolio, analyses):
        """Generate HTML report."""
        logger.info("Mock: Generating HTML email report...")
        # Import here to avoid circular imports
        from src.services.email_service import EmailService
        
        # Create a real email service instance just for HTML generation
        real_service = EmailService(self.settings)
        html_content = real_service.generate_html_report(portfolio, analyses)
        return html_content
    
    async def send_report(self, html_content, subject=None):
        """Save report to file instead of sending."""
        logger.info("Mock: Saving email report to file instead of sending...")
        
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"portfolio_report_{timestamp}.html"
            filepath = self.output_dir / filename
            
            # Save HTML content to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Mock: Saved HTML report to {filepath}")
            
            return True
            
        except Exception as e:
            logger.error(f"Mock: Error saving email report: {str(e)}")
            return False
    
    async def close(self):
        """Mock close."""
        pass


class LocalTestRunner:
    """Local test runner for Quantasaurus Rex."""
    
    def __init__(self):
        self.handler = QuantasaurusLambdaHandler()
        self.use_mocks = True
    
    async def run_test(self, test_type="full"):
        """Run local test."""
        try:
            logger.info(f"Starting local test: {test_type}")
            
            # Initialize handler
            await self.handler.initialize()
            
            # Replace services with mocks if needed
            if self.use_mocks:
                await self._setup_mocks()
            
            # Always use mock email service for local testing
            await self._setup_email_mock()
            
            # Run test based on type
            if test_type == "full":
                result = await self.handler.process_portfolio()
            elif test_type == "health":
                result = await self.handler.health_check()
            else:
                raise ValueError(f"Unknown test type: {test_type}")
            
            logger.info("Test completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise
    
    async def _setup_mocks(self):
        """Set up mock services."""
        logger.info("Setting up mock services...")
        
        # Replace services with mocks
        self.handler.robinhood_service = MockRobinhoodService(self.handler.settings.robinhood)
        self.handler.aiera_service = MockAieraService(self.handler.settings.aiera_api_key)
        self.handler.tavily_service = MockTavilyService(self.handler.settings.tavily_api_key)
        
        # Re-initialize agent with mock services
        await self.handler.react_agent.initialize_services(
            self.handler.robinhood_service,
            self.handler.aiera_service,
            self.handler.tavily_service
        )
    
    async def _setup_email_mock(self):
        """Set up mock email service (always used for local testing)."""
        logger.info("Setting up mock email service for local testing...")
        
        # Always replace email service with mock for local testing
        self.handler.email_service = MockEmailService(self.handler.settings)


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local test runner for Quantasaurus Rex")
    parser.add_argument(
        "--test-type",
        choices=["full", "health"],
        default="full",
        help="Type of test to run"
    )
    parser.add_argument(
        "--no-mocks",
        action="store_true",
        help="Use real services instead of mocks"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check environment variables
    required_vars = [
        "OPENAI_API_KEY",
        "ROBINHOOD__USERNAME",
        "ROBINHOOD__PASSWORD",
        "EMAIL_SENDER"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
        if not args.no_mocks:
            logger.info("Using mocks for missing services")
        else:
            logger.error("Cannot run without mocks when environment variables are missing")
            return 1
    
    # Run test
    runner = LocalTestRunner()
    runner.use_mocks = not args.no_mocks
    
    try:
        result = asyncio.run(runner.run_test(args.test_type))
        
        # Print results
        print("\n" + "="*50)
        print("TEST RESULTS")
        print("="*50)
        print(json.dumps(result, indent=2, default=str))
        
        # Check if any files were saved
        output_dir = Path(__file__).parent.parent / "output"
        if output_dir.exists():
            html_files = list(output_dir.glob("portfolio_report_*.html"))
            json_files = list(output_dir.glob("portfolio_report_*.json"))
            
            if html_files or json_files:
                print("\n" + "="*50)
                print("SAVED FILES")
                print("="*50)
                for file in sorted(html_files + json_files):
                    print(f"📄 {file.name}")
                print(f"\n📁 All files saved to: {output_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())