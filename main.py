"""Main entry point for the application"""
# Local imports
from src.ui.streamlit_app import StreamlitUI

def main():
    """Run the application"""
    ui = StreamlitUI()
    ui.run()

if __name__ == "__main__":
    main() 