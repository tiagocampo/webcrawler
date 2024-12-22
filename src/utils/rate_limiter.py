"""Rate limiter for API calls"""
import time
import threading
from typing import Dict, Callable, TypeVar, ParamSpec
from functools import wraps
from dataclasses import dataclass, field
from .logger import get_logger

logger = get_logger(__name__)

class RateLimitError(Exception):
    """Rate limit error"""
    pass

@dataclass
class RateLimit:
    """Rate limit configuration"""
    calls_per_minute: int
    max_retries: int = 3
    _call_count: int = field(default=0)
    _window_start: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def __post_init__(self) -> None:
        """Validate configuration"""
        if self.calls_per_minute <= 0:
            raise RateLimitError("calls_per_minute must be positive")
        if self.max_retries < 0:
            raise RateLimitError("max_retries must be non-negative")
            
    def _reset_if_needed(self) -> None:
        """Reset window if a minute has passed"""
        with self._lock:
            if time.time() - self._window_start >= 60:
                self._call_count = 0
                self._window_start = time.time()
        
    def can_proceed(self) -> bool:
        """Check if call can proceed"""
        self._reset_if_needed()
        with self._lock:
            return self._call_count < self.calls_per_minute
        
    def wait_time(self) -> float:
        """Calculate wait time in seconds"""
        self._reset_if_needed()
        with self._lock:
            return max(0.0, 60 - (time.time() - self._window_start))
            
    def record_call(self) -> None:
        """Record a successful call"""
        with self._lock:
            self._call_count += 1

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self):
        self._limits: Dict[str, RateLimit] = {
            "anthropic": RateLimit(calls_per_minute=50),
            "google_search": RateLimit(calls_per_minute=60),
            "web_scrape": RateLimit(calls_per_minute=30)
        }
        
    def wait_if_needed(self, api_name: str) -> None:
        """Wait if rate limit requires"""
        if api_name not in self._limits:
            raise RateLimitError(f"No rate limit for: {api_name}")
            
        limit = self._limits[api_name]
        retries = 0
        
        while not limit.can_proceed():
            if retries >= limit.max_retries:
                raise RateLimitError(
                    f"Rate limit exceeded for {api_name} after {retries} retries"
                )
                
            wait_time = limit.wait_time()
            logger.warning(
                f"Rate limit reached for {api_name}. "
                f"Waiting {wait_time:.2f}s. "
                f"Retry {retries + 1}/{limit.max_retries}"
            )
            time.sleep(wait_time)
            retries += 1
            
        limit.record_call()

P = ParamSpec("P")
T = TypeVar("T")

def rate_limited(api_name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Rate limiting decorator"""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            rate_limiter.wait_if_needed(api_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Global instance
rate_limiter = RateLimiter() 