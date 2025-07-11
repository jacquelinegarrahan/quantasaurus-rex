"""Test parallel processing functionality in ReAct agent."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.services.react_agent import QuantasaurusReactAgent
from src.config.settings import Settings
from src.models.portfolio import Portfolio, StockPosition, CryptoPosition, AssetType
from src.models.analysis import AssetAnalysis, Recommendation


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.openai_api_key = "test_key"
    settings.openai_model = "gpt-4"
    settings.enable_parallel_processing = True
    settings.max_concurrent_analyses = 5
    settings.api_rate_limit_delay = 0.1
    settings.batch_delay = 0.2
    settings.stagger_delay = 0.05
    return settings


@pytest.fixture
def sample_portfolio():
    """Create a sample portfolio for testing."""
    stocks = [
        StockPosition.create_position(
            symbol="AAPL",
            quantity=10,
            current_price=150.0,
            company_name="Apple Inc."
        ),
        StockPosition.create_position(
            symbol="GOOGL",
            quantity=5,
            current_price=2800.0,
            company_name="Alphabet Inc."
        ),
        StockPosition.create_position(
            symbol="MSFT",
            quantity=8,
            current_price=300.0,
            company_name="Microsoft Corporation"
        )
    ]
    
    crypto = [
        CryptoPosition.create_position(
            symbol="BTC",
            quantity=0.5,
            current_price=50000.0,
            full_name="Bitcoin"
        ),
        CryptoPosition.create_position(
            symbol="ETH",
            quantity=2.0,
            current_price=3000.0,
            full_name="Ethereum"
        )
    ]
    
    return Portfolio.create_portfolio(stocks=stocks, crypto=crypto)


@pytest.mark.asyncio
async def test_react_agent_parallel_processing_initialization(mock_settings):
    """Test that the ReAct agent initializes with parallel processing settings."""
    agent = QuantasaurusReactAgent(mock_settings)
    
    assert agent.enable_parallel_processing is True
    assert agent.max_concurrent_analyses == 5
    assert agent.api_rate_limit_delay == 0.1
    assert agent.batch_delay == 0.2
    assert agent.stagger_delay == 0.05


@pytest.mark.asyncio
async def test_parallel_processing_disabled_fallback(mock_settings, sample_portfolio):
    """Test that sequential processing is used when parallel processing is disabled."""
    # Disable parallel processing
    mock_settings.enable_parallel_processing = False
    
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Mock the sequential analysis method
    with patch.object(agent, '_sequential_portfolio_analysis', new_callable=AsyncMock) as mock_sequential:
        mock_sequential.return_value = []
        
        result = await agent.generate_portfolio_analysis(sample_portfolio)
        
        # Verify sequential method was called
        mock_sequential.assert_called_once_with(sample_portfolio)
        assert result == []


@pytest.mark.asyncio
async def test_parallel_processing_with_small_portfolio(mock_settings, sample_portfolio):
    """Test parallel processing with a small portfolio."""
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Mock the analyze_asset method to return dummy analysis
    with patch.object(agent, 'analyze_asset', new_callable=AsyncMock) as mock_analyze:
        mock_analysis = Mock(spec=AssetAnalysis)
        mock_analysis.symbol = "TEST"
        mock_analysis.recommendation = Recommendation.HOLD
        mock_analyze.return_value = mock_analysis
        
        # Mock portfolio correlations
        with patch.object(agent, '_analyze_portfolio_correlations', new_callable=AsyncMock) as mock_correlations:
            result = await agent.generate_portfolio_analysis(sample_portfolio)
            
            # Verify analyze_asset was called for each position
            assert mock_analyze.call_count == 5  # 3 stocks + 2 crypto
            
            # Verify correlations analysis was called
            mock_correlations.assert_called_once()
            
            # Verify results
            assert len(result) == 5
            assert all(isinstance(analysis, Mock) for analysis in result)


@pytest.mark.asyncio
async def test_batch_processing_with_large_portfolio(mock_settings):
    """Test batch processing with a large portfolio."""
    # Create a large portfolio that exceeds max_concurrent_analyses
    large_stocks = [
        StockPosition.create_position(
            symbol=f"STOCK{i}",
            quantity=1,
            current_price=100.0,
            company_name=f"Company {i}"
        ) for i in range(10)  # 10 stocks, max concurrent is 5
    ]
    
    large_portfolio = Portfolio.create_portfolio(stocks=large_stocks, crypto=[])
    
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Mock the batch analysis method
    with patch.object(agent, '_batch_portfolio_analysis', new_callable=AsyncMock) as mock_batch:
        mock_batch.return_value = []
        
        result = await agent.generate_portfolio_analysis(large_portfolio)
        
        # Verify batch method was called
        mock_batch.assert_called_once()
        assert result == []


@pytest.mark.asyncio
async def test_parallel_processing_error_handling(mock_settings, sample_portfolio):
    """Test error handling in parallel processing."""
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Mock analyze_asset to raise an exception for some assets
    async def mock_analyze_asset(position):
        if position.symbol == "AAPL":
            raise Exception("API Error")
        else:
            mock_analysis = Mock(spec=AssetAnalysis)
            mock_analysis.symbol = position.symbol
            mock_analysis.recommendation = Recommendation.HOLD
            return mock_analysis
    
    with patch.object(agent, 'analyze_asset', side_effect=mock_analyze_asset):
        with patch.object(agent, '_create_default_analysis') as mock_default:
            mock_default.return_value = Mock(spec=AssetAnalysis)
            
            with patch.object(agent, '_analyze_portfolio_correlations', new_callable=AsyncMock):
                result = await agent.generate_portfolio_analysis(sample_portfolio)
                
                # Verify default analysis was created for failed asset
                mock_default.assert_called()
                
                # Verify we still got results for all positions
                assert len(result) == 5


@pytest.mark.asyncio
async def test_parallel_processing_methods_exist(mock_settings):
    """Test that all parallel processing methods exist."""
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Check that all required methods exist
    assert hasattr(agent, '_analyze_asset_with_delay')
    assert hasattr(agent, '_batch_portfolio_analysis')
    assert hasattr(agent, '_sequential_portfolio_analysis')
    assert hasattr(agent, 'disable_parallel_processing')
    assert hasattr(agent, 'enable_parallel_processing_feature')
    assert hasattr(agent, 'set_max_concurrent_analyses')


@pytest.mark.asyncio
async def test_parallel_processing_configuration_methods(mock_settings):
    """Test parallel processing configuration methods."""
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Test disabling parallel processing
    agent.disable_parallel_processing()
    assert agent.enable_parallel_processing is False
    
    # Test enabling parallel processing
    agent.enable_parallel_processing_feature()
    assert agent.enable_parallel_processing is True
    
    # Test setting max concurrent analyses
    agent.set_max_concurrent_analyses(15)
    assert agent.max_concurrent_analyses == 15
    
    # Test bounds checking
    agent.set_max_concurrent_analyses(100)  # Should be capped at 50
    assert agent.max_concurrent_analyses == 50
    
    agent.set_max_concurrent_analyses(0)  # Should be minimum 1
    assert agent.max_concurrent_analyses == 1


@pytest.mark.asyncio
async def test_staggered_delays_in_parallel_processing(mock_settings):
    """Test that staggered delays are applied in parallel processing."""
    agent = QuantasaurusReactAgent(mock_settings)
    
    # Create a position for testing
    position = StockPosition.create_position(
        symbol="TEST",
        quantity=1,
        current_price=100.0
    )
    
    # Test that _analyze_asset_with_delay applies the delay
    with patch.object(agent, 'analyze_asset', new_callable=AsyncMock) as mock_analyze:
        mock_analysis = Mock(spec=AssetAnalysis)
        mock_analyze.return_value = mock_analysis
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await agent._analyze_asset_with_delay(position, delay=0.5)
            
            # Verify sleep was called with the correct delays
            mock_sleep.assert_any_call(0.5)  # Stagger delay
            mock_sleep.assert_any_call(0.1)  # API rate limit delay


if __name__ == "__main__":
    pytest.main([__file__, "-v"])