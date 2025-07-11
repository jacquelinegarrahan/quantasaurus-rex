"""Test environment variable loading."""

import os
import pytest


def test_env_variables_loaded():
    """Test that environment variables are loaded from .env file."""
    # These should be loaded from the .env file or test fixtures
    assert os.getenv("OPENAI_API_KEY") is not None
    assert os.getenv("ENVIRONMENT") is not None  # Could be "test" or "development"
    assert os.getenv("EMAIL_SENDER") is not None


def test_robinhood_config_loaded():
    """Test that Robinhood configuration is loaded."""
    assert os.getenv("ROBINHOOD__USERNAME") is not None
    assert os.getenv("ROBINHOOD__PASSWORD") is not None


def test_api_keys_loaded():
    """Test that API keys are loaded from .env file."""
    assert os.getenv("TAVILY_API_KEY") is not None
    assert os.getenv("AIERA_API_KEY") is not None
    assert os.getenv("OPENAI_API_KEY") is not None