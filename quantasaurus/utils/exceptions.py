"""
Custom exceptions for Quantasaurus-Rex.
"""

class QuantasaurusError(Exception):
    """Base exception for Quantasaurus-Rex application."""
    
    def __init__(self, message: str, code: str = "UNKNOWN"):
        super().__init__(message)
        self.code = code


class DataCollectionError(QuantasaurusError):
    """Error occurred during data collection."""
    pass


class AnalysisError(QuantasaurusError):
    """Error occurred during AI analysis."""
    pass


class EmailGenerationError(QuantasaurusError):
    """Error occurred during email generation or delivery."""
    pass


class ConfigurationError(QuantasaurusError):
    """Error in configuration or environment setup."""
    pass