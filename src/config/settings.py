"""Configuration settings using Pydantic."""

from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RobinhoodConfig(BaseModel):
    """Robinhood API configuration."""
    
    username: str = Field(..., description="Robinhood username")
    password: str = Field(..., description="Robinhood password")
    device_id: Optional[str] = Field(None, description="Device ID for authentication")
    mfa_code: Optional[str] = Field(None, description="MFA code if required")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Keys
    openai_api_key: str = Field(..., description="OpenAI API key")
    tavily_api_key: str = Field(..., description="Tavily API key")
    aiera_api_key: str = Field(..., description="Aiera API key")
    
    # Robinhood Configuration
    robinhood: RobinhoodConfig = Field(..., description="Robinhood configuration")
    
    # Email Configuration
    email_recipient: str = Field(
        default="jacquelinegarrahan@gmail.com",
        description="Email recipient for reports"
    )
    email_sender: str = Field(..., description="Verified SES email sender")
    
    # Model Configuration
    openai_model: str = Field(
        default="gpt-4.1-2025-04-14",
        description="OpenAI model to use"
    )
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_account_id: Optional[str] = Field(None, description="AWS account ID")
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Analysis Configuration
    max_historical_days: int = Field(
        default=365,
        description="Maximum days of historical data to fetch"
    )
    
    confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence threshold for recommendations"
    )
    
    # Email Configuration
    email_template_path: str = Field(
        default="assets/email_templates/report.html",
        description="Path to email template"
    )
    
    # Parallel Processing Configuration
    enable_parallel_processing: bool = Field(
        default=True,
        description="Enable parallel processing for asset analysis"
    )
    
    max_concurrent_analyses: int = Field(
        default=10,
        description="Maximum number of concurrent asset analyses"
    )
    
    api_rate_limit_delay: float = Field(
        default=1.0,
        description="Base delay between API calls in seconds"
    )
    
    batch_delay: float = Field(
        default=2.0,
        description="Delay between processing batches in seconds"
    )
    
    stagger_delay: float = Field(
        default=0.1,
        description="Delay between starting individual tasks in seconds"
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"