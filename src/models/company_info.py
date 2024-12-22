from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    """Evidence for extracted information"""
    text: str = Field(..., description="The exact text evidence")
    source: str = Field(..., description="The source URL of the evidence")

class CompanyInfo(BaseModel):
    """Schema for company information"""
    company_name: Optional[str] = Field(None, description="The name of the company")
    company_location: Optional[str] = Field(None, description="The location of the company")
    products_or_services: Optional[str] = Field(None, description="The products or services offered by the company") 
    company_overview: Optional[str] = Field(None, description="An overview of the company")
    target_clients: Optional[str] = Field(None, description="The target clients of the company")
    sources: List[str] = Field(default_factory=list, description="List of source URLs")
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for each field (0-1)"
    )
    evidence: Dict[str, Evidence] = Field(
        default_factory=dict,
        description="Evidence for each extracted field"
    )
    
    def calculate_average_confidence(self) -> float:
        """Calculate the average confidence score across all fields"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)
    
    def is_complete(self) -> bool:
        """Check if all main fields are filled with high confidence"""
        main_fields = [
            self.company_name,
            self.company_location,
            self.products_or_services,
            self.company_overview,
            self.target_clients
        ]
        
        # Check if all fields are filled
        if not all(field is not None for field in main_fields):
            return False
            
        # Check if all fields have high confidence
        return all(
            self.confidence_scores.get(field, 0.0) >= 0.75
            for field in [
                "company_name",
                "company_location",
                "products_or_services",
                "company_overview",
                "target_clients"
            ]
        )
    
    def get_field_evidence(self, field: str) -> Optional[Evidence]:
        """Get evidence for a specific field"""
        return self.evidence.get(field)
    
    def add_evidence(self, field: str, text: str, source: str):
        """Add evidence for a field"""
        self.evidence[field] = Evidence(text=text, source=source)
    
    def get_missing_fields(self) -> List[str]:
        """Get list of fields that are missing or have low confidence"""
        missing = []
        for field in [
            "company_name",
            "company_location",
            "products_or_services",
            "company_overview",
            "target_clients"
        ]:
            if (
                getattr(self, field) is None or
                self.confidence_scores.get(field, 0.0) < 0.75
            ):
                missing.append(field)
        return missing