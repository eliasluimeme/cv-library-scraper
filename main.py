#!/usr/bin/env python3
"""
CV-Library Scraper - Main CLI Entry Point

A robust Python web scraper for CV-Library's recruiter portal that can authenticate, 
search for CVs using predefined keywords, process results, and download CVs.

Usage:
    python main.py --keywords "Python Developer" --location "London" --max-downloads 10
    python main.py --config config/config.yaml --output-dir ./results/
    python main.py --resume-session session_12345.json
"""

import argparse
import logging
import logging.config
import sys
import yaml
import os
from pathlib import Path
from typing import List, Optional
import time # Added for timing

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import ConfigLoader, Settings
from src.scraper.utils import ScrapingUtils
from src.scraper.cv_library_scraper import CVLibraryScraper

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
    # Create simple fallback objects
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


def setup_logging(log_level: str = "INFO", log_path: Optional[str] = None):
    """Setup logging configuration."""
    
    # Create logs directory if specified
    if log_path:
        Path(log_path).mkdir(parents=True, exist_ok=True)
    
    # Load logging configuration
    try:
        with open("config/logging_config.yaml", 'r') as f:
            logging_config = yaml.safe_load(f)
        
        # Update log level if specified
        if log_level:
            logging_config['loggers']['cv_scraper']['level'] = log_level.upper()
            logging_config['root']['level'] = log_level.upper()
        
        # Update log path if specified
        if log_path:
            for handler in logging_config['handlers'].values():
                if 'filename' in handler:
                    filename = Path(handler['filename']).name
                    handler['filename'] = str(Path(log_path) / filename)
        
        logging.config.dictConfig(logging_config)
        
    except Exception as e:
        # Fallback to basic logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.getLogger(__name__).warning(f"Could not load logging config: {e}")


