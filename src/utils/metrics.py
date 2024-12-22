"""Metrics collector for tracking scraper performance"""
import time
import threading
from typing import Dict, List, Optional, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from .logger import get_logger

logger = get_logger(__name__)

class MetricsError(Exception):
    """Metrics error"""
    pass

class APIMetricsDict(TypedDict):
    """API metrics dictionary"""
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_time: float
    success_rate: float
    average_duration: float

class MetricsDict(TypedDict):
    """Scrape metrics dictionary"""
    company_name: str
    start_time: str
    end_time: Optional[str]
    duration: float
    urls_visited: List[str]
    total_urls: int
    api_metrics: Dict[str, APIMetricsDict]
    field_confidence: Dict[str, float]
    average_confidence: float

@dataclass
class APIMetrics:
    """API call metrics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_time: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def add_call(self, success: bool, duration: float) -> None:
        """Add a call to metrics"""
        if duration < 0:
            raise MetricsError("duration must be non-negative")
            
        with self._lock:
            self.total_calls += 1
            if success:
                self.successful_calls += 1
            else:
                self.failed_calls += 1
            self.total_time += duration
        
    def to_dict(self) -> APIMetricsDict:
        """Convert to dictionary"""
        with self._lock:
            return {
                "total_calls": self.total_calls,
                "successful_calls": self.successful_calls,
                "failed_calls": self.failed_calls,
                "total_time": self.total_time,
                "success_rate": (
                    self.successful_calls / self.total_calls 
                    if self.total_calls > 0 else 0.0
                ),
                "average_duration": (
                    self.total_time / self.total_calls 
                    if self.total_calls > 0 else 0.0
                )
            }

@dataclass
class ScrapeMetrics:
    """Scraping session metrics"""
    company_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    urls_visited: List[str] = field(default_factory=list)
    api_metrics: Dict[str, APIMetrics] = field(default_factory=lambda: {
        "anthropic": APIMetrics(),
        "google_search": APIMetrics(),
        "web_scrape": APIMetrics()
    })
    field_confidence: Dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def add_url(self, url: str) -> None:
        """Add visited URL"""
        if not url:
            raise MetricsError("url cannot be empty")
            
        with self._lock:
            if url not in self.urls_visited:
                self.urls_visited.append(url)
            
    def update_confidence(self, field: str, confidence: float) -> None:
        """Update field confidence"""
        if not 0 <= confidence <= 1:
            raise MetricsError("confidence must be between 0 and 1")
            
        with self._lock:
            self.field_confidence[field] = max(
                confidence,
                self.field_confidence.get(field, 0.0)
            )
        
    def complete(self) -> None:
        """Complete the session"""
        with self._lock:
            if self.end_time is None:
                self.end_time = time.time()
        
    def to_dict(self) -> MetricsDict:
        """Convert to dictionary"""
        with self._lock:
            return {
                "company_name": self.company_name,
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": (
                    datetime.fromtimestamp(self.end_time).isoformat() 
                    if self.end_time else None
                ),
                "duration": self.end_time - self.start_time if self.end_time else 0.0,
                "urls_visited": self.urls_visited.copy(),
                "total_urls": len(self.urls_visited),
                "api_metrics": {
                    name: metrics.to_dict()
                    for name, metrics in self.api_metrics.items()
                },
                "field_confidence": self.field_confidence.copy(),
                "average_confidence": (
                    sum(self.field_confidence.values()) / len(self.field_confidence)
                    if self.field_confidence else 0.0
                )
            }

class MetricsManager:
    """Metrics manager"""
    
    def __init__(self, metrics_dir: str = "metrics"):
        self.metrics_dir = Path(metrics_dir)
        self._lock = threading.Lock()
        try:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise MetricsError(f"Failed to create metrics directory: {e}")
        
    def create_session(self, company_name: str) -> ScrapeMetrics:
        """Create new session"""
        if not company_name:
            raise MetricsError("company_name cannot be empty")
        return ScrapeMetrics(company_name=company_name)
        
    def save_metrics(self, metrics: ScrapeMetrics) -> None:
        """Save metrics to file"""
        if not metrics.end_time:
            metrics.complete()
            
        with self._lock:
            filename = (
                self.metrics_dir / 
                f"{metrics.company_name}_{int(metrics.start_time)}.json"
            )
            
            try:
                with open(filename, 'w') as f:
                    json.dump(metrics.to_dict(), f, indent=2)
            except OSError as e:
                raise MetricsError(f"Failed to save metrics: {e}")
                
            logger.info(f"Saved metrics to {filename}")
        
    def load_metrics(self, filename: str) -> MetricsDict:
        """Load metrics from file"""
        with self._lock:
            filepath = self.metrics_dir / filename
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                raise MetricsError(f"Failed to load metrics: {e}")
            
    def get_all_metrics(self) -> List[MetricsDict]:
        """Get all metrics"""
        with self._lock:
            try:
                metrics = []
                for filepath in self.metrics_dir.glob("*.json"):
                    try:
                        metrics.append(self.load_metrics(filepath.name))
                    except MetricsError as e:
                        logger.warning(f"Failed to load metrics from {filepath}: {e}")
                return metrics
            except OSError as e:
                raise MetricsError(f"Failed to list metrics files: {e}")

# Global instance
metrics_manager = MetricsManager() 