"""
Main CV-Library scraper class that coordinates authentication, search, and download operations.
"""

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import math

from ..config.settings import Settings
from ..models.cv_data import CVData
from ..models.search_result import SearchResultCollection
from .auth import AuthenticationManager
from .search import SearchManager
from .download import DownloadManager
from .utils import ScrapingUtils


class CVLibraryScraper:
    """
    Main scraper class that orchestrates the entire CV scraping workflow.
    """
    
    def __init__(self, settings: Settings):
        """Initialize the scraper with configuration."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize managers
        self.auth_manager = AuthenticationManager(settings)
        self.search_manager = None  # Will be initialized after authentication
        self.download_manager = None  # Will be initialized after authentication
        self.utils = ScrapingUtils(settings)
        
        # Session state
        self.session_id = self._generate_session_id()
        self.is_authenticated = False
        self.current_session_data = {}
        
        self.logger.info(f"CV-Library scraper initialized with session ID: {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"
    
    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with CV-Library.
        
        Args:
            username: CV-Library username (optional, will use settings if not provided)
            password: CV-Library password (optional, will use settings if not provided)
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self.logger.info("Starting authentication with CV-Library")
            
            # Use the real authentication manager
            success = self.auth_manager.login(username, password)
            
            if success:
                self.is_authenticated = True
                self.logger.info("Authentication successful")
                
                # Initialize other managers now that we have an authenticated WebDriver
                driver = self.auth_manager.get_driver()
                if driver:
                    self.search_manager = SearchManager(self.settings, driver)
                    self.download_manager = DownloadManager(self.settings)
                
                return True
            else:
                self.is_authenticated = False
                self.logger.error("Authentication failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            self.is_authenticated = False
            return False
    
    def search(self, keywords: List[str], location: Optional[str] = None, 
              salary_min: Optional[str] = None, salary_max: Optional[str] = None,
              # Job and industry filters
              job_type: Optional[List[str]] = None, industry: Optional[List[str]] = None,
              # Location and timing filters
              distance: Optional[int] = None, time_period: Optional[str] = None,
              # Boolean filters
              willing_to_relocate: Optional[bool] = None, uk_driving_licence: Optional[bool] = None,
              hide_recently_viewed: Optional[bool] = None,
              # Advanced filters
              languages: Optional[List[str]] = None, minimum_match: Optional[str] = None,
              sort_order: Optional[str] = None,
              # Advanced keyword filters
              must_have_keywords: Optional[str] = None, any_keywords: Optional[str] = None,
              none_keywords: Optional[str] = None,
              # Original parameters
              max_pages: int = 5, target_results: Optional[int] = None) -> SearchResultCollection:
        """
        Search for CVs matching the specified criteria.
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            salary_min: Minimum salary (optional)
            salary_max: Maximum salary (optional)
            max_pages: Maximum number of pages to crawl
            target_results: Target number of results needed (for automatic pagination)
            
        Returns:
            SearchResultCollection with found CVs
        """
        try:
            if not self.is_authenticated:
                self.logger.error("Not authenticated. Please authenticate first.")
                return SearchResultCollection(results=[])
            
            if not self.search_manager:
                self.logger.error("Search manager not initialized. Authentication may have failed.")
                return SearchResultCollection(results=[])
            
            # Verify session is still valid
            if not self.auth_manager.verify_session():
                self.logger.warning("Session expired, attempting re-authentication")
                if not self.authenticate():
                    self.logger.error("Re-authentication failed")
                    return SearchResultCollection(results=[])
            
            self.logger.info(f"Starting CV search for keywords: {keywords}")
            
            # Perform the search with comprehensive filters
            search_success = self.search_manager.search_cvs(
                keywords=keywords, 
                location=location, 
                salary_min=salary_min, 
                salary_max=salary_max,
                # Job and industry filters
                job_type=job_type,
                industry=industry,
                # Location and timing filters
                distance=distance,
                time_period=time_period,
                # Boolean filters
                willing_to_relocate=willing_to_relocate,
                uk_driving_licence=uk_driving_licence,
                hide_recently_viewed=hide_recently_viewed,
                # Advanced filters
                languages=languages,
                minimum_match=minimum_match,
                sort_order=sort_order,
                # Advanced keyword filters
                must_have_keywords=must_have_keywords,
                any_keywords=any_keywords,
                none_keywords=none_keywords
            )
            
            # Phase 2: Collect search results with smart pagination
            if search_success:
                self.logger.info("🚀 Parsing search results with OPTIMIZED performance...")
                
                # SMART LOGIC: Only get what we need
                first_page_results = self.search_manager.parse_search_results_optimized() if hasattr(self.search_manager, "parse_search_results_optimized") else self.search_manager.parse_search_results()
                
                first_page_count = len(first_page_results.results)
                self.logger.info(f"📊 First page results: {first_page_count} found")
                
                # Get pagination info
                total_available = self.search_manager._detect_total_pages() * 20  # Estimate
                self.logger.info(f"📊 Total available results: {total_available}")
                
                # SMART PAGINATION DECISION
                if target_results and first_page_count >= target_results:
                    # We have enough on first page - no need for more pages!
                    self.logger.info(f"📄 Pagination decision: target of {target_results} already met with {first_page_count} results")
                    self.logger.info(f"📊 No additional pages needed")
                    results = first_page_results
                elif max_pages > 1:
                    # Need more pages, but be smart about it
                    self.logger.info(f"📄 Pagination decision: max_pages ({max_pages}) allows multiple pages")
                    
                    if target_results:
                        # Calculate minimum pages needed
                        pages_needed = math.ceil(target_results / max(first_page_count, 20))
                        actual_max_pages = min(max_pages, pages_needed)
                        self.logger.info(f"📊 Smart pagination: need {pages_needed} pages for {target_results} results, fetching max {actual_max_pages}")
                    else:
                        actual_max_pages = max_pages
                    
                    self.logger.info("🔄 Fetching additional pages...")
                    results = self.search_manager.get_all_results(max_pages=actual_max_pages, target_results=target_results)
                else:
                    # Single page only
                    self.logger.info(f"📄 Single page mode: using {first_page_count} results from first page")
                    results = first_page_results
                
                final_count = len(results.results)
                
                # Final summary with edge case information
                if target_results:
                    if final_count >= target_results:
                        self.logger.info(f"✅ Search SUCCESS: Found {final_count} CVs (target: {target_results})")
                    else:
                        self.logger.warning(f"⚠️  Search PARTIAL: Found {final_count} CVs (target: {target_results})")
                        if total_available > 0:
                            self.logger.info(f"📊 Available vs Found: {total_available} available, {final_count} collected")
                else:
                    self.logger.info(f"📊 Search completed: {final_count} CVs found")
                
                return results
            else:
                self.logger.error("Failed to perform search")
                return SearchResultCollection(
                    results=[],
                    search_keywords=keywords,
                    search_location=location
                )
                
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return SearchResultCollection(results=[])
    
    def download_cvs(self, search_results: SearchResultCollection, 
                    quantity: Optional[int] = None) -> List[CVData]:
        """
        Download CVs from search results.
        
        Args:
            search_results: Collection of search results to download from
            quantity: Number of CVs to download (overrides settings if provided)
            
        Returns:
            List of downloaded CVData objects
        """
        if not self.is_authenticated:
            self.logger.error("Must be authenticated before downloading CVs")
            return []
        
        if not self.download_manager:
            self.logger.error("Download manager not initialized")
            return []
        
        try:
            # Use provided quantity or fall back to settings
            download_quantity = quantity or self.settings.download.max_quantity
            
            # Start download process directly (no redundant logging)
            downloaded_cvs = self.download_manager.download_cvs_from_results(
                driver=self.get_webdriver(),
                search_results=search_results,
                max_downloads=download_quantity
            )
            
            return downloaded_cvs
            
        except Exception as e:
            self.logger.error(f"Download process failed: {e}")
            return []
    
    def run_session(self, keywords: List[str], location: Optional[str] = None,
                   max_downloads: Optional[int] = None) -> Dict[str, Any]:
        """
        Run a complete scraping session: authenticate, search, and download CVs.
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            max_downloads: Maximum number of CVs to download (optional)
            
        Returns:
            Dictionary containing session results and statistics
        """
        try:
            session_start = time.time()
            results = {
                'session_id': self.session_id,
                'keywords': keywords,
                'location': location,
                'status': 'started',
                'authentication': False,
                'search_results': None,
                'download_results': None,
                'error': None,
                'duration': 0
            }
            
            self.logger.info("🔍 Starting scraping session for keywords: %s", " ".join(keywords))
            self.logger.info("Starting scraping session: %s", self.session_id)
            
            # Phase 1: Authentication (optimized)
            self.logger.info("Phase 1: Authenticating with CV-Library")
            if not self.authenticate():
                results['error'] = "Authentication failed"
                results['status'] = 'failed'
                return results
            
            results['authentication'] = True
            
            # Initialize search and download managers with authenticated driver (already done in authenticate)
            if not self.search_manager:
                self.search_manager = SearchManager(self.settings, self.get_webdriver())
            if not self.download_manager:
                self.download_manager = DownloadManager(self.settings)
            
            # Phase 2: Search for CVs (streamlined)
            self.logger.info("Phase 2: Searching for CVs")
            
            # Determine target downloads first
            if max_downloads:
                target_downloads = max_downloads
            else:
                target_downloads = self.settings.download.max_quantity
            
            # Search with target results to enable automatic pagination
            search_results = self.search(keywords, location, target_results=target_downloads)
            if not search_results or not search_results.results:
                results['error'] = "Search failed or no results found"
                results['status'] = 'failed'
                return results
            
            # Store search results info (optimized - no name extraction for large result sets)
            results['search_results'] = {
                'total_found': len(search_results.results),
                'candidates': [result.name for result in search_results.results[:min(5, len(search_results.results))]]  # Only extract names for first 5
            }
            
            # Phase 3: Download CVs (optimized)
            self.logger.info("Phase 3: Downloading CVs")
            
            downloaded_cvs = self.download_cvs(search_results, target_downloads)
            
            # Phase 4: Final wait to ensure all downloads are completely finished
            self.logger.info("Phase 4: Ensuring all downloads are complete...")
            time.sleep(3)  # Final wait to ensure all file operations are complete
            
            results['download_results'] = {
                'successful_downloads': len(downloaded_cvs),
                'failed_downloads': len(search_results.results) - len(downloaded_cvs),
                'download_summary': self.download_manager.get_download_summary() if self.download_manager else {}
            }
            
            # Session completion
            session_duration = time.time() - session_start
            results['duration'] = session_duration
            results['status'] = 'completed'
            
            self.logger.info("🎉 Scraping session completed!")
            self.logger.info("✅ Total time: %.2f seconds", session_duration)
            self.logger.info("✅ CVs downloaded: %d", len(downloaded_cvs))
            
            return results
            
        except Exception as e:
            self.logger.error("❌ Scraping session failed: %s", e)
            results['error'] = str(e)
            results['status'] = 'failed'
            results['duration'] = time.time() - session_start
            return results
    
    def verify_authentication(self) -> bool:
        """
        Verify current authentication status.
        
        Returns:
            True if authenticated and session is valid, False otherwise
        """
        if not self.is_authenticated or not self.auth_manager:
            return False
        
        return self.auth_manager.verify_session()
    
    def logout(self) -> bool:
        """
        Logout from CV-Library.
        
        Returns:
            True if logout successful, False otherwise
        """
        try:
            if self.auth_manager:
                success = self.auth_manager.logout()
                if success:
                    self.is_authenticated = False
                    self.search_manager = None
                    self.download_manager = None
                return success
            return True
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            return False
    
    def save_session(self, session_data: Optional[Dict] = None) -> bool:
        """
        Save current session data to file.
        
        Args:
            session_data: Session data to save (optional, uses current if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data_to_save = session_data or self.current_session_data
            if not data_to_save:
                self.logger.warning("No session data to save")
                return False
            
            session_file = Path(self.settings.session.session_path) / f"{self.session_id}.json"
            return self.utils.session_manager.save_session(data_to_save, session_file)
            
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self, session_file: Path) -> Dict[str, Any]:
        """
        Load session data from file.
        
        Args:
            session_file: Path to session file
            
        Returns:
            Dictionary with session data
        """
        try:
            return self.utils.session_manager.load_session(session_file)
        except Exception as e:
            self.logger.error(f"Failed to load session: {e}")
            return {}
    
    def get_webdriver(self):
        """Get the current WebDriver instance."""
        if self.auth_manager:
            return self.auth_manager.get_driver()
        return None
    
    def close(self):
        """Clean up resources and close connections."""
        try:
            self.logger.info("Closing CV-Library scraper")
            
            # IMPORTANT: Logout first to release the session on CV-Library
            if self.is_authenticated and self.auth_manager:
                self.logger.info("Logging out to release CV-Library session")
                logout_success = self.auth_manager.logout()
                if logout_success:
                    self.logger.info("Successfully logged out from CV-Library")
                else:
                    self.logger.warning("Logout may have failed, but continuing cleanup")
            
            # Close authentication manager (this will close WebDriver)
            if self.auth_manager:
                self.auth_manager.close()
            
            # Reset state
            self.is_authenticated = False
            self.search_manager = None
            self.download_manager = None
            
            self.logger.info("CV-Library scraper closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            # Even if there's an error, try to reset state
            self.is_authenticated = False
            self.search_manager = None
            self.download_manager = None 