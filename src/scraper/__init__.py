"""
CV-Library Scraper Core Package
Contains all scraping functionality including authentication, search, and download.
"""

from .cv_library_scraper import CVLibraryScraper
from .auth import AuthenticationManager
from .search import SearchManager  
from .download import DownloadManager
from .utils import ScrapingUtils

__all__ = [
    'CVLibraryScraper',
    'AuthenticationManager', 
    'SearchManager',
    'DownloadManager',
    'ScrapingUtils'
] 