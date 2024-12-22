from typing import Dict, List, TypedDict, Literal
from .company_info import CompanyInfo

class ScrapeState(TypedDict):
    """State for the scraping process"""
    company_info: CompanyInfo
    company_name: str
    current_url: str
    visited_urls: List[str]
    navigation_attempts: int
    google_search_attempts: int
    mode: Literal["navigation", "google_search"]
    last_update: float  # timestamp of last state update