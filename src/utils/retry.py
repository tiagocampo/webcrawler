"""Retry decorator for handling transient errors"""
import time
import random
from typing import TypeVar, Callable, ParamSpec, Type, Union, Tuple, Optional
from functools import wraps
from .logger import get_logger

logger = get_logger(__name__)

class RetryError(Exception):
    """Base class for retry errors"""
    pass

class MaxRetriesExceededError(RetryError):
    """Error raised when max retries is exceeded"""
    pass

class RetryConfigError(RetryError):
    """Error raised when retry configuration is invalid"""
    pass

P = ParamSpec("P")
T = TypeVar("T")

def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[
        Type[Exception],
        Tuple[Type[Exception], ...],
        None
    ] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for retrying functions that may fail transiently
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        exceptions: Exception types to catch and retry on
        
    Returns:
        Decorated function
        
    Raises:
        RetryConfigError: If retry configuration is invalid
        MaxRetriesExceededError: If max retries is exceeded
        
    Example:
        @retry(max_retries=3, exceptions=(ConnectionError, TimeoutError))
        def unstable_function():
            ...
    """
    # Validate configuration
    if max_retries < 0:
        raise RetryConfigError("max_retries must be non-negative")
    if initial_delay <= 0:
        raise RetryConfigError("initial_delay must be positive")
    if max_delay < initial_delay:
        raise RetryConfigError("max_delay must be greater than or equal to initial_delay")
    if exponential_base <= 1:
        raise RetryConfigError("exponential_base must be greater than 1")
        
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if exceptions and not isinstance(e, exceptions):
                        raise
                        
                    last_exception = e
                    
                    if attempt == max_retries:
                        raise MaxRetriesExceededError(
                            f"Function {func.__name__} failed after {max_retries} retries"
                        ) from e
                        
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    if jitter:
                        delay *= (0.5 + random.random())
                        
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} "
                        f"for {func.__name__} failed: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
                    
            # This should never happen due to the raise in the loop
            assert last_exception is not None
            raise last_exception
            
        return wrapper
    return decorator