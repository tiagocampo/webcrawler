import logging
import os
from datetime import datetime
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None

def get_logger(name: str) -> logging.Logger:
    """Configure and return a logger instance"""
    global _logger
    
    if _logger is not None:
        return _logger.getChild(name)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create a unique log file name with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f'scraper_{timestamp}.log')
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Create formatter
    formatter = logging.Formatter(log_format, date_format)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Create root logger
    _logger = logging.getLogger('company_scraper')
    _logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    _logger.handlers = []
    
    # Add handlers
    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)
    
    # Create and return child logger
    logger = _logger.getChild(name)
    logger.debug(f"Logger initialized: {name}")
    
    return logger

def get_log_file_path() -> str:
    """Get the current log file path"""
    logs_dir = os.path.join(os.getcwd(), 'logs')
    if not os.path.exists(logs_dir):
        return ""
    
    # Get the most recent log file
    log_files = [f for f in os.listdir(logs_dir) if f.startswith('scraper_')]
    if not log_files:
        return ""
    
    latest_log = max(log_files)
    return os.path.join(logs_dir, latest_log) 