"""Test configuration for Quantasaurus Rex."""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Load environment variables from .env file for testing
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded test environment variables from {env_path}")
    else:
        print("⚠️  No .env file found for testing, using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not available for testing, using system environment variables")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.settings import Settings, RobinhoodConfig
from src.models.portfolio import Portfolio, StockPosition, CryptoPosition
from src.models.analysis import AssetAnalysis, TechnicalAnalysis, SentimentAnalysis, EventAnalysis, RiskAssessment


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        openai_api_key="test-openai-key",
        tavily_api_key="test-tavily-key",
        aiera_api_key="test-aiera-key",
        robinhood=RobinhoodConfig(
            username="test-user",
            password="test-password"
        ),
        email_sender="test@example.com",
        email_recipient="recipient@example.com",
        environment="test"
    )


@pytest.fixture
def sample_stock_position():
    """Create a sample stock position for testing."""
    return StockPosition(
        symbol="AAPL",
        quantity=10,
        current_price=150.00,
        market_value=1500.00,
        company_name="Apple Inc."
    )


@pytest.fixture
def sample_crypto_position():
    """Create a sample crypto position for testing."""
    return CryptoPosition(
        symbol="BTC",
        quantity=0.1,
        current_price=50000.00,
        market_value=5000.00,
        full_name="Bitcoin"
    )


@pytest.fixture
def sample_portfolio(sample_stock_position, sample_crypto_position):
    """Create a sample portfolio for testing."""
    return Portfolio(
        stocks=[sample_stock_position],
        crypto=[sample_crypto_position],
        total_value=6500.00
    )


@pytest.fixture
def sample_technical_analysis():
    """Create a sample technical analysis for testing."""
    from src.models.analysis import TechnicalIndicators, TrendDirection
    
    return TechnicalAnalysis(
        indicators=TechnicalIndicators(
            sma_20=145.00,
            sma_50=140.00,
            rsi=65.0
        ),
        trend=TrendDirection.BULLISH,
        technical_score=0.7,
        confidence=0.8,
        summary="Bullish technical outlook"
    )


@pytest.fixture
def sample_sentiment_analysis():
    """Create a sample sentiment analysis for testing."""
    from src.models.analysis import SentimentLevel
    
    return SentimentAnalysis(
        sentiment_level=SentimentLevel.POSITIVE,
        sentiment_score=0.3,
        news_sentiment=SentimentLevel.POSITIVE,
        confidence=0.75,
        summary="Positive market sentiment"
    )


@pytest.fixture
def sample_event_analysis():
    """Create a sample event analysis for testing."""
    return EventAnalysis(
        overall_impact="positive",
        confidence=0.6
    )


@pytest.fixture
def sample_risk_assessment():
    """Create a sample risk assessment for testing."""
    from src.models.analysis import RiskLevel, RiskMetrics
    
    return RiskAssessment(
        risk_level=RiskLevel.MEDIUM,
        risk_score=0.4,
        metrics=RiskMetrics(
            price_volatility=0.25,
            beta=1.1
        ),
        summary="Medium risk investment",
        confidence=0.8
    )


@pytest.fixture
def sample_asset_analysis(sample_technical_analysis, sample_sentiment_analysis, 
                         sample_event_analysis, sample_risk_assessment):
    """Create a sample asset analysis for testing."""
    from src.models.analysis import Recommendation
    
    return AssetAnalysis(
        symbol="AAPL",
        asset_type="stock",
        current_price=150.00,
        market_value=1500.00,
        technical_analysis=sample_technical_analysis,
        sentiment_analysis=sample_sentiment_analysis,
        event_analysis=sample_event_analysis,
        risk_assessment=sample_risk_assessment,
        recommendation=Recommendation.BUY,
        overall_score=0.7,
        confidence=0.8,
        reasoning="Strong technical and fundamental outlook"
    )


@pytest.fixture
def mock_robinhood_service():
    """Create a mock Robinhood service."""
    service = Mock()
    service.authenticate = AsyncMock(return_value=True)
    service.get_portfolio = AsyncMock()
    service.get_stock_fundamentals = AsyncMock(return_value={})
    service.get_historical_data = AsyncMock(return_value={})
    service.logout = AsyncMock()
    return service


@pytest.fixture
def mock_aiera_service():
    """Create a mock Aiera service."""
    service = Mock()
    service.get_company_info = AsyncMock(return_value={})
    service.get_earnings_data = AsyncMock(return_value={})
    service.get_events = AsyncMock(return_value=[])
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_tavily_service():
    """Create a mock Tavily service."""
    service = Mock()
    service.search_news = AsyncMock(return_value=[])
    service.search_market_sentiment = AsyncMock(return_value={})
    service.search_company_events = AsyncMock(return_value=[])
    return service


@pytest.fixture
def mock_email_service():
    """Create a mock email service."""
    service = Mock()
    service.generate_html_report = Mock(return_value="<html>Test Report</html>")
    service.send_report = AsyncMock(return_value=True)
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_react_agent():
    """Create a mock ReAct agent."""
    agent = Mock()
    agent.initialize_services = AsyncMock()
    agent.analyze_asset = AsyncMock()
    agent.generate_portfolio_analysis = AsyncMock(return_value=[])
    return agent


@pytest.fixture
def lambda_event():
    """Create a sample Lambda event for testing."""
    return {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {},
        "time": "2024-01-01T13:00:00Z",
        "region": "us-east-1",
        "account": "123456789012"
    }


@pytest.fixture
def lambda_context():
    """Create a sample Lambda context for testing."""
    context = Mock()
    context.function_name = "quantasaurus-rex-test"
    context.function_version = "$LATEST"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:quantasaurus-rex-test"
    context.memory_limit_in_mb = 1024
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/quantasaurus-rex-test"
    context.log_stream_name = "test-stream"
    context.get_remaining_time_in_millis = Mock(return_value=300000)
    return context


@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 client."""
    client = Mock()
    client.send_email = Mock(return_value={"MessageId": "test-message-id"})
    client.get_parameter = Mock(return_value={"Parameter": {"Value": "test-value"}})
    client.put_parameter = Mock()
    client.delete_parameter = Mock()
    return client


@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Set up test environment variables."""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "TAVILY_API_KEY": "test-tavily-key",
        "AIERA_API_KEY": "test-aiera-key",
        "EMAIL_SENDER": "test@example.com",
        "EMAIL_RECIPIENT": "recipient@example.com",
        "ROBINHOOD__USERNAME": "test-user",
        "ROBINHOOD__PASSWORD": "test-password",
        "ENVIRONMENT": "test",
        "AWS_REGION": "us-east-1"
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Clean up
    for key in test_env:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    return [
        {"date": "2024-01-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0, "volume": 1000000},
        {"date": "2024-01-02", "open": 102.0, "high": 108.0, "low": 101.0, "close": 106.0, "volume": 1200000},
        {"date": "2024-01-03", "open": 106.0, "high": 110.0, "low": 104.0, "close": 108.0, "volume": 1100000},
        {"date": "2024-01-04", "open": 108.0, "high": 112.0, "low": 107.0, "close": 110.0, "volume": 1300000},
        {"date": "2024-01-05", "open": 110.0, "high": 115.0, "low": 109.0, "close": 113.0, "volume": 1400000}
    ]


class AsyncContextManager:
    """Helper class for async context manager testing."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.entered = False
        self.exited = False
    
    async def __aenter__(self):
        self.entered = True
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exited = True
        return False


@pytest.fixture
def async_context_manager():
    """Create an async context manager for testing."""
    return AsyncContextManager