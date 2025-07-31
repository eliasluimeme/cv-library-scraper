"""
Configuration loader for CV-Library Scraper.
Handles loading configuration from YAML files and environment variables.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .settings import Settings


class ConfigLoader:
    """Loads and manages configuration from multiple sources."""
    
    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_path: Path to YAML configuration file
            env_file: Path to .env file
        """
        self.config_path = config_path or "config/config.yaml"
        self.env_file = env_file or ".env"
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        self._load_env_file()
        
    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            self.logger.info(f"Loaded environment variables from {self.env_file}")
        else:
            self.logger.warning(f"Environment file {self.env_file} not found")
    
    def load_yaml_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Dictionary containing configuration data
        """
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                self.logger.warning(f"Config file {self.config_path} not found, using defaults")
                return {}
            
            with open(config_file, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                self.logger.info(f"Loaded configuration from {self.config_path}")
                return config_data or {}
                
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML config file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading config file: {e}")
            raise
    
    def create_settings(self) -> Settings:
        """
        Create Settings object with configuration from all sources.
        
        Returns:
            Configured Settings object
        """
        # Start with default settings
        settings = Settings()
        
        # Load and apply YAML configuration
        try:
            yaml_config = self.load_yaml_config()
            self._apply_yaml_config(settings, yaml_config)
        except Exception as e:
            self.logger.error(f"Failed to load YAML config: {e}")
            # Continue with defaults and environment variables only
        
        # Validate settings
        validation_errors = settings.validate()
        if validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info("Configuration loaded and validated successfully")
        return settings
    
    def _apply_yaml_config(self, settings: Settings, config: Dict[str, Any]):
        """
        Apply YAML configuration to settings object.
        
        Args:
            settings: Settings object to update
            config: Configuration dictionary from YAML
        """
        # Apply search criteria
        if 'search_criteria' in config:
            search_config = config['search_criteria']
            if 'keywords' in search_config:
                settings.search.keywords = search_config['keywords']
            if 'locations' in search_config:
                settings.search.locations = search_config['locations']
            if 'salary_range' in search_config:
                salary_range = search_config['salary_range']
                settings.search.salary_min = salary_range.get('min')
                settings.search.salary_max = salary_range.get('max')
            if 'experience_level' in search_config:
                settings.search.experience_level = search_config['experience_level']
            if 'job_type' in search_config:
                settings.search.job_type = search_config['job_type']
        
        # Apply download settings
        if 'download_settings' in config:
            download_config = config['download_settings']
            if 'max_quantity' in download_config:
                settings.download.max_quantity = download_config['max_quantity']
            if 'file_formats' in download_config:
                settings.download.file_formats = download_config['file_formats']
            if 'organize_by_keywords' in download_config:
                settings.download.organize_by_keywords = download_config['organize_by_keywords']
            if 'organize_by_date' in download_config:
                settings.download.organize_by_date = download_config['organize_by_date']
            if 'skip_duplicates' in download_config:
                settings.download.skip_duplicates = download_config['skip_duplicates']
        
        # Apply scraping settings
        if 'scraping_settings' in config:
            scraping_config = config['scraping_settings']
            if 'delay_between_requests' in scraping_config:
                delay_config = scraping_config['delay_between_requests']
                settings.scraping.delay_min = delay_config.get('min', settings.scraping.delay_min)
                settings.scraping.delay_max = delay_config.get('max', settings.scraping.delay_max)
            if 'page_load_timeout' in scraping_config:
                settings.scraping.page_load_timeout = scraping_config['page_load_timeout']
            if 'max_retries' in scraping_config:
                settings.scraping.max_retries = scraping_config['max_retries']
            if 'respect_robots_txt' in scraping_config:
                settings.scraping.respect_robots_txt = scraping_config['respect_robots_txt']
        
        # Apply browser settings
        if 'browser_settings' in config:
            browser_config = config['browser_settings']
            if 'browser_type' in browser_config:
                settings.browser.browser_type = browser_config['browser_type']
            if 'headless' in browser_config:
                settings.browser.headless = browser_config['headless']
            if 'window_size' in browser_config:
                window_size = browser_config['window_size']
                settings.browser.window_width = window_size.get('width', settings.browser.window_width)
                settings.browser.window_height = window_size.get('height', settings.browser.window_height)
            if 'user_agent' in browser_config:
                settings.browser.user_agent = browser_config['user_agent']
        
        self.logger.debug("Applied YAML configuration to settings")
    
    def save_config(self, settings: Settings, output_path: Optional[str] = None):
        """
        Save current settings to YAML file.
        
        Args:
            settings: Settings object to save
            output_path: Path to save file (defaults to config_path)
        """
        output_path = output_path or self.config_path
        
        # Convert settings to YAML-friendly format
        config_data = {
            'search_criteria': {
                'keywords': settings.search.keywords,
                'locations': settings.search.locations,
                'salary_range': {
                    'min': settings.search.salary_min,
                    'max': settings.search.salary_max
                },
                'experience_level': settings.search.experience_level,
                'job_type': settings.search.job_type
            },
            'download_settings': {
                'max_quantity': settings.download.max_quantity,
                'file_formats': settings.download.file_formats,
                'organize_by_keywords': settings.download.organize_by_keywords,
                'organize_by_date': settings.download.organize_by_date,
                'skip_duplicates': settings.download.skip_duplicates
            },
            'scraping_settings': {
                'delay_between_requests': {
                    'min': settings.scraping.delay_min,
                    'max': settings.scraping.delay_max
                },
                'page_load_timeout': settings.scraping.page_load_timeout,
                'max_retries': settings.scraping.max_retries,
                'respect_robots_txt': settings.scraping.respect_robots_txt
            },
            'browser_settings': {
                'browser_type': settings.browser.browser_type,
                'headless': settings.browser.headless,
                'window_size': {
                    'width': settings.browser.window_width,
                    'height': settings.browser.window_height
                },
                'user_agent': settings.browser.user_agent
            }
        }
        
        try:
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as file:
                yaml.dump(config_data, file, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Configuration saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise 