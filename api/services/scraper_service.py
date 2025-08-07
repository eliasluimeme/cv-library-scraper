"""
Scraper Service - Production-Ready API wrapper for CV scraping operations
Enhanced with ProductionCVScraper for maximum reliability and monitoring
"""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any
from pathlib import Path

from api.models.requests import ScrapeRequest
from api.models.responses import ScrapingProgress, ScrapeResponse
from api.services.session_manager import SessionManager, SessionData

# Import production-ready scraper
try:
    from production_runner import ProductionCVScraper
    PRODUCTION_SCRAPER_AVAILABLE = True
except ImportError:
    # Fallback to basic scraper if production_runner not available
    from src.scraper.cv_library_scraper import CVLibraryScraper
    PRODUCTION_SCRAPER_AVAILABLE = False

# Import production enhancements
try:
    from src.config.production_settings import (
        PRODUCTION_CONFIG, 
        PRODUCTION_OPTIMIZER, 
        PERFORMANCE_MONITOR
    )
    PRODUCTION_FEATURES_AVAILABLE = True
except ImportError:
    PRODUCTION_FEATURES_AVAILABLE = False
    # Simple fallback objects
    class SimpleConfig:
        HEADLESS_PRODUCTION = False
    class SimpleOptimizer:
        def setup_logging(self): pass
    class SimpleMonitor:
        def start_operation(self): pass
        def end_operation(self, success=True): pass
        def get_performance_summary(self): return {'avg_time_per_operation': '0.0s'}
    
    PRODUCTION_CONFIG = SimpleConfig()
    PRODUCTION_OPTIMIZER = SimpleOptimizer()
    PERFORMANCE_MONITOR = SimpleMonitor()


