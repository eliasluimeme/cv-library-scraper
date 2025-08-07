"""
Settings class for CV-Library Scraper configuration management.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class ScrapingSettings:
    """Configuration for scraping behavior."""
    delay_min: int = 2
    delay_max: int = 5
    page_load_timeout: int = 30
    max_retries: int = 3
    respect_robots_txt: bool = True
    requests_per_minute: int = 10
    exponential_backoff: bool = True


@dataclass
class BrowserProfile:
    """Browser profile settings for session persistence."""
    enable_persistent_profile: bool = True
    profile_name: str = "default"
    auto_backup: bool = True
    backup_on_login: bool = True
    clear_on_logout: bool = False
    max_profile_age_hours: int = 24
    max_profile_size_mb: int = 500

@dataclass
class Browser:
    """Browser configuration settings."""
    browser_type: str = "chrome"
    headless: bool = True
    window_width: int = 1920
    window_height: int = 1080
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    timeout: int = 30
    
    # Profile settings
    profile: BrowserProfile = field(default_factory=BrowserProfile)


@dataclass
class SearchCriteria:
    """Configuration for search parameters."""
    keywords: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_level: Optional[str] = None
    job_type: Optional[str] = None


@dataclass
class DownloadSettings:
    """Configuration for download behavior."""
    max_quantity: int = 100
    file_formats: List[str] = field(default_factory=lambda: ["pdf", "doc", "docx"])
    organize_by_keywords: bool = True
    organize_by_date: bool = True
    skip_duplicates: bool = True
    download_path: str = "./downloaded_cvs/"


@dataclass
class LoggingSettings:
    """Configuration for logging."""
    log_level: str = "INFO"
    log_to_file: bool = True
    log_path: str = "./logs/"
    max_log_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class SessionSettings:
    """Configuration for session management."""
    session_timeout: int = 3600
    save_session: bool = True
    session_path: str = "./sessions/"


class Settings:
    """Main settings class that aggregates all configuration."""
    
    def __init__(self):
        self.credentials = self._load_credentials()
        self.scraping = ScrapingSettings()
        self.browser = Browser()
        self.search = SearchCriteria()
        self.download = DownloadSettings()
        self.logging = LoggingSettings()
        self.session = SessionSettings()
        
        # Update from environment variables
        self._update_from_env()
        
    def _load_credentials(self) -> Dict[str, str]:
        """Load credentials from environment variables."""
        return {
            'username': os.getenv('CV_LIBRARY_USERNAME', ''),
            'password': os.getenv('CV_LIBRARY_PASSWORD', '')
        }
    
    def _update_from_env(self):
        """Update settings from environment variables."""
        # Download settings
        self.download.download_path = os.getenv('DOWNLOAD_PATH', self.download.download_path)
        self.download.max_quantity = int(os.getenv('MAX_DOWNLOADS_PER_SESSION', self.download.max_quantity))
        
        # Scraping settings
        self.scraping.delay_min = int(os.getenv('DELAY_MIN_SECONDS', self.scraping.delay_min))
        self.scraping.delay_max = int(os.getenv('DELAY_MAX_SECONDS', self.scraping.delay_max))
        self.scraping.requests_per_minute = int(os.getenv('REQUESTS_PER_MINUTE', self.scraping.requests_per_minute))
        self.scraping.exponential_backoff = os.getenv('EXPONENTIAL_BACKOFF', 'true').lower() == 'true'
        
        # Browser settings
        self.browser.browser_type = os.getenv('BROWSER', self.browser.browser_type)
        self.browser.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.browser.timeout = int(os.getenv('BROWSER_TIMEOUT', self.browser.timeout))
        
        # Browser profile settings
        self.browser.profile.profile_name = os.getenv('BROWSER_PROFILE', self.browser.profile.profile_name)
        
        # Logging settings
        self.logging.log_level = os.getenv('LOG_LEVEL', self.logging.log_level)
        self.logging.log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
        self.logging.log_path = os.getenv('LOG_PATH', self.logging.log_path)
        
        # Session settings
        self.session.session_timeout = int(os.getenv('SESSION_TIMEOUT', self.session.session_timeout))
        self.session.save_session = os.getenv('SAVE_SESSION', 'true').lower() == 'true'
        self.session.session_path = os.getenv('SESSION_PATH', self.session.session_path)
    
    def validate(self) -> List[str]:
        """Validate settings and return list of validation errors."""
        errors = []
        
        # Validate credentials
        if not self.credentials['username']:
            errors.append("CV_LIBRARY_USERNAME is required")
        if not self.credentials['password']:
            errors.append("CV_LIBRARY_PASSWORD is required")
        
        # Validate paths
        try:
            Path(self.download.download_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Invalid download path: {e}")
        
        try:
            Path(self.logging.log_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Invalid log path: {e}")
        
        try:
            Path(self.session.session_path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Invalid session path: {e}")
        
        # Validate numeric settings
        if self.scraping.delay_min < 0 or self.scraping.delay_max < 0:
            errors.append("Delay values must be non-negative")
        if self.scraping.delay_min > self.scraping.delay_max:
            errors.append("Minimum delay cannot be greater than maximum delay")
        if self.download.max_quantity <= 0:
            errors.append("Max downloads per session must be positive")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization."""
        return {
            'scraping': self.scraping.__dict__,
            'browser': self.browser.__dict__,
            'search': self.search.__dict__,
            'download': self.download.__dict__,
            'logging': self.logging.__dict__,
            'session': self.session.__dict__
        } 