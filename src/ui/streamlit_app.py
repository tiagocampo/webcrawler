"""Streamlit UI for company scraper"""
# Third-party imports
import streamlit as st

# Local imports
from ..scraper.langgraph_scraper import LangGraphScraper, CompanyInfo

class StreamlitUI:
    def __init__(self):
        self.setup_page()
        self.scraper = LangGraphScraper()
    
    def setup_page(self):
        """Setup page configuration"""
        st.set_page_config(
            page_title="Company Scraper",
            page_icon="🔍",
            layout="wide"
        )
    
    def display_company_info(self, company_info: CompanyInfo):
        """Display company information"""
        st.title(company_info["company_name"])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if company_info["company_overview"]:
                st.subheader("📝 Company Overview")
                st.write(company_info["company_overview"])
                self.display_confidence("company_overview", company_info)
            
            if company_info["products_or_services"]:
                st.subheader("🛍️ Products & Services")
                for product in company_info["products_or_services"]:
                    st.markdown(f"- {product}")
                self.display_confidence("products_or_services", company_info)
            
            if company_info["target_clients"]:
                st.subheader("👥 Target Clients")
                for client in company_info["target_clients"]:
                    st.markdown(f"- {client}")
                self.display_confidence("target_clients", company_info)
        
        with col2:
            if company_info["company_location"]:
                st.subheader("🌍 Location")
                st.write(company_info["company_location"])
                self.display_confidence("company_location", company_info)
            
            if company_info["sources"]:
                st.subheader("📚 Sources")
                for source in company_info["sources"]:
                    domain = source.split("/")[2]
                    st.markdown(f"- [{domain}]({source})")
    
    def display_confidence(self, field: str, company_info: CompanyInfo):
        """Display confidence score"""
        confidence = company_info["confidence_scores"].get(field, 0.0)
        color = (
            "#00C853" if confidence >= 0.8
            else "#FFB300" if confidence >= 0.6
            else "#E53935"
        )
        st.caption(
            f"Confidence: :green[{confidence:.0%}]" if confidence >= 0.8
            else f"Confidence: :orange[{confidence:.0%}]" if confidence >= 0.6
            else f"Confidence: :red[{confidence:.0%}]"
        )
    
    def run(self):
        """Run the application"""
        st.title("🔍 Company Information Scraper")
        
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input(
                "Company Name",
                placeholder="e.g., Acme Corp"
            )
        with col2:
            website_url = st.text_input(
                "Company Website",
                placeholder="e.g., https://www.acme.com"
            )
        
        if st.button("🚀 Search", use_container_width=True):
            if not company_name or not website_url:
                st.error("Please enter both company name and website URL")
                return
            
            with st.spinner("Searching company information..."):
                try:
                    company_info = self.scraper.scrape(company_name, website_url)
                    self.display_company_info(company_info)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        st.markdown("---")
        st.caption(
            "Built with Streamlit, LangChain, and Claude 🤖 | "
            "Will try website first, then fall back to Google search"
        )