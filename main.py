#!/usr/bin/env python3
"""
CV-Library Scraper - Main CLI Entry Point

A robust Python web scraper for CV-Library's recruiter portal that can authenticate, 
search for CVs using predefined keywords, process results, and download CVs.

Usage:
    python main.py --keywords "Python,Django" --location "London" --quantity 25
    python main.py --config config/config.yaml --output-dir ./results/
    python main.py --resume-session session_12345.json
"""

import argparse
import logging
import logging.config
import sys
import yaml
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import ConfigLoader, Settings
from src.scraper.utils import ScrapingUtils
from src.scraper.cv_library_scraper import CVLibraryScraper


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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CV-Library Scraper - Download CVs from CV-Library recruiter portal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --keywords "Python developer,Data scientist" --location London --quantity 25
  %(prog)s --config custom_config.yaml --output-dir ./downloads/
  %(prog)s --resume-session session_20240101_123456.json
  %(prog)s --keywords "DevOps" --headless false --log-level DEBUG
        """
    )
    
    # Search parameters
    search_group = parser.add_argument_group('Search Parameters')
    search_group.add_argument(
        '--keywords', '-k',
        type=str,
        help='Comma-separated list of keywords to search for (e.g., "Python,Django,React")'
    )
    search_group.add_argument(
        '--location', '-l',
        type=str,
        help='Location to search in (e.g., "London", "Manchester", "Remote")'
    )
    search_group.add_argument(
        '--salary-min',
        type=int,
        help='Minimum salary filter'
    )
    search_group.add_argument(
        '--salary-max',
        type=int,
        help='Maximum salary filter'
    )
    search_group.add_argument(
        '--experience-level',
        choices=['entry', 'mid-level', 'senior', 'executive'],
        help='Experience level filter'
    )
    
    # Download parameters
    download_group = parser.add_argument_group('Download Parameters')
    download_group.add_argument(
        '--quantity', '-q',
        type=int,
        default=10,
        help='Number of CVs to download (default: 10)'
    )
    download_group.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory for downloaded CVs'
    )
    download_group.add_argument(
        '--file-formats',
        type=str,
        default='pdf,doc,docx',
        help='Comma-separated list of file formats to download (default: pdf,doc,docx)'
    )
    
    # Configuration
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration YAML file'
    )
    config_group.add_argument(
        '--env-file',
        type=str,
        help='Path to environment variables file (default: .env)'
    )
    
    # Browser settings
    browser_group = parser.add_argument_group('Browser Settings')
    browser_group.add_argument(
        '--browser',
        choices=['chrome', 'firefox'],
        help='Browser to use for scraping'
    )
    browser_group.add_argument(
        '--headless',
        type=str,
        choices=['true', 'false'],
        help='Run browser in headless mode (true/false)'
    )
    browser_group.add_argument(
        '--enable-persistent-profile',
        action='store_true',
        help='Enable persistent browser profile (recommended for single-session compliance)'
    )
    browser_group.add_argument(
        '--disable-persistent-profile',
        action='store_true',
        help='Disable persistent browser profile (use temporary sessions)'
    )
    browser_group.add_argument(
        '--profile-name',
        type=str,
        default='default',
        help='Name of the browser profile to use (default: default)'
    )
    browser_group.add_argument(
        '--clear-profile',
        action='store_true',
        help='Clear the browser profile before starting (fresh session)'
    )
    browser_group.add_argument(
        '--backup-profile',
        action='store_true',
        help='Create a backup of the profile before starting'
    )
    
    # Session management
    session_group = parser.add_argument_group('Session Management')
    session_group.add_argument(
        '--resume-session',
        type=str,
        help='Resume from a previous session file'
    )
    session_group.add_argument(
        '--save-session',
        action='store_true',
        help='Save session data for resuming later'
    )
    
    # Logging and debugging
    debug_group = parser.add_argument_group('Logging and Debugging')
    debug_group.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    debug_group.add_argument(
        '--log-path',
        type=str,
        help='Directory for log files'
    )
    debug_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without actually downloading files'
    )
    
    # Rate limiting
    rate_group = parser.add_argument_group('Rate Limiting')
    rate_group.add_argument(
        '--delay-min',
        type=float,
        help='Minimum delay between requests in seconds'
    )
    rate_group.add_argument(
        '--delay-max',
        type=float,
        help='Maximum delay between requests in seconds'
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """Validate command line arguments."""
    errors = []
    
    # Check if we have enough information to perform a search
    if not args.resume_session:
        if not args.keywords and not args.config:
            errors.append("Either --keywords or --config must be specified for new searches")
        
        if args.quantity and args.quantity <= 0:
            errors.append("Quantity must be a positive number")
        
        if args.salary_min and args.salary_max and args.salary_min > args.salary_max:
            errors.append("Minimum salary cannot be greater than maximum salary")
    
    # Validate file paths
    if args.config and not Path(args.config).exists():
        errors.append(f"Configuration file not found: {args.config}")
    
    if args.resume_session and not Path(args.resume_session).exists():
        errors.append(f"Session file not found: {args.resume_session}")
    
    if args.env_file and not Path(args.env_file).exists():
        errors.append(f"Environment file not found: {args.env_file}")
    
    return errors


def create_settings_from_args(args) -> Settings:
    """Create Settings object from command line arguments."""
    
    # Load base configuration
    config_loader = ConfigLoader(
        config_path=args.config,
        env_file=args.env_file
    )
    settings = config_loader.create_settings()
    
    # Override with command line arguments
    if args.keywords:
        settings.search.keywords = [k.strip() for k in args.keywords.split(',')]
    
    if args.location:
        settings.search.locations = [args.location]
    
    if args.salary_min:
        settings.search.salary_min = args.salary_min
    
    if args.salary_max:
        settings.search.salary_max = args.salary_max
    
    if args.experience_level:
        settings.search.experience_level = args.experience_level
    
    if args.quantity:
        settings.download.max_quantity = args.quantity
    
    if args.output_dir:
        settings.download.download_path = args.output_dir
    
    if args.file_formats:
        settings.download.file_formats = [f.strip() for f in args.file_formats.split(',')]
    
    if args.browser:
        settings.browser.browser_type = args.browser
    
    if args.headless:
        settings.browser.headless = args.headless.lower() == 'true'
    
    # Handle persistent profile arguments
    if args.enable_persistent_profile:
        settings.browser.profile.enable_persistent_profile = True
    
    if args.disable_persistent_profile:
        settings.browser.profile.enable_persistent_profile = False
    
    if args.profile_name:
        settings.browser.profile.profile_name = args.profile_name
    
    if args.backup_profile:
        settings.browser.profile.auto_backup = True
        settings.browser.profile.backup_on_login = True
    
    if args.clear_profile:
        settings.browser.profile.clear_on_logout = True
    
    if args.log_path:
        settings.logging.log_path = args.log_path
    
    if args.delay_min:
        settings.scraping.delay_min = args.delay_min
    
    if args.delay_max:
        settings.scraping.delay_max = args.delay_max
    
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
    """Main application entry point."""
    
    scraper = None  # Initialize scraper variable for finally block
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Setup logging early
        setup_logging(args.log_level, args.log_path)
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
        
        logger.info("Starting CV-Library scraper")
        
        # Initialize scraper
        scraper = CVLibraryScraper(settings)
        
        # Handle profile management
        if args.clear_profile and settings.browser.profile.enable_persistent_profile:
            from src.scraper.browser_profile import BrowserProfileManager
            profile_manager = BrowserProfileManager(settings)
            profile_manager.clear_profile(settings.browser.profile.profile_name)
            print(f"✅ Profile '{settings.browser.profile.profile_name}' cleared")
        
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
        
        if args.dry_run:
            print("   🔍 Dry run mode - no actual scraping will be performed")
            print("\n✅ All systems ready! The scraper would now:")
            print("   1. 🔐 Authenticate with CV-Library")
            print("   2. 🔍 Search for CVs matching criteria")
            print("   3. 📄 Parse and filter results")
            print("   4. ⬇️  Download selected CVs")
            print("   5. 📊 Generate reports")
            return 0
        
        # Run scraping session
        if settings.search.keywords:
            print(f"\n🔍 Starting scraping session for keywords: {', '.join(settings.search.keywords)}")
            
            session_results = scraper.run_session(
                keywords=settings.search.keywords,
                location=settings.search.locations[0] if settings.search.locations else None,
                max_downloads=settings.download.max_quantity
            )
            
            # Print results
            print(f"\n📊 Session Results:")
            print(f"   Session ID: {session_results['session_id']}")
            print(f"   Keywords: {', '.join(session_results['keywords'])}")
            print(f"   Status: {'✅ Success' if session_results.get('status') == 'completed' else '❌ Failed'}")
            print(f"   Duration: {session_results.get('duration', 0):.2f} seconds")
            
            if session_results.get('search_results'):
                search_info = session_results['search_results']
                print(f"   Search Results: {search_info.get('total_found', 0)} candidates found")
            
            if session_results.get('download_results'):
                download_info = session_results['download_results']
                print(f"   Downloads: {download_info.get('successful_downloads', 0)} successful, {download_info.get('failed_downloads', 0)} failed")
            
            if session_results.get('error'):
                print(f"   Error: {session_results['error']}")
            
            # Save session if requested
            if args.save_session:
                scraper.save_session(session_results)
                print(f"   💾 Session saved")
            
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
        # CRITICAL: Always ensure cleanup, even if main() is interrupted
        if scraper:
            try:
                print("\n🧹 Cleaning up...")
                scraper.close()
                print("✅ Cleanup completed")
            except Exception as cleanup_error:
                print(f"⚠️  Error during cleanup: {cleanup_error}")
                logger = logging.getLogger('cv_scraper')
                logger.error(f"Cleanup error: {cleanup_error}")
        else:
            print("✅ No cleanup needed")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 