class ScraperService:
    """
    Production-ready scraper service with enhanced reliability and monitoring.
    Uses the same logic and patterns as production_runner.py for consistency.
    """
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scraper")
        
        # Track active scrape operations with production-style statistics
        self._active_scrapes: Dict[str, Dict[str, Any]] = {}
        
        # Setup production environment for API
        self._setup_production_environment()
        
        self.logger.info("🚀 Production-ready ScraperService initialized")
    
    def _setup_production_environment(self):
        """Setup production environment for API operations."""
        if PRODUCTION_FEATURES_AVAILABLE:
            self.logger.info("🚀 Setting up production environment for API...")
            PRODUCTION_OPTIMIZER.setup_logging()
            
        # Create output directories
        Path("downloaded_cvs").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
        if PRODUCTION_FEATURES_AVAILABLE:
            self.logger.info("✅ Production environment configured for API")
        else:
            self.logger.info("ℹ️  API running in standard mode (production features not available)")
    
    def _initialize_session_stats(self, keywords: List[str], location: Optional[str] = None):
        """Initialize session statistics tracking (production_runner.py pattern)."""
        return {
            'start_time': time.time(),
            'end_time': None,
            'total_processed': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'average_time_per_cv': 0.0,
            'keywords_used': keywords,
            'location_used': location,
            'phase': 'initializing',
            'current_operation': 'Starting scraping session...'
        }
    
    def _generate_session_report(self, session_stats: dict, success: bool, 
                               downloaded_cvs: List = None, error: str = None) -> dict:
        """Generate comprehensive session report (production_runner.py pattern)."""
        session_duration = (session_stats.get('end_time', time.time()) - 
                          session_stats.get('start_time', time.time()))
        
        # Update final statistics
        if downloaded_cvs:
            session_stats['successful_downloads'] = len(downloaded_cvs)
            session_stats['failed_downloads'] = max(0, session_stats['total_processed'] - len(downloaded_cvs))
            if session_stats['total_processed'] > 0:
                session_stats['average_time_per_cv'] = session_duration / session_stats['total_processed']
        
        report = {
            'success': success,
            'session_duration': session_duration,
            'statistics': session_stats.copy(),
            'performance_metrics': PERFORMANCE_MONITOR.get_performance_summary() if PRODUCTION_FEATURES_AVAILABLE else {},
            'production_config': {
                'headless_mode': PRODUCTION_CONFIG.HEADLESS_PRODUCTION if PRODUCTION_FEATURES_AVAILABLE else False,
                'processing_mode': 'sequential_production_api',
                'production_features': PRODUCTION_FEATURES_AVAILABLE,
                'scraper_type': 'ProductionCVScraper' if PRODUCTION_SCRAPER_AVAILABLE else 'CVLibraryScraper'
            }
        }
        
        if success and downloaded_cvs:
            report['results'] = {
                'downloaded_files': [str(cv.file_path) for cv in downloaded_cvs if hasattr(cv, 'file_path') and cv.file_path],
                'candidate_names': [
                    cv.candidate.name if hasattr(cv, 'candidate') and cv.candidate and hasattr(cv.candidate, 'name') and cv.candidate.name 
                    else getattr(cv, 'name', 'Unknown') 
                    for cv in downloaded_cvs
                ],
                'success_rate': (len(downloaded_cvs) / max(session_stats['total_processed'], 1)) * 100
            }
        
        if error:
            report['error'] = error
            
        return report
    
    def _log_session_summary(self, report: dict, session_stats: dict):
        """Log comprehensive session summary (production_runner.py pattern)."""
        self.logger.info("\n🎉 API PRODUCTION SESSION SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"✅ Success: {report['success']}")
        self.logger.info(f"⏱️  Duration: {report['session_duration']:.2f}s")
        self.logger.info(f"📊 Total Processed: {session_stats['total_processed']}")
        self.logger.info(f"✅ Successful: {session_stats['successful_downloads']}")
        self.logger.info(f"❌ Failed: {session_stats['failed_downloads']}")
        
        if session_stats['total_processed'] > 0:
            success_rate = (session_stats['successful_downloads'] / session_stats['total_processed']) * 100
            self.logger.info(f"📈 Success Rate: {success_rate:.1f}%")
            self.logger.info(f"⚡ Avg Time/CV: {session_stats['average_time_per_cv']:.2f}s")
            
        # Performance metrics
        if PRODUCTION_FEATURES_AVAILABLE and 'performance_metrics' in report:
            perf_metrics = report['performance_metrics']
            self.logger.info(f"🚀 Performance: {perf_metrics.get('avg_time_per_operation', 'N/A')}")
    
    def _cleanup_session(self, scraper):
        """Cleanup resources after session (production_runner.py pattern)."""
        try:
            if scraper:
                # Use production cleanup method if available
                if hasattr(scraper, '_cleanup_session') and callable(getattr(scraper, '_cleanup_session')):
                    scraper._cleanup_session()
                elif hasattr(scraper, 'scraper') and scraper.scraper:
                    # For ProductionCVScraper wrapper
                    if hasattr(scraper.scraper, 'close') and callable(getattr(scraper.scraper, 'close')):
                        scraper.scraper.close()
                    elif hasattr(scraper.scraper, 'driver') and scraper.scraper.driver:
                        try:
                            scraper.scraper.driver.quit()
                        except:
                            pass
                elif hasattr(scraper, 'close') and callable(getattr(scraper, 'close')):
                    scraper.close()
                elif hasattr(scraper, 'driver') and scraper.driver:
                    try:
                        scraper.driver.quit()
                    except:
                        pass
                        
            self.logger.info("🧹 API session cleanup completed")
            
        except Exception as e:
            self.logger.warning(f"⚠️  API cleanup warning: {e}")
    
    async def scrape_cvs(self, scrape_request: ScrapeRequest) -> str:
        """
        Initiate CV scraping operation using production-ready logic.
        Returns operation ID for status tracking.
        """
        scrape_id = f"scrape_{scrape_request.session_id}_{int(time.time())}"
        
        # Initialize session statistics
        session_stats = self._initialize_session_stats(
            scrape_request.keywords, 
            scrape_request.location
        )
        
        # Store operation with initial status
        self._active_scrapes[scrape_id] = {
            'id': scrape_id,
            'session_id': scrape_request.session_id,
            'status': 'pending',
            'session_stats': session_stats,
            'request_params': scrape_request.dict(),
            'created_at': time.time(),
            'last_updated': time.time()
        }
        
        # Start scraping in background using production logic
        task = asyncio.create_task(self._run_production_scrape(scrape_id, scrape_request))
        
        self.logger.info(f"🚀 Production scrape operation {scrape_id} initiated")
        return scrape_id
    
    async def _run_production_scrape(self, scrape_id: str, scrape_request: ScrapeRequest):
        """Run production scraping operation using ProductionCVScraper logic."""
        try:
            # Update status
            self._active_scrapes[scrape_id]['status'] = 'running'
            self._active_scrapes[scrape_id]['last_updated'] = time.time()
            
            # Execute in thread pool using production logic
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._execute_production_scrape,
                scrape_id,
                scrape_request
            )
            
            # Update final status
            self._active_scrapes[scrape_id].update({
                'status': 'completed' if result['success'] else 'failed',
                'result': result,
                'last_updated': time.time()
            })
            
        except Exception as e:
            self.logger.error(f"Production scrape {scrape_id} failed: {e}", exc_info=True)
            self._active_scrapes[scrape_id].update({
                'status': 'failed',
                'error': str(e),
                'last_updated': time.time()
            })
    
    def _execute_production_scrape(self, scrape_id: str, scrape_request: ScrapeRequest) -> dict:
        """
        Execute production scraping using the existing authenticated session.
        This avoids browser profile conflicts by reusing the authenticated browser.
        """
        session_stats = self._active_scrapes[scrape_id]['session_stats']
        
        try:
            self.logger.info(f"🎯 STARTING API PRODUCTION CV SCRAPING SESSION: {scrape_id}")
            self.logger.info("=" * 60)
            self.logger.info(f"📋 Keywords: {', '.join(scrape_request.keywords)}")
            self.logger.info(f"📍 Location: {scrape_request.location or 'All locations'}")
            self.logger.info(f"📊 Target CVs: {scrape_request.max_downloads}")
            self.logger.info("🔄 Processing Mode: Sequential Production API (Reusing Session)")
            
            # Update progress
            session_stats.update({
                'phase': 'initializing',
                'current_operation': 'Getting authenticated session...'
            })
            self._active_scrapes[scrape_id]['session_stats'] = session_stats
            
            # Get the existing authenticated session
            session_data = self.session_manager.get_session(scrape_request.session_id)
            if not session_data:
                raise Exception(f"Session {scrape_request.session_id} not found")
            
            if not session_data.is_authenticated:
                raise Exception(f"Session {scrape_request.session_id} is not authenticated")
            
            # Use the existing authenticated scraper instance
            scraper = session_data.scraper_instance
            if not scraper:
                raise Exception("No authenticated scraper instance found in session")
            
            self.logger.info("🚀 Using existing authenticated scraper session for maximum efficiency")
            
            # Performance monitoring
            if PRODUCTION_FEATURES_AVAILABLE:
                PERFORMANCE_MONITOR.start_operation()
            
            # Update progress to searching
            session_stats.update({
                'phase': 'searching',
                'current_operation': 'Searching for CVs with comprehensive filters...'
            })
            self._active_scrapes[scrape_id]['session_stats'] = session_stats
            
            # Perform search using the existing authenticated scraper with comprehensive filters
            self.logger.info("🔍 Starting CV search with existing authenticated session")
            search_results = scraper.search(
                keywords=scrape_request.keywords,
                location=scrape_request.location,
                # Salary filters
                salary_min=scrape_request.salary_min,
                salary_max=scrape_request.salary_max,
                # Job and industry filters
                job_type=scrape_request.job_type,
                industry=scrape_request.industry,
                # Location and timing filters
                distance=scrape_request.distance,
                time_period=scrape_request.time_period,
                # Boolean filters
                willing_to_relocate=scrape_request.willing_to_relocate,
                uk_driving_licence=scrape_request.uk_driving_licence,
                hide_recently_viewed=scrape_request.hide_recently_viewed,
                # Advanced filters
                languages=scrape_request.languages,
                minimum_match=scrape_request.minimum_match,
                sort_order=scrape_request.sort_order,
                # Advanced keyword filters
                must_have_keywords=scrape_request.must_have_keywords,
                any_keywords=scrape_request.any_keywords,
                none_keywords=scrape_request.none_keywords,
                # Smart pagination with target results
                target_results=scrape_request.max_downloads
            )
            
            if not search_results or not search_results.results:
                raise Exception("No search results found")
            
            search_count = len(search_results.results)
            session_stats.update({
                'total_processed': search_count,
                'phase': 'downloading',
                'current_operation': f'Found {search_count} candidates, starting downloads...'
            })
            self._active_scrapes[scrape_id]['session_stats'] = session_stats
            
            self.logger.info(f"📊 Found {search_count} candidates, downloading up to {scrape_request.max_downloads}")
            
            # Download CVs using the existing authenticated session
            downloaded_cvs = scraper.download_cvs(search_results, quantity=scrape_request.max_downloads)
            
            # Update final statistics
            session_stats.update({
                'end_time': time.time(),
                'successful_downloads': len(downloaded_cvs),
                'failed_downloads': max(0, search_count - len(downloaded_cvs)),
                'phase': 'completed',
                'current_operation': 'Scraping completed successfully'
            })
            
            # Performance monitoring
            if PRODUCTION_FEATURES_AVAILABLE:
                PERFORMANCE_MONITOR.end_operation(success=True)
            
            # Generate comprehensive report using production pattern
            final_report = self._generate_session_report(session_stats, True, downloaded_cvs)
            
            # Add detailed results in production format
            final_report['results'] = {
                'downloaded_files': [str(cv.file_path) for cv in downloaded_cvs if hasattr(cv, 'file_path') and cv.file_path],
                'candidate_names': [
                    cv.candidate.name if hasattr(cv, 'candidate') and cv.candidate and hasattr(cv.candidate, 'name') and cv.candidate.name 
                    else getattr(cv, 'name', 'Unknown') 
                    for cv in downloaded_cvs
                ],
                'success_rate': (len(downloaded_cvs) / max(search_count, 1)) * 100
            }
            
            # Log comprehensive summary
            self._log_session_summary(final_report, session_stats)
            
            # Clean up browser resources while preserving the profile for future use
            self.logger.info("🧹 Cleaning up browser resources while preserving user profile...")
            self._cleanup_browser_but_preserve_profile(scraper, session_data)
            
            self.logger.info(f"✅ API Production scrape {scrape_id} completed successfully")
            return final_report
            
        except Exception as e:
            session_stats.update({
                'end_time': time.time(),
                'phase': 'failed',
                'current_operation': f'Scraping failed: {str(e)}'
            })
            
            error_report = self._generate_session_report(session_stats, False, error=str(e))
            self._log_session_summary(error_report, session_stats)
            
            # Clean up browser resources even on failure
            session_data = self.session_manager.get_session(scrape_request.session_id)
            if session_data and session_data.scraper_instance:
                self.logger.info("🧹 Cleaning up browser resources after failure...")
                self._cleanup_browser_but_preserve_profile(session_data.scraper_instance, session_data)
            
            self.logger.error(f"❌ API Production scrape {scrape_id} failed: {e}")
            return error_report
            
        # Browser cleanup is now handled explicitly above for both success and failure cases
    
    def _cleanup_browser_but_preserve_profile(self, scraper, session_data):
        """
        Clean up browser resources while preserving the user profile for future reuse.
        This ensures the browser closes but the profile data (cookies, session storage) is maintained.
        """
        try:
            if scraper:
                # First, save session metadata to preserve authentication state
                if hasattr(scraper, 'auth_manager') and scraper.auth_manager:
                    try:
                        # Save session metadata before closing
                        metadata = {
                            'login_time': time.time(),
                            'username': session_data.username,
                            'profile_preserved': True,
                            'last_scrape_time': time.time()
                        }
                        scraper.auth_manager._save_session_metadata(metadata)
                        self.logger.info(f"💾 Session metadata saved for user: {session_data.username}")
                    except Exception as e:
                        self.logger.warning(f"Could not save session metadata: {e}")
                
                # Close the browser instance cleanly
                if hasattr(scraper, 'close') and callable(getattr(scraper, 'close')):
                    scraper.close()
                    self.logger.info("🔒 Browser closed via scraper.close()")
                elif hasattr(scraper, 'auth_manager') and scraper.auth_manager and hasattr(scraper.auth_manager, 'close'):
                    scraper.auth_manager.close()
                    self.logger.info("🔒 Browser closed via auth_manager.close()")
                elif hasattr(scraper, 'auth_manager') and scraper.auth_manager and hasattr(scraper.auth_manager, 'driver'):
                    try:
                        scraper.auth_manager.driver.quit()
                        self.logger.info("🔒 Browser closed via driver.quit()")
                    except Exception as e:
                        self.logger.debug(f"Driver quit error: {e}")
                
                # Clear the scraper instance from session but keep the session data
                session_data.scraper_instance = None
                session_data.is_authenticated = False  # Will re-authenticate next time using saved profile
                
                self.logger.info(f"✅ Browser cleanup completed. Profile '{session_data.browser_profile_name}' preserved for future use.")
                
        except Exception as e:
            self.logger.warning(f"⚠️  Browser cleanup warning: {e}")
            # Ensure scraper instance is cleared even if cleanup fails
            if session_data:
                session_data.scraper_instance = None
                session_data.is_authenticated = False
    
    async def authenticate_session(self, session_id: str, username: str, password: str) -> bool:
        """
        Authenticate a session with CV-Library using production-ready logic.
        This method bridges the gap between the API and the production scraper.
        """
        try:
            session_data = self.session_manager.get_session(session_id)
            if not session_data:
                raise ValueError("Session not found")
            
            # Run authentication in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._run_authentication,
                session_data,
                username,
                password
            )
            
            # Update session data
            self.session_manager.update_session(
                session_id,
                is_authenticated=result
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Authentication failed for session {session_id}: {e}")
            return False
    
    def _run_authentication(self, session_data, username: str, password: str) -> bool:
        """Run authentication in a separate thread using production logic."""
        try:
            # For API authentication, we use the basic scraper approach since 
            # ProductionCVScraper is designed for complete session runs
            if PRODUCTION_SCRAPER_AVAILABLE:
                self.logger.info("Using ProductionCVScraper authentication approach")
                
                # Import the base scraper for authentication-only operations
                from src.scraper.cv_library_scraper import CVLibraryScraper
                from src.config.settings import Settings
                import os
                
                # Set user-specific browser profile via environment variable
                original_profile = os.environ.get('BROWSER_PROFILE')
                if session_data.browser_profile_name:
                    os.environ['BROWSER_PROFILE'] = session_data.browser_profile_name
                    self.logger.info(f"Using user-specific browser profile: {session_data.browser_profile_name}")
                
                try:
                    scraper = CVLibraryScraper(Settings())
                    
                    # First, try to use existing persistent session
                    self.logger.info("Checking for existing persistent browser session...")
                    try:
                        existing_auth = scraper.authenticate()  # No credentials = check existing session
                        if existing_auth:
                            self.logger.info("✅ Found existing authenticated browser session - reusing it!")
                            session_data.scraper_instance = scraper
                            return True
                    except Exception as e:
                        self.logger.info(f"No existing session found: {e}")
                    
                    # No existing session, perform fresh authentication
                    self.logger.info("Performing fresh authentication with provided credentials...")
                    success = scraper.authenticate(username, password)
                    
                    if success:
                        session_data.scraper_instance = scraper
                        self.logger.info(f"Authentication successful for session {session_data.session_id}")
                        self.logger.info(f"📝 User '{username}' authenticated using profile: {session_data.browser_profile_name}")
                    else:
                        if hasattr(scraper, 'close'):
                            scraper.close()
                        self.logger.warning(f"Authentication failed for session {session_data.session_id}")
                    
                    return success
                
                finally:
                    # Restore original profile setting
                    if original_profile is not None:
                        os.environ['BROWSER_PROFILE'] = original_profile
                    elif 'BROWSER_PROFILE' in os.environ:
                        del os.environ['BROWSER_PROFILE']
                
            else:
                # Fallback to basic scraper
                self.logger.info("Using basic CVLibraryScraper for authentication")
                from src.scraper.cv_library_scraper import CVLibraryScraper
                from src.config.settings import Settings
                
                scraper = CVLibraryScraper(Settings())
                success = scraper.authenticate(username, password)
                
                if success:
                    session_data.scraper_instance = scraper
                    self.logger.info(f"Authentication successful for session {session_data.session_id}")
                else:
                    if hasattr(scraper, 'close'):
                        scraper.close()
                    self.logger.warning(f"Authentication failed for session {session_data.session_id}")
                
                return success
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def get_scrape_status(self, scrape_id: str) -> Optional[dict]:
        """Get status of scraping operation with production-level details."""
        return self._active_scrapes.get(scrape_id)
    
    def list_scrapes(self, session_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        """List scraping operations for a session with production details."""
        session_scrapes = [
            scrape for scrape in self._active_scrapes.values()
            if scrape['session_id'] == session_id
        ]
        
        # Sort by creation time (newest first)
        session_scrapes.sort(key=lambda x: x['created_at'], reverse=True)
        
        return session_scrapes[offset:offset + limit]
    
    async def cleanup(self):
        """Cleanup service resources."""
        self.logger.info("🧹 Cleaning up ScraperService...")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Clear active scrapes
        self._active_scrapes.clear()
        
        self.logger.info("✅ ScraperService cleanup completed") 