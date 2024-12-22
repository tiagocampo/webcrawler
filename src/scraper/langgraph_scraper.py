"""Website and Google search scraper using LangGraph"""
# Standard library imports
import json
import os
from typing import Dict, List, Optional, TypedDict, Literal, TypeVar, Annotated, Union
from urllib.parse import urljoin

# Third-party imports
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from googlesearch import search as google_search
import requests

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

# Load environment variables
load_dotenv()

# Define state types
State = TypeVar("State", bound=Dict)

class CompanyInfo(TypedDict):
    """Company information schema"""
    company_name: str
    company_location: str
    products_or_services: List[str]
    company_overview: str
    target_clients: List[str]
    sources: List[str]
    confidence_scores: Dict[str, float]

class ScraperState(TypedDict):
    """Scraper state"""
    company_name: str
    website_url: str
    company_info: CompanyInfo
    current_url: str
    visited_urls: List[str]
    content: Dict[str, str]
    navigation_tries: int
    search_tries: int
    mode: Literal["website", "google"]
    error: Optional[str]

def create_initial_state(company_name: str, website_url: str) -> ScraperState:
    """Create initial state"""
    return {
        "company_name": company_name,
        "website_url": website_url,
        "company_info": {
            "company_name": company_name,
            "company_location": "",
            "products_or_services": [],
            "company_overview": "",
            "target_clients": [],
            "sources": [],
            "confidence_scores": {}
        },
        "current_url": website_url,
        "visited_urls": [],
        "content": {},
        "navigation_tries": 0,
        "search_tries": 0,
        "mode": "website",
        "error": None
    }

def extract_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract relevant navigation links"""
    relevant_keywords = [
        "about", "company", "products", "services", "clients",
        "customers", "contact", "locations", "overview"
    ]
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").lower()
        text = a.get_text().lower()
        if any(keyword in href or keyword in text for keyword in relevant_keywords):
            full_url = urljoin(base_url, href)
            if base_url in full_url:  # Only include internal links
                links.append(full_url)
    return links

def scrape_website(state: Annotated[State, "state"]) -> Dict:
    """Scrape website content"""
    if state["navigation_tries"] >= 5:
        state["mode"] = "google"
        return state

    try:
        response = requests.get(
            state["current_url"],
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}  # Add user agent to avoid 403
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        content = " ".join(p.get_text() for p in soup.find_all(["p", "h1", "h2", "h3", "li"]))
        
        if not content.strip():  # Check if content is empty
            raise ValueError("No content found on page")
        
        state["content"][state["current_url"]] = content
        state["visited_urls"].append(state["current_url"])
        
        # Get next URL to visit
        links = extract_links(soup, state["website_url"])
        unvisited_links = [url for url in links if url not in state["visited_urls"]]
        
        if unvisited_links:
            state["current_url"] = unvisited_links[0]
        
        state["navigation_tries"] += 1
        
    except Exception as e:
        state["mode"] = "google"  # Always switch to Google on any error
    
    return state

def search_google(state: Annotated[State, "state"]) -> Dict:
    """Search and scrape Google results"""
    if state["search_tries"] >= 5:
        return state

    try:
        # Generate search query based on missing information
        missing_fields = []
        for field, value in state["company_info"].items():
            if field not in ["sources", "confidence_scores"] and not value:
                missing_fields.append(field)
        
        if not missing_fields:  # If no missing fields, search for general info
            query = f"{state['company_name']} company information overview"
        else:
            query = f"{state['company_name']} {' '.join(missing_fields)}"
        
        results = list(google_search(query, num_results=3))
        
        for url in results:
            if url not in state["visited_urls"]:
                try:
                    response = requests.get(
                        url,
                        timeout=10,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, "html.parser")
                    content = " ".join(p.get_text() for p in soup.find_all(["p", "h1", "h2", "h3", "li"]))
                    
                    if content.strip():  # Only add if content is not empty
                        state["content"][url] = content
                        state["visited_urls"].append(url)
                except:
                    continue
        
        state["search_tries"] += 1
        
    except Exception as e:
        pass  # Continue even if search fails
    
    return state

def extract_info(state: Annotated[State, "state"]) -> Dict:
    """Extract company information"""
    if not state["content"]:
        return state

    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            
        llm = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            anthropic_api_key=api_key
        )
        
        system_prompt = """You are a company information extractor.
        Your task is to analyze text and extract specific company information.
        Only include information that is explicitly mentioned in the text.
        For each field, provide a confidence score between 0 and 1 based on how certain you are about the information.
        
        The response should be a valid JSON object with two main sections:
        1. Company information fields
        2. Confidence scores for each field
        
        Example format:
        {
            "company_name": "Example Corp",
            "company_location": "New York, USA",
            "products_or_services": ["Product A", "Service B"],
            "company_overview": "A brief description...",
            "target_clients": ["Client Type 1", "Client Type 2"],
            "confidence_scores": {
                "company_name": 0.9,
                "company_location": 0.8,
                "products_or_services": 0.7,
                "company_overview": 0.8,
                "target_clients": 0.6
            }
        }
        """
        
        human_prompt = f"""Extract company information from the following text. 
        Format the response as a JSON object with these fields:
        - company_name: Company name
        - company_location: Company location/headquarters
        - products_or_services: List of products or services
        - company_overview: Brief company overview/description
        - target_clients: List of target clients or customer types

        Also include a "confidence_scores" object with confidence scores between 0 and 1 for each field.

        Text sources:
        {json.dumps(state['content'])}

        Only include information that is explicitly mentioned in the text.
        Format numbers consistently and use empty strings or empty lists for missing values.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        response = llm.invoke(messages)
        extracted_info = json.loads(response.content)
        
        # Update non-empty fields with confidence scores
        for field in ["company_name", "company_location", "products_or_services", 
                     "company_overview", "target_clients"]:
            if field in extracted_info and extracted_info[field]:
                state["company_info"][field] = extracted_info[field]
                if "confidence_scores" in extracted_info:
                    state["company_info"]["confidence_scores"][field] = extracted_info["confidence_scores"][field]
        
        # Add sources
        state["company_info"]["sources"].extend(
            [url for url in state["content"].keys() if url not in state["company_info"]["sources"]]
        )
        
    except Exception as e:
        state["error"] = f"Information extraction failed: {str(e)}"
    return state

