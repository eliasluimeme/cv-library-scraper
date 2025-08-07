#!/usr/bin/env python3
"""
Production Runner for CV-Library Scraper
Demonstrates enhanced performance and reliability features for production deployment.
"""

import os
import time
import logging
from typing import List, Optional
from pathlib import Path
import requests

# Import production enhancements
from src.config.production_settings import (
    PRODUCTION_CONFIG, 
    PRODUCTION_OPTIMIZER, 
    PERFORMANCE_MONITOR
)
from src.scraper.cv_library_scraper import CVLibraryScraper
from src.config.settings import Settings


class ProductionCVScraper:
    """
    Production-grade CV scraper with enhanced performance and reliability.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.logger = logging.getLogger(__name__)
        self.settings = Settings()  # Settings class doesn't take config_path argument
        self.scraper = None
        self.session_stats = {
            'start_time': None,
            'end_time': None,
            'total_processed': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'average_time_per_cv': 0.0
        }
        
        # Apply production optimizations
        self._setup_production_environment()
        
    def _check_api_server_status(self):
        """Check if the API server is running and warn user."""
        try:
            response = requests.get("http://localhost:8000/", timeout=2)
            if response.status_code == 200:
                self.logger.warning("⚠️  API server detected running on localhost:8000")
                self.logger.info("💡 Using separate browser profile to avoid conflicts")
                return True
        except requests.exceptions.RequestException:
            pass
        return False
        
    def _setup_production_environment(self):
        """Setup production environment with optimizations."""
        self.logger.info("🚀 Setting up production environment...")
        
        # Check for running API server
        api_running = self._check_api_server_status()
        
        # Configure production logging
        PRODUCTION_OPTIMIZER.setup_logging()
        
        # Set environment variables for production
        os.environ['CV_SCRAPER_MODE'] = 'production'
        os.environ['BROWSER_HEADLESS'] = str(PRODUCTION_CONFIG.HEADLESS_PRODUCTION)
        
        # Use unique profile to avoid conflicts with API server
        profile_name = 'production_runner' if api_running else 'production_runner'
        os.environ['BROWSER_PROFILE'] = profile_name
        
        # Create output directories
        Path("downloaded_cvs").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
        self.logger.info("✅ Production environment configured")
        self.logger.info(f"🔧 Using browser profile: {profile_name}")
        if api_running:
            self.logger.info("🔄 Running alongside API server with separate profile")
        
    def run_production_session(self, keywords: List[str], 
                             location: Optional[str] = None,
                             max_downloads: int = 50,
                             # Salary filters
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
                             none_keywords: Optional[str] = None) -> dict:
        """
        Run a production scraping session with sequential processing.
        
        Args:
            keywords: Search keywords
            location: Location filter
            max_downloads: Maximum number of CVs to download
            
        Returns:
            Session results and statistics
        """
        self.session_stats['start_time'] = time.time()
        
        try:
            self.logger.info("🎯 STARTING PRODUCTION CV SCRAPING SESSION")
            self.logger.info("=" * 60)
            self.logger.info(f"📋 Keywords: {', '.join(keywords)}")
            self.logger.info(f"📍 Location: {location or 'All locations'}")
            self.logger.info(f"📊 Target CVs: {max_downloads}")
            self.logger.info("🔄 Processing Mode: Sequential (Reliable)")
            
            # Initialize scraper with production settings
            self.scraper = CVLibraryScraper(self.settings)
            
            # Phase 1: Authentication and Search
            PERFORMANCE_MONITOR.start_operation()
            
            self.logger.info("\n🔐 Phase 1: Authentication & Search")
            search_results = self._perform_search(keywords, location, max_downloads, 
                                                 salary_min, salary_max, job_type, industry, 
                                                 distance, time_period, willing_to_relocate, 
                                                 uk_driving_licence, hide_recently_viewed, 
                                                 languages, minimum_match, sort_order, 
                                                 must_have_keywords, any_keywords, none_keywords)
            
            if not search_results or not search_results.results:
                self.logger.error("❌ No search results found")
                return self._generate_session_report(success=False, error="No search results")
            
            PERFORMANCE_MONITOR.end_operation(success=True)
            
            # Phase 2: Download CVs (Sequential Processing Only)
            self.logger.info(f"\n📥 Phase 2: Processing {len(search_results.results)} candidates")
            downloaded_cvs = self._process_sequential(search_results, max_downloads)
            
            # Phase 3: Generate Results
            self.session_stats['end_time'] = time.time()
            self.session_stats['total_processed'] = len(search_results.results)
            self.session_stats['successful_downloads'] = len(downloaded_cvs)
            self.session_stats['failed_downloads'] = len(search_results.results) - len(downloaded_cvs)
            
            session_duration = self.session_stats['end_time'] - self.session_stats['start_time']
            self.session_stats['average_time_per_cv'] = session_duration / max(len(search_results.results), 1)
            
            return self._generate_session_report(success=True, downloaded_cvs=downloaded_cvs)
            
        except Exception as e:
            self.logger.error(f"❌ Production session failed: {e}")
            return self._generate_session_report(success=False, error=str(e))
            
        finally:
            self._cleanup_session()
            
    def _perform_search(self, keywords: List[str], location: Optional[str], 
                       max_downloads: int,
                       salary_min: Optional[str] = None, salary_max: Optional[str] = None,
                       job_type: Optional[List[str]] = None, industry: Optional[List[str]] = None,
                       distance: Optional[int] = None, time_period: Optional[str] = None,
                       willing_to_relocate: Optional[bool] = None, uk_driving_licence: Optional[bool] = None,
                       hide_recently_viewed: Optional[bool] = None,
                       languages: Optional[List[str]] = None, minimum_match: Optional[str] = None,
                       sort_order: Optional[str] = None,
                       must_have_keywords: Optional[str] = None, any_keywords: Optional[str] = None,
                       none_keywords: Optional[str] = None):
        """Perform search with production optimizations."""
        try:
            # Authenticate first
            self.logger.info("🔐 Authenticating with CV-Library...")
            if not self.scraper.authenticate():
                raise Exception("Authentication failed")
            self.logger.info("✅ Authentication successful")
            
            # Use the existing scraper's search functionality with comprehensive filters
            search_results = self.scraper.search(
                keywords=keywords, 
                location=location,
                # Salary filters
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
                none_keywords=none_keywords,
                # Target results
                target_results=max_downloads
            )
            
            self.logger.info(f"✅ Search completed: {len(search_results.results)} candidates found")
            return search_results
            
        except Exception as e:
            self.logger.error(f"❌ Search failed: {e}")
            raise
            
    def _process_sequential(self, search_results, max_downloads: int) -> List:
        """Process CVs sequentially using the proven reliable method."""
        try:
            self.logger.info("🔄 Using sequential processing for maximum reliability")
            
            downloaded_cvs = self.scraper.download_cvs(search_results, max_downloads)
            
            self.logger.info(f"✅ Sequential processing completed: {len(downloaded_cvs)} downloads")
            return downloaded_cvs
            
        except Exception as e:
            self.logger.error(f"❌ Sequential processing failed: {e}")
            return []
            
    def _generate_session_report(self, success: bool, downloaded_cvs: List = None, 
                                error: str = None) -> dict:
        """Generate comprehensive session report."""
        session_duration = (self.session_stats['end_time'] or time.time()) - (self.session_stats['start_time'] or time.time())
        
        report = {
            'success': success,
            'session_duration': session_duration,
            'statistics': self.session_stats.copy(),
            'performance_metrics': PERFORMANCE_MONITOR.get_performance_summary(),
            'production_config': {
                'max_retry_attempts': PRODUCTION_CONFIG.MAX_RETRY_ATTEMPTS,
                'headless_mode': PRODUCTION_CONFIG.HEADLESS_PRODUCTION,
                'rate_limiting': f"{PRODUCTION_CONFIG.MIN_DELAY_BETWEEN_REQUESTS}-{PRODUCTION_CONFIG.MAX_DELAY_BETWEEN_REQUESTS}s",
                'processing_mode': 'sequential_only'
            }
        }
        
        if success and downloaded_cvs:
            report['results'] = {
                'downloaded_files': [str(cv.file_path) for cv in downloaded_cvs if cv.file_path],
                'candidate_names': [cv.candidate.name if cv.candidate and cv.candidate.name else 'Unknown' for cv in downloaded_cvs],
                'success_rate': (len(downloaded_cvs) / max(self.session_stats['total_processed'], 1)) * 100
            }
        
        if error:
            report['error'] = error
            
        self._log_session_summary(report)
        return report
        
    def _log_session_summary(self, report: dict):
        """Log comprehensive session summary."""
        self.logger.info("\n🎉 PRODUCTION SESSION SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"✅ Success: {report['success']}")
        self.logger.info(f"⏱️ Duration: {report['session_duration']:.2f}s")
        self.logger.info(f"📊 Total Processed: {self.session_stats['total_processed']}")
        self.logger.info(f"✅ Successful: {self.session_stats['successful_downloads']}")
        self.logger.info(f"❌ Failed: {self.session_stats['failed_downloads']}")
        
        if self.session_stats['total_processed'] > 0:
            success_rate = (self.session_stats['successful_downloads'] / self.session_stats['total_processed']) * 100
            self.logger.info(f"📈 Success Rate: {success_rate:.1f}%")
            self.logger.info(f"⚡ Avg Time/CV: {self.session_stats['average_time_per_cv']:.2f}s")
            
        # Performance metrics
        perf_metrics = report['performance_metrics']
        self.logger.info(f"🚀 Performance: {perf_metrics['avg_time_per_operation']}")
        
    def _cleanup_session(self):
        """Cleanup resources after session."""
        try:
            if self.scraper:
                # Try to close the driver properly
                if hasattr(self.scraper, 'close') and callable(getattr(self.scraper, 'close')):
                    self.scraper.close()
                elif hasattr(self.scraper, 'driver') and self.scraper.driver:
                    try:
                        self.scraper.driver.quit()
                    except:
                        pass
                        
            self.logger.info("🧹 Session cleanup completed")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Cleanup warning: {e}")


def main():
    """Main entry point for production runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production CV-Library Scraper with Comprehensive Filters")
    parser.add_argument("--keywords", nargs="+", required=True, help="Search keywords")
    parser.add_argument("--location", type=str, help="Location filter (e.g., 'Manchester', 'London')")
    parser.add_argument("--max-downloads", type=int, default=50, help="Maximum downloads")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Config file path")

    # Salary filters
    parser.add_argument("--salary-min", type=str, help="Minimum salary filter (e.g., '30000')")
    parser.add_argument("--salary-max", type=str, help="Maximum salary filter (e.g., '50000')")

    # Job and industry filters
    parser.add_argument("--job-type", nargs="+", help="Job types (e.g., 'Permanent' 'Contract')")
    parser.add_argument("--industry", nargs="+", help="Industries (e.g., 'IT/Internet/Technical')")

    # Location and timing filters
    parser.add_argument("--distance", type=int, help="Distance in miles from location (e.g., 10, 25, 50)")
    parser.add_argument("--time-period", type=str, help="CV submission period in days (e.g., '1', '7', '30')")

    # Boolean filters
    parser.add_argument("--relocate", action="store_true", help="Only candidates willing to relocate")
    parser.add_argument("--driving-licence", action="store_true", help="Only candidates with UK driving licence")
    parser.add_argument("--hide-viewed", action="store_true", help="Hide recently viewed candidates")

    # Advanced filters
    parser.add_argument("--languages", nargs="+", help="Additional languages (e.g., 'French' 'German')")
    parser.add_argument("--min-match", type=str, help="Minimum match percentage (e.g., '60', '80')")
    parser.add_argument("--sort", type=str, choices=["relevancy desc", "updated desc", "distance asc"], 
                       default="relevancy desc", help="Sort order")

    # Advanced keyword filters
    parser.add_argument("--must-have", type=str, help="Keywords that must appear")
    parser.add_argument("--any-keywords", type=str, help="Any of these keywords")
    parser.add_argument("--none-keywords", type=str, help="Keywords that must not appear")

    args = parser.parse_args()
    
    # Initialize production scraper
    production_scraper = ProductionCVScraper(args.config)
    
    # Run production session with comprehensive filters
    results = production_scraper.run_production_session(
        keywords=args.keywords,
        location=args.location,
        max_downloads=args.max_downloads,
        # Salary filters
        salary_min=args.salary_min,
        salary_max=args.salary_max,
        # Job and industry filters
        job_type=args.job_type,
        industry=args.industry,
        # Location and timing filters
        distance=args.distance,
        time_period=args.time_period,
        # Boolean filters
        willing_to_relocate=args.relocate,
        uk_driving_licence=args.driving_licence,
        hide_recently_viewed=args.hide_viewed,
        # Advanced filters
        languages=args.languages,
        minimum_match=args.min_match,
        sort_order=args.sort,
        # Advanced keyword filters
        must_have_keywords=args.must_have,
        any_keywords=args.any_keywords,
        none_keywords=args.none_keywords
    )
    
    # Output results
    if results['success']:
        print(f"\n🎉 SUCCESS: Downloaded {results['statistics']['successful_downloads']} CVs")
        if 'results' in results and results['results']:
            print(f"📊 Success Rate: {results['results']['success_rate']:.1f}%")
        print(f"⏱️ Total Time: {results['session_duration']:.2f}s")
    else:
        print(f"\n❌ FAILED: {results.get('error', 'Unknown error')}")
        
    return 0 if results['success'] else 1


if __name__ == "__main__":
    exit(main()) 