def setup_production_environment():
    """Setup production environment with optimizations (like production_runner.py)."""
    logger = logging.getLogger(__name__)
    
    if PRODUCTION_FEATURES_AVAILABLE:
        logger.info("🚀 Setting up production environment...")
        
        # Configure production logging
        PRODUCTION_OPTIMIZER.setup_logging()
        
        # Set environment variables for production
        os.environ['CV_SCRAPER_MODE'] = 'production'
        os.environ['BROWSER_HEADLESS'] = str(PRODUCTION_CONFIG.HEADLESS_PRODUCTION)
    
    # Create output directories (always do this regardless of production features)
    Path("downloaded_cvs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    if PRODUCTION_FEATURES_AVAILABLE:
        logger.info("✅ Production environment configured")
    else:
        logger.info("ℹ️  Running in standard mode (production features not available)")


def initialize_session_stats():
    """Initialize session statistics tracking."""
    return {
        'start_time': None,
        'end_time': None,
        'total_processed': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'average_time_per_cv': 0.0,
        'keywords_used': [],
        'location_used': None
    }


def generate_session_report(session_stats: dict, success: bool, downloaded_cvs: List = None, 
                          error: str = None) -> dict:
    """Generate comprehensive session report (like production_runner.py)."""
    session_duration = (session_stats['end_time'] or time.time()) - (session_stats['start_time'] or time.time())
    
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
            'processing_mode': 'sequential_production',
            'production_features': PRODUCTION_FEATURES_AVAILABLE
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


def log_session_summary(report: dict, session_stats: dict):
    """Log comprehensive session summary (like production_runner.py)."""
    logger = logging.getLogger(__name__)
    
    logger.info("\n🎉 PRODUCTION SESSION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"✅ Success: {report['success']}")
    logger.info(f"⏱️  Duration: {report['session_duration']:.2f}s")
    logger.info(f"📊 Total Processed: {session_stats['total_processed']}")
    logger.info(f"✅ Successful: {session_stats['successful_downloads']}")
    logger.info(f"❌ Failed: {session_stats['failed_downloads']}")
    
    if session_stats['total_processed'] > 0:
        success_rate = (session_stats['successful_downloads'] / session_stats['total_processed']) * 100
        logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        logger.info(f"⚡ Avg Time/CV: {session_stats['average_time_per_cv']:.2f}s")
        
    # Performance metrics
    if PRODUCTION_FEATURES_AVAILABLE and 'performance_metrics' in report:
        perf_metrics = report['performance_metrics']
        logger.info(f"🚀 Performance: {perf_metrics.get('avg_time_per_operation', 'N/A')}")


def cleanup_session(scraper):
    """Cleanup resources after session (like production_runner.py)."""
    logger = logging.getLogger(__name__)
    
    try:
        if scraper:
            # Try to close the driver properly
            if hasattr(scraper, 'close') and callable(getattr(scraper, 'close')):
                scraper.close()
            elif hasattr(scraper, 'driver') and scraper.driver:
                try:
                    scraper.driver.quit()
                except:
                    pass
                    
        logger.info("🧹 Session cleanup completed")
        
    except Exception as e:
        logger.warning(f"⚠️  Cleanup warning: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CV-Library Scraper - Production-Ready CLI with Comprehensive Filters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --keywords "Python Developer" --location "London" --max-downloads 10
  %(prog)s --keywords "Senior Engineer" "Machine Learning" --salary-min 50000 --salary-max 80000
  %(prog)s --config config/custom.yaml --job-type "Permanent" --industry "IT/Internet/Technical"
  %(prog)s --keywords "Data Scientist" --relocate --driving-licence --time-period 7
  %(prog)s --keywords "Manager" --must-have "leadership team" --none-keywords "junior intern"
        """
    )
    
    # Required arguments
    parser.add_argument("--keywords", nargs="+", 
                       help="Search keywords (space-separated)")
    
    # Core search parameters
    parser.add_argument("--location", type=str, 
                       help="Location filter (e.g., 'Manchester', 'London')")
    parser.add_argument("--max-downloads", type=int, default=25,
                       help="Maximum number of CVs to download (default: 25)")
    
    # Configuration and output
    parser.add_argument("--config", type=str, default="config/config.yaml",
                       help="Configuration file path")
    parser.add_argument("--output-dir", type=str,
                       help="Output directory for downloaded CVs")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")

    # Salary filters
    parser.add_argument("--salary-min", type=str, 
                       help="Minimum salary filter (e.g., '30000')")
    parser.add_argument("--salary-max", type=str, 
                       help="Maximum salary filter (e.g., '50000')")

    # Job and industry filters
    parser.add_argument("--job-type", nargs="+", 
                       help="Job types (e.g., 'Permanent' 'Contract')")
    parser.add_argument("--industry", nargs="+", 
                       help="Industries (e.g., 'IT/Internet/Technical')")

    # Location and timing filters
    parser.add_argument("--distance", type=int, 
                       help="Distance in miles from location (e.g., 10, 25, 50)")
    parser.add_argument("--time-period", type=str, 
                       help="CV submission period in days (e.g., '1', '7', '30')")

    # Boolean filters
    parser.add_argument("--relocate", action="store_true", 
                       help="Only candidates willing to relocate")
    parser.add_argument("--driving-licence", action="store_true", 
                       help="Only candidates with UK driving licence")
    parser.add_argument("--hide-viewed", action="store_true", 
                       help="Hide recently viewed candidates")

    # Advanced filters
    parser.add_argument("--languages", nargs="+", 
                       help="Additional languages (e.g., 'French' 'German')")
    parser.add_argument("--min-match", type=str, 
                       help="Minimum match percentage (e.g., '60', '80')")
    parser.add_argument("--sort", type=str, 
                       choices=["relevancy desc", "updated desc", "distance asc"], 
                       default="relevancy desc", help="Sort order")

    # Advanced keyword filters
    parser.add_argument("--must-have", type=str, 
                       help="Keywords that must appear")
    parser.add_argument("--any-keywords", type=str, 
                       help="Any of these keywords")
    parser.add_argument("--none-keywords", type=str, 
                       help="Keywords that must not appear")
    
    # Session management
    parser.add_argument("--resume-session", type=str,
                       help="Resume from saved session file")
    parser.add_argument("--save-session", action="store_true",
                       help="Save session data after completion")
    
    # Operational modes
    parser.add_argument("--demo", action="store_true",
                       help="Run in demo mode (show workflow without execution)")
    parser.add_argument("--validate", action="store_true",
                       help="Validate configuration and exit")
    parser.add_argument("--version", action="store_true",
                       help="Show version information and exit")
    
    return parser.parse_args()


def validate_arguments(args):
    """Validate command line arguments."""
    errors = []
    
    # Check if we have enough information to perform a search
    if not args.resume_session:
        if not args.keywords and not args.config:
            errors.append("Either --keywords or --config must be specified for new searches")
        
        if hasattr(args, 'max_downloads') and args.max_downloads and args.max_downloads <= 0:
            errors.append("Max downloads must be a positive number")
        
        if (hasattr(args, 'salary_min') and args.salary_min and 
            hasattr(args, 'salary_max') and args.salary_max):
            try:
                if int(args.salary_min) > int(args.salary_max):
                    errors.append("Minimum salary cannot be greater than maximum salary")
            except (ValueError, TypeError):
                errors.append("Salary values must be numeric")
    
    # Validate file paths
    if args.config and not Path(args.config).exists():
        errors.append(f"Configuration file not found: {args.config}")
    
    if args.resume_session and not Path(args.resume_session).exists():
        errors.append(f"Session file not found: {args.resume_session}")
    
    return errors


def create_settings_from_args(args) -> Settings:
    """Create Settings object from command line arguments."""
    
    # Load base configuration
    config_loader = ConfigLoader(config_path=args.config if args.config else "config/config.yaml")
    settings = config_loader.create_settings()
    
    # Override with command line arguments
    if args.keywords:
        settings.search.keywords = args.keywords  # Now it's already a list
    
    if args.location:
        settings.search.locations = [args.location]
    
    if hasattr(args, 'max_downloads') and args.max_downloads:
        settings.download.max_quantity = args.max_downloads
    
    if args.output_dir:
        settings.download.download_path = args.output_dir
    
    # Advanced search parameters (new production-ready features)
    if hasattr(args, 'salary_min') and args.salary_min:
        settings.search.salary_min = args.salary_min
    
    if hasattr(args, 'salary_max') and args.salary_max:
        settings.search.salary_max = args.salary_max
    
    return settings


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                    CV-Library Scraper v1.0                   ║
║         Automated CV downloading from CV-Library portal       ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_settings_summary(settings: Settings):
    """Print a summary of current settings."""
    print("\n📋 Configuration Summary:")
    print(f"   Search Keywords: {', '.join(settings.search.keywords) if settings.search.keywords else 'None'}")
    print(f"   Search Locations: {', '.join(settings.search.locations) if settings.search.locations else 'None'}")
    print(f"   Download Quantity: {settings.download.max_quantity}")
    print(f"   Download Path: {settings.download.download_path}")
    print(f"   Browser: {settings.browser.browser_type} (headless: {settings.browser.headless})")
    
    # Show profile information
    if settings.browser.profile.enable_persistent_profile:
        print(f"   Profile: {settings.browser.profile.profile_name} (persistent)")
        if settings.browser.profile.auto_backup:
            print("   Profile Backup: Enabled")
        if settings.browser.profile.clear_on_logout:
            print("   Clear on Logout: Enabled")
    else:
        print("   Profile: Temporary session")
    
    print(f"   Rate Limiting: {settings.scraping.delay_min}-{settings.scraping.delay_max}s delays")
    print()


def main():
    """Main application entry point with production-ready enhancements."""
    
    scraper = None  # Initialize scraper variable for finally block
    session_stats = initialize_session_stats()
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Setup production environment first
        setup_production_environment()
        
        # Setup logging early
        setup_logging(args.log_level)
        logger = logging.getLogger('cv_scraper')
        
        # Print banner
        print_banner()
        
        # Validate arguments
        validation_errors = validate_arguments(args)
        if validation_errors:
            print("❌ Validation Errors:")
            for error in validation_errors:
                print(f"   • {error}")
            return 1
        
        # Create settings
        settings = create_settings_from_args(args)
        
        # Print settings summary
        print_settings_summary(settings)
        
        # Validate settings
        settings_errors = settings.validate()
        if settings_errors:
            print("❌ Configuration Errors:")
            for error in settings_errors:
                print(f"   • {error}")
            return 1
        
        logger.info("Starting CV-Library scraper with production enhancements")
        
        # Initialize scraper
        scraper = CVLibraryScraper(settings)
        
        print("🚀 CV-Library Scraper initialized successfully!")
        
        # Show profile information if using persistent profiles
        if settings.browser.profile.enable_persistent_profile:
            from src.scraper.browser_profile import BrowserProfileManager
            profile_manager = BrowserProfileManager(settings)
            profile_info = profile_manager.get_profile_info(settings.browser.profile.profile_name)
            print(f"📁 Using persistent profile: {profile_info['name']}")
            if profile_info.get('exists'):
                print(f"   Size: {profile_info.get('size_mb', 0):.1f} MB")
                print(f"   Has session data: {'Yes' if profile_info.get('has_metadata') else 'No'}")
        
        if args.demo:
            print("   🔍 Demo mode - no actual scraping will be performed")
            print("\n✅ All systems ready! The scraper would now:")
            print("   1. 🔐 Authenticate with CV-Library")
            print("   2. 🔍 Search for CVs matching criteria")
            print("   3. 📄 Parse and filter results")
            print("   4. ⬇️  Download selected CVs")
            print("   5. 📊 Generate reports")
            return 0
        
        # Run scraping session with production-ready approach
        if settings.search.keywords:
            session_stats['start_time'] = time.time()
            session_stats['keywords_used'] = settings.search.keywords
            session_stats['location_used'] = settings.search.locations[0] if settings.search.locations else None
            
            print(f"\n🎯 STARTING PRODUCTION CV SCRAPING SESSION")
            print("=" * 60)
            print(f"📋 Keywords: {', '.join(settings.search.keywords)}")
            print(f"📍 Location: {session_stats['location_used'] or 'All locations'}")
            print(f"📊 Target CVs: {getattr(args, 'max_downloads', None) or settings.download.max_quantity}")
            print("🔄 Processing Mode: Sequential (Production-Ready)")
            
            try:
                # Phase 1: Authentication 
                print("\n🔐 Phase 1: Authentication & Setup")
                if PRODUCTION_FEATURES_AVAILABLE:
                    PERFORMANCE_MONITOR.start_operation()
                
                if not scraper.authenticate():
                    print("❌ Authentication failed")
                    session_stats['end_time'] = time.time()
                    report = generate_session_report(session_stats, False, error="Authentication failed")
                    log_session_summary(report, session_stats)
                    return 1
                print("✅ Authentication successful")
                
                # Phase 2: Search with comprehensive filters (production-ready approach)
                print("\n🔍 Phase 2: Searching for CVs with comprehensive filters...")
                search_results = scraper.search(
                    keywords=settings.search.keywords,
                    location=settings.search.locations[0] if settings.search.locations else None,
                    # Salary filters
                    salary_min=getattr(args, 'salary_min', None),
                    salary_max=getattr(args, 'salary_max', None),
                    # Job and industry filters
                    job_type=getattr(args, 'job_type', None),
                    industry=getattr(args, 'industry', None),
                    # Location and timing filters
                    distance=getattr(args, 'distance', None),
                    time_period=getattr(args, 'time_period', None),
                    # Boolean filters
                    willing_to_relocate=getattr(args, 'relocate', None),
                    uk_driving_licence=getattr(args, 'driving_licence', None),
                    hide_recently_viewed=getattr(args, 'hide_viewed', None),
                    # Advanced filters
                    languages=getattr(args, 'languages', None),
                    minimum_match=getattr(args, 'min_match', None),
                    sort_order=getattr(args, 'sort', None),
                    # Advanced keyword filters
                    must_have_keywords=getattr(args, 'must_have', None),
                    any_keywords=getattr(args, 'any_keywords', None),
                    none_keywords=getattr(args, 'none_keywords', None),
                    # Smart pagination with target results
                    target_results=getattr(args, 'max_downloads', None) or settings.download.max_quantity
                )
                
                if not search_results or not search_results.results:
                    print("❌ Search failed or no results found")
                    session_stats['end_time'] = time.time()
                    report = generate_session_report(session_stats, False, error="No search results found")
                    log_session_summary(report, session_stats)
                    return 1
                
                search_count = len(search_results.results)
                session_stats['total_processed'] = search_count
                print(f"✅ Search completed: {search_count} candidates found")
                
                if PRODUCTION_FEATURES_AVAILABLE:
                    PERFORMANCE_MONITOR.end_operation(success=True)
                
                # Phase 3: Download CVs with smart quantity control (sequential processing)
                target_downloads = getattr(args, 'max_downloads', None) or settings.download.max_quantity
                print(f"\n📥 Phase 3: Processing {search_count} candidates")
                print("🔄 Using sequential processing for maximum reliability")
                
                downloaded_cvs = scraper.download_cvs(search_results, target_downloads)
                
                # Session completion
                session_stats['end_time'] = time.time()
                session_stats['successful_downloads'] = len(downloaded_cvs)
                session_stats['failed_downloads'] = max(0, search_count - len(downloaded_cvs))
                
                # Generate comprehensive report
                report = generate_session_report(session_stats, True, downloaded_cvs)
                
                # Print results (production-style summary)
                print(f"\n🎉 SCRAPING SESSION COMPLETED!")
                print(f"=" * 50)
                print(f"⏱️  Duration: {report['session_duration']:.2f} seconds")
                print(f"🔍 Keywords: {', '.join(settings.search.keywords)}")
                print(f"📊 Candidates Found: {search_count}")
                print(f"✅ Successfully Downloaded: {len(downloaded_cvs)} CVs")
                print(f"❌ Failed Downloads: {session_stats['failed_downloads']}")
                
                if search_count > 0:
                    success_rate = (len(downloaded_cvs) / search_count) * 100
                    print(f"📈 Download Success Rate: {success_rate:.1f}%")
                    print(f"⚡ Avg Time/CV: {session_stats['average_time_per_cv']:.2f}s")
                
                # Log comprehensive session summary
                log_session_summary(report, session_stats)
                
                # Save session if requested
                if args.save_session:
                    scraper.save_session(report)
                    print(f"💾 Session saved with ID: {scraper.session_id}")
                
                return 0
                
            except Exception as e:
                session_stats['end_time'] = time.time()
                print(f"❌ Scraping session failed: {e}")
                logger = logging.getLogger('cv_scraper')
                logger.error(f"Session error: {e}", exc_info=True)
                
                # Generate error report
                report = generate_session_report(session_stats, False, error=str(e))
                log_session_summary(report, session_stats)
                return 1
        
        else:
            print("\n⚠️  No keywords specified. Use --keywords or --config to define search criteria.")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        logger = logging.getLogger('cv_scraper')
        logger.warning("Application interrupted by user")
        return 1
        
    except Exception as e:
        logger = logging.getLogger('cv_scraper')
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1
    
    finally:
        # CRITICAL: Always ensure cleanup using production-ready cleanup
        cleanup_session(scraper)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 