def router(state: Annotated[State, "state"]) -> Union[Literal["scrape_website", "search_google", "extract_info"], END]:
    """Route to next node"""
    # First, check if we have all required information with good confidence
    has_all_info = True
    for field in ["company_location", "products_or_services", "company_overview", "target_clients"]:
        confidence = state["company_info"]["confidence_scores"].get(field, 0.0)
        if not state["company_info"][field] or confidence < 0.7:
            has_all_info = False
            break
    
    if has_all_info:
        return END
    
    # If in website mode and under max tries, continue scraping
    if state["mode"] == "website" and state["navigation_tries"] < 5:
        return "scrape_website"
    
    # If in Google mode and under max tries, continue searching
    if state["mode"] == "google" and state["search_tries"] < 5:
        return "search_google"
    
    # If we have content, try to extract information
    if state["content"]:
        return "extract_info"
    
    # If we've exhausted all options, end
    return END

def scrape_router(state: Annotated[State, "state"]) -> Union[Literal["extract_info"], END]:
    """Route after scraping"""
    if state["content"]:
        return "extract_info"
    return END

def search_router(state: Annotated[State, "state"]) -> Union[Literal["extract_info"], END]:
    """Route after searching"""
    if state["content"]:
        return "extract_info"
    return END

def extract_router(state: Annotated[State, "state"]) -> Union[Literal["scrape_website", "search_google"], END]:
    """Route after extraction"""
    # Check if we have all required information with good confidence
    has_all_info = True
    for field in ["company_location", "products_or_services", "company_overview", "target_clients"]:
        confidence = state["company_info"]["confidence_scores"].get(field, 0.0)
        if not state["company_info"][field] or confidence < 0.7:
            has_all_info = False
            break
    
    if has_all_info:
        return END
        
    # If in website mode and under max tries, continue scraping
    if state["mode"] == "website" and state["navigation_tries"] < 5:
        return "scrape_website"
    
    # If in Google mode and under max tries, continue searching
    if state["mode"] == "google" and state["search_tries"] < 5:
        return "search_google"
    
    return END

class LangGraphScraper:
    """Website and Google search scraper"""
    
    def __init__(self):
        # Create graph with state schema
        workflow = StateGraph(state_schema=ScraperState)
        
        # Add nodes
        workflow.add_node("scrape_website", scrape_website)
        workflow.add_node("search_google", search_google)
        workflow.add_node("extract_info", extract_info)
        
        # Add edges with specific routers
        workflow.add_conditional_edges(
            "scrape_website",
            scrape_router,
            {
                "extract_info": "extract_info",
                END: END
            }
        )
        workflow.add_conditional_edges(
            "search_google",
            search_router,
            {
                "extract_info": "extract_info",
                END: END
            }
        )
        workflow.add_conditional_edges(
            "extract_info",
            extract_router,
            {
                "scrape_website": "scrape_website",
                "search_google": "search_google",
                END: END
            }
        )
        
        # Set entry point
        workflow.set_entry_point("scrape_website")
        
        # Compile graph
        self.graph = workflow.compile()

    def scrape(self, company_name: str, website_url: str) -> CompanyInfo:
        """Scrape company information"""
        state = create_initial_state(company_name, website_url)
        final_state = self.graph.invoke(state)
        
        if not isinstance(final_state, dict):
            raise Exception("Invalid graph output")
            
        if final_state["error"] is not None:
            raise Exception(final_state["error"])
            
        return final_state["company_info"]