"""
Configuration management for Quantasaurus-Rex.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    """Configuration class using Pydantic for validation and environment variable loading."""
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_s3_bucket: str = Field(default="quantasaurus-rex-data", env="AWS_S3_BUCKET")
    
    # Robinhood Configuration
    robinhood_username: str = Field(env="ROBINHOOD_USERNAME")
    robinhood_password: str = Field(env="ROBINHOOD_PASSWORD")
    robinhood_mfa_code: Optional[str] = Field(default=None, env="ROBINHOOD_MFA_CODE")
    robinhood_device_approval_delay: int = Field(default=30, env="ROBINHOOD_DEVICE_APPROVAL_DELAY")
    robinhood_max_auth_retries: int = Field(default=3, env="ROBINHOOD_MAX_AUTH_RETRIES")
    robinhood_device_storage_path: Optional[str] = Field(default=None, env="ROBINHOOD_DEVICE_STORAGE_PATH")
    
    # API Keys
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    tavily_api_key: str = Field(env="TAVILY_API_KEY")
    
    # Aiera Configuration
    aiera_api_key: str = Field(env="AIERA_API_KEY")
    aiera_api_url: str = Field(default="http://localhost:8000/api", env="AIERA_API_URL")
    aiera_api_timeout: int = Field(default=30, env="AIERA_API_TIMEOUT")
    
    # Email Configuration
    from_email: str = Field(env="FROM_EMAIL")
    to_email: str = Field(default="jacquelinegarrahan@gmail.com", env="TO_EMAIL")
    ses_region: str = Field(default="us-east-1", env="SES_REGION")
    email_subject_prefix: str = Field(default="[Quantasaurus-Rex]", env="EMAIL_SUBJECT_PREFIX")
    
    # Analysis Configuration
    analysis_lookback_days: int = Field(default=90, env="ANALYSIS_LOOKBACK_DAYS")
    confidence_threshold: int = Field(default=60, env="CONFIDENCE_THRESHOLD")
    max_recommendations: int = Field(default=20, env="MAX_RECOMMENDATIONS")
    enable_crypto_analysis: bool = Field(default=True, env="ENABLE_CRYPTO_ANALYSIS")
    enable_stock_analysis: bool = Field(default=True, env="ENABLE_STOCK_ANALYSIS")
    
    # Risk Management
    max_position_size_percent: float = Field(default=10.0, env="MAX_POSITION_SIZE_PERCENT")
    portfolio_risk_limit: float = Field(default=0.20, env="PORTFOLIO_RISK_LIMIT")
    volatility_threshold: float = Field(default=0.30, env="VOLATILITY_THRESHOLD")
    
    # Logging and Monitoring
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_detailed_logging: bool = Field(default=False, env="ENABLE_DETAILED_LOGGING")
    cloudwatch_log_group: str = Field(default="/aws/lambda/quantasaurus-rex", env="CLOUDWATCH_LOG_GROUP")
    
    # Development Settings
    debug: bool = Field(default=False, env="DEBUG")
    mock_data: bool = Field(default=False, env="MOCK_DATA")
    dry_run: bool = Field(default=False, env="DRY_RUN")
    local_development: bool = Field(default=False, env="LOCAL_DEVELOPMENT")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra environment variables
    }