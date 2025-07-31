"""
Data models for CV-Library Scraper
"""

from .cv_data import CVData, CandidateInfo
from .search_result import SearchResult, SearchResultCollection

__all__ = ['CVData', 'CandidateInfo', 'SearchResult', 'SearchResultCollection'] 