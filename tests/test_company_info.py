import pytest
from src.models.company_info import CompanyInfo

def test_company_info_creation():
    """Test creating a CompanyInfo instance"""
    company = CompanyInfo(
        company_name="Test Company",
        company_location="Test Location",
        products_or_services="Test Products",
        company_overview="Test Overview",
        target_clients="Test Clients"
    )
    
    assert company.company_name == "Test Company"
    assert company.company_location == "Test Location"
    assert company.products_or_services == "Test Products"
    assert company.company_overview == "Test Overview"
    assert company.target_clients == "Test Clients"
    assert isinstance(company.sources, list)
    assert isinstance(company.confidence_scores, dict)

def test_calculate_average_confidence():
    """Test calculating average confidence score"""
    company = CompanyInfo(
        company_name="Test Company",
        confidence_scores={
            "company_name": 0.8,
            "company_location": 0.6,
            "products_or_services": 0.9
        }
    )
    
    avg_confidence = company.calculate_average_confidence()
    assert avg_confidence == pytest.approx(0.7666, rel=1e-3)

def test_is_complete():
    """Test checking if all fields are complete"""
    # Complete company info
    complete = CompanyInfo(
        company_name="Test Company",
        company_location="Test Location",
        products_or_services="Test Products",
        company_overview="Test Overview",
        target_clients="Test Clients"
    )
    assert complete.is_complete() is True
    
    # Incomplete company info
    incomplete = CompanyInfo(
        company_name="Test Company",
        company_location="Test Location"
    )
    assert incomplete.is_complete() is False

def test_empty_confidence_scores():
    """Test handling empty confidence scores"""
    company = CompanyInfo(company_name="Test Company")
    assert company.calculate_average_confidence() == 0.0 