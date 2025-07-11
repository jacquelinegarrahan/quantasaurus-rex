"""Test Lambda handler functionality."""

import pytest
import os
from unittest.mock import Mock, patch
from src.lambda_handler import QuantasaurusLambdaHandler


@pytest.mark.asyncio
async def test_lambda_handler_initialization():
    """Test that the Lambda handler initializes correctly."""
    handler = QuantasaurusLambdaHandler()
    
    # Check that handler has basic attributes
    assert hasattr(handler, 'settings')
    assert hasattr(handler, 'execution_id')
    assert handler.execution_id is not None


@pytest.mark.asyncio
async def test_lambda_handler_environment_loaded():
    """Test that the Lambda handler can access environment variables."""
    handler = QuantasaurusLambdaHandler()
    
    # Initialize the handler to load settings
    await handler.initialize()
    
    # Check that settings can be loaded (environment variables are available)
    assert handler.settings is not None
    assert handler.settings.openai_api_key is not None
    assert handler.settings.environment is not None
    
    # Clean up
    await handler._cleanup()


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    handler = QuantasaurusLambdaHandler()
    
    # Initialize the handler
    await handler.initialize()
    
    # Run health check
    result = await handler.health_check()
    
    # Check result structure
    assert "statusCode" in result
    assert result["statusCode"] == 200
    assert "body" in result
    assert "status" in result["body"]
    assert result["body"]["status"] == "healthy"
    assert "services" in result["body"]
    
    # Clean up
    await handler._cleanup()


def test_lambda_event_handler():
    """Test the main Lambda event handler function."""
    from src.lambda_handler import lambda_handler
    
    # Create a mock event
    event = {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {}
    }
    
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    
    # Test that the handler can be called (may fail due to missing services but shouldn't crash)
    try:
        result = lambda_handler(event, context)
        # If it succeeds, check the structure
        assert "statusCode" in result
        assert "body" in result
    except Exception as e:
        # Expected to fail in test environment, but should be a specific error
        assert "Error in Lambda handler" in str(e) or "initialization" in str(e).lower()