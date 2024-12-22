"""Models for web scraping functionality"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class CompanyExtraction(BaseModel):
    """Model for extracted company information"""
    company_name: Optional[str] = Field(None, description="Company name")
    company_location: Optional[str] = Field(None, description="Company headquarters location")
    products_or_services: Optional[str] = Field(None, description="Products or services offered")
    company_overview: Optional[str] = Field(None, description="Company overview/description")
    target_clients: Optional[str] = Field(None, description="Target clients/market")
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for each field (0-1)"
    )

    @validator('confidence_scores')
    def validate_confidence_scores(cls, v):
        """Validate confidence scores are between 0 and 1"""
        for field, score in v.items():
            if not 0 <= score <= 1:
                raise ValueError(f'Confidence score for {field} must be between 0 and 1')
        return v

class LinkInfo(BaseModel):
    """Model for link information"""
    url: str = Field(..., description="URL of the link")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    target_fields: List[str] = Field(..., description="Target fields this link might contain")

    @validator('relevance_score')
    def validate_relevance_score(cls, v):
        """Validate relevance score is between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError('Relevance score must be between 0 and 1')
        return v

    @validator('target_fields')
    def validate_target_fields(cls, v):
        """Validate target fields"""
        valid_fields = {
            'company_location',
            'products_or_services',
            'company_overview',
            'target_clients'
        }
        for field in v:
            if field not in valid_fields:
                raise ValueError(f'Invalid target field: {field}')
        return v

class SearchResult(BaseModel):
    """Model for search results"""
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Snippet/description from search result")

class ScrapeUrlInput(BaseModel):
    """Input model for URL scraping"""
    url: str = Field(..., description="URL to scrape")

class ExtractMenuLinksInput(BaseModel):
    """Input model for menu link extraction"""
    html_content: str = Field(..., description="HTML content to extract links from")
    base_url: str = Field(..., description="Base URL for resolving relative links")

class GoogleSearchInput(BaseModel):
    """Input model for Google search"""
    query: str = Field(..., description="Search query")
    company_name: str = Field(..., description="Company name to search for")
    target_field: str = Field(..., description="Target field to find information about")

    @validator('target_field')
    def validate_target_field(cls, v):
        """Validate target field"""
        valid_fields = {
            'company_location',
            'products_or_services',
            'company_overview',
            'target_clients'
        }
        if v not in valid_fields:
            raise ValueError(f'Invalid target field: {v}')
        return v