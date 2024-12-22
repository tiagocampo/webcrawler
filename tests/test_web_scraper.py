import pytest
import aiohttp
import asyncio
from unittest.mock import Mock, patch
from src.scraper.web_scraper import WebScraper
from src.models.company_info import CompanyInfo

@pytest.fixture
def web_scraper():
    """Create a WebScraper instance for testing"""
    return WebScraper("dummy_api_key")

@pytest.fixture
def sample_html():
    """Sample HTML content for testing"""
    return """
    <html>
        <head><title>Test Company</title></head>
        <body>
            <h1>Test Company</h1>
            <p>We are located in Test City</p>
            <div class="products">
                <h2>Our Products</h2>
                <p>We offer amazing products and services</p>
            </div>
            <div class="about">
                <h2>About Us</h2>
                <p>A great company serving customers since 2000</p>
            </div>
            <div class="clients">
                <h2>Our Clients</h2>
                <p>We serve enterprise businesses</p>
            </div>
        </body>
    </html>
    """

@pytest.mark.asyncio
async def test_scrape_website(web_scraper, sample_html):
    """Test website scraping"""
    # Mock aiohttp.ClientSession
    mock_response = Mock()
    mock_response.text = asyncio.coroutine(lambda: sample_html)
    
    mock_session = Mock()
    mock_session.__aenter__ = asyncio.coroutine(lambda *args: mock_session)
    mock_session.__aexit__ = asyncio.coroutine(lambda *args: None)
    mock_session.get = asyncio.coroutine(lambda *args, **kwargs: mock_response)
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        result = await web_scraper.scrape_website("http://test.com")
        assert result == sample_html

def test_clean_html(web_scraper, sample_html):
    """Test HTML cleaning"""
    cleaned = web_scraper.clean_html(sample_html)
    assert "Test Company" in cleaned
    assert "script" not in cleaned
    assert "style" not in cleaned

@pytest.mark.asyncio
async def test_extract_company_info(web_scraper, sample_html):
    """Test company information extraction"""
    # Mock LLM response
    mock_llm_response = Mock()
    mock_llm_response.content = """
    {
        "company_name": "Test Company",
        "company_location": "Test City",
        "products_or_services": "Amazing products and services",
        "company_overview": "A great company serving customers since 2000",
        "target_clients": "Enterprise businesses"
    }
    """
    
    with patch.object(web_scraper.llm, 'ainvoke', 
                     return_value=asyncio.Future()) as mock_invoke:
        mock_invoke.return_value.set_result(mock_llm_response)
        
        result = await web_scraper.extract_company_info(
            sample_html,
            "http://test.com"
        )
        
        assert isinstance(result, dict)
        assert "company_name" in result
        assert "confidence_scores" in result
        assert "sources" in result
        assert "http://test.com" in result["sources"]

@pytest.mark.asyncio
async def test_process_website(web_scraper):
    """Test complete website processing"""
    # Mock dependencies
    mock_html = "<html><body>Test content</body></html>"
    mock_info = {
        "company_name": "Test Company",
        "company_location": "Test Location",
        "confidence_scores": {"company_name": 0.9}
    }
    
    # Patch necessary methods
    with patch.object(web_scraper, 'scrape_website',
                     return_value=asyncio.Future()) as mock_scrape:
        mock_scrape.return_value.set_result(mock_html)
        
        with patch.object(web_scraper, 'extract_company_info',
                         return_value=asyncio.Future()) as mock_extract:
            mock_extract.return_value.set_result(mock_info)
            
            async for event in web_scraper.process_website(
                "Test Company",
                "http://test.com"
            ):
                assert isinstance(event, dict)
                assert "company_info" in event
                assert isinstance(event["company_info"], CompanyInfo)
                assert event["company_info"].company_name == "Test Company" 