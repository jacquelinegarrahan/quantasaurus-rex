"""Retry utilities with exponential backoff for API calls."""

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar, Optional, Type, Tuple, Any
import openai
from openai import RateLimitError, APIConnectionError, APITimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_multiplier: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_multiplier = backoff_multiplier


def calculate_backoff_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for exponential backoff with jitter."""
    if attempt == 0:
        return 0
    
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    
    # Apply backoff multiplier
    delay *= config.backoff_multiplier
    
    # Cap at max delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to avoid thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def should_retry(exception: Exception, attempt: int, max_retries: int) -> bool:
    """Determine if an exception should trigger a retry."""
    if attempt >= max_retries:
        return False
    
    # Retry on rate limit errors
    if isinstance(exception, RateLimitError):
        return True
    
    # Retry on connection errors
    if isinstance(exception, APIConnectionError):
        return True
    
    # Retry on timeout errors
    if isinstance(exception, APITimeoutError):
        return True
    
    # Retry on 5xx server errors
    if hasattr(exception, 'status_code') and exception.status_code >= 500:
        return True
    
    return False


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (RateLimitError, APIConnectionError, APITimeoutError)
) -> Callable:
    """Decorator for retrying functions with exponential backoff."""
    
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if not should_retry(e, attempt, config.max_retries):
                        logger.error(f"Max retries ({config.max_retries}) exceeded for {func.__name__}")
                        raise e
                    
                    delay = calculate_backoff_delay(attempt + 1, config)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    if delay > 0:
                        await asyncio.sleep(delay)
                except Exception as e:
                    # Don't retry on other exceptions
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise e
            
            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            
            raise Exception(f"All retries failed for {func.__name__}")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if not should_retry(e, attempt, config.max_retries):
                        logger.error(f"Max retries ({config.max_retries}) exceeded for {func.__name__}")
                        raise e
                    
                    delay = calculate_backoff_delay(attempt + 1, config)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    if delay > 0:
                        import time
                        time.sleep(delay)
                except Exception as e:
                    # Don't retry on other exceptions
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise e
            
            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            
            raise Exception(f"All retries failed for {func.__name__}")
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def openai_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Callable:
    """Specialized retry decorator for OpenAI API calls."""
    
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        backoff_multiplier=1.5  # Gentler backoff for API calls
    )
    
    # Include OpenAI-specific exceptions
    exceptions = (
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        openai.APIError
    )
    
    return retry_with_backoff(config, exceptions)


async def test_retry_mechanism():
    """Test the retry mechanism with a mock function."""
    
    @openai_retry(max_retries=3, base_delay=0.1, max_delay=2.0)
    async def mock_api_call(fail_count: int = 2):
        """Mock API call that fails fail_count times."""
        if not hasattr(mock_api_call, 'attempts'):
            mock_api_call.attempts = 0
        
        mock_api_call.attempts += 1
        
        if mock_api_call.attempts <= fail_count:
            raise RateLimitError(
                message="Rate limit exceeded", 
                response=None, 
                body=None
            )
        
        return f"Success after {mock_api_call.attempts} attempts"
    
    try:
        result = await mock_api_call(fail_count=2)
        logger.info(f"Test result: {result}")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test the retry mechanism
    import asyncio
    
    async def main():
        result = await test_retry_mechanism()
        print(f"Retry test {'passed' if result else 'failed'}")
    
    asyncio.run(main())