"""
Browser Profile Manager for CV-Library scraper.
Handles persistent browser profiles to maintain complete session state.
"""

import logging
import json
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from ..config.settings import Settings


class BrowserProfileManager:
    """
    Manages persistent browser profiles to maintain complete session state.
    
    This solves the single-session policy issue by preserving the entire browser
    context (cookies, local storage, session storage, cache, etc.) between runs.
    """
    
    def __init__(self, settings: Settings):
        """Initialize profile manager."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Profile paths
        self.profiles_base_dir = Path(settings.session.session_path) / "browser_profiles"
        self.profiles_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Current profile info
        self.current_profile_name = None
        self.current_profile_path = None
        
    def get_profile_path(self, profile_name: str = "default") -> Path:
        """
        Get the path for a browser profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Path to the profile directory
        """
        profile_path = self.profiles_base_dir / f"{profile_name}_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path
    
    def create_chrome_options_with_profile(self, profile_name: str = "default") -> ChromeOptions:
        """
        Create Chrome options with persistent profile.
        
        Args:
            profile_name: Name of the profile to use
            
        Returns:
            ChromeOptions configured with persistent profile
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            self.current_profile_name = profile_name
            self.current_profile_path = profile_path
            
            chrome_options = ChromeOptions()
            
            # Core persistent profile settings
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
            chrome_options.add_argument("--profile-directory=Default")
            
            # Basic options from settings
            if self.settings.browser.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument(f"--window-size={self.settings.browser.window_width},{self.settings.browser.window_height}")
            chrome_options.add_argument(f"--user-agent={self.settings.browser.user_agent}")
            
            # Additional options for stability and stealth
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Disable various popup notifications
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-default-apps")
            
            # Session persistence options
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            
            self.logger.info(f"Created Chrome options with persistent profile: {profile_path}")
            return chrome_options
            
        except Exception as e:
            self.logger.error(f"Failed to create Chrome options with profile: {e}")
            raise
    
    def create_firefox_options_with_profile(self, profile_name: str = "default") -> FirefoxOptions:
        """
        Create Firefox options with persistent profile.
        
        Args:
            profile_name: Name of the profile to use
            
        Returns:
            FirefoxOptions configured with persistent profile
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            self.current_profile_name = profile_name
            self.current_profile_path = profile_path
            
            firefox_options = FirefoxOptions()
            
            # Set persistent profile
            firefox_options.add_argument("-profile")
            firefox_options.add_argument(str(profile_path))
            
            if self.settings.browser.headless:
                firefox_options.add_argument("--headless")
            
            firefox_options.add_argument(f"--width={self.settings.browser.window_width}")
            firefox_options.add_argument(f"--height={self.settings.browser.window_height}")
            
            # Set user agent
            firefox_options.set_preference("general.useragent.override", self.settings.browser.user_agent)
            
            # Additional privacy and security preferences
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference('useAutomationExtension', False)
            
            self.logger.info(f"Created Firefox options with persistent profile: {profile_path}")
            return firefox_options
            
        except Exception as e:
            self.logger.error(f"Failed to create Firefox options with profile: {e}")
            raise
    
    def save_session_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Save additional session metadata.
        
        Args:
            metadata: Dictionary containing session metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.current_profile_path:
                self.logger.warning("No active profile path")
                return False
            
            metadata_file = self.current_profile_path / "session_metadata.json"
            metadata_with_timestamp = {
                **metadata,
                'timestamp': time.time(),
                'profile_name': self.current_profile_name
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_with_timestamp, f, indent=2)
            
            self.logger.info(f"Session metadata saved to {metadata_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save session metadata: {e}")
            return False
    
    def load_session_metadata(self, profile_name: str = "default") -> Optional[Dict[str, Any]]:
        """
        Load session metadata for a profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Dictionary with session metadata or None if not found
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            metadata_file = profile_path / "session_metadata.json"
            
            if not metadata_file.exists():
                self.logger.info(f"No session metadata found for profile: {profile_name}")
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Check if metadata is too old (24 hours)
            if time.time() - metadata.get('timestamp', 0) > 86400:
                self.logger.info("Session metadata is too old, treating as invalid")
                return None
            
            self.logger.info(f"Session metadata loaded for profile: {profile_name}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to load session metadata: {e}")
            return None
    
    def clear_profile(self, profile_name: str = "default") -> bool:
        """
        Clear a browser profile completely.
        
        Args:
            profile_name: Name of the profile to clear
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            
            if profile_path.exists():
                # Remove the entire profile directory
                shutil.rmtree(profile_path)
                self.logger.info(f"Profile cleared: {profile_path}")
                
                # Recreate empty directory
                profile_path.mkdir(parents=True, exist_ok=True)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear profile {profile_name}: {e}")
            return False
    
    def list_profiles(self) -> list:
        """
        List all available browser profiles.
        
        Returns:
            List of profile names
        """
        try:
            profiles = []
            if self.profiles_base_dir.exists():
                for profile_dir in self.profiles_base_dir.iterdir():
                    if profile_dir.is_dir() and profile_dir.name.endswith("_profile"):
                        profile_name = profile_dir.name.replace("_profile", "")
                        profiles.append(profile_name)
            
            self.logger.info(f"Found {len(profiles)} profiles: {profiles}")
            return profiles
            
        except Exception as e:
            self.logger.error(f"Failed to list profiles: {e}")
            return []
    
    def backup_profile(self, profile_name: str = "default", backup_name: str = None) -> bool:
        """
        Create a backup of a browser profile.
        
        Args:
            profile_name: Name of the profile to backup
            backup_name: Name for the backup (auto-generated if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            
            if backup_name is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{profile_name}_backup_{timestamp}"
            
            backup_path = self.profiles_base_dir / f"{backup_name}_profile"
            
            if profile_path.exists():
                shutil.copytree(profile_path, backup_path)
                self.logger.info(f"Profile backed up: {profile_path} -> {backup_path}")
                return True
            else:
                self.logger.warning(f"Profile not found for backup: {profile_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to backup profile {profile_name}: {e}")
            return False
    
    def restore_profile(self, backup_name: str, target_profile_name: str = "default") -> bool:
        """
        Restore a browser profile from backup.
        
        Args:
            backup_name: Name of the backup to restore
            target_profile_name: Name for the restored profile
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = self.profiles_base_dir / f"{backup_name}_profile"
            target_path = self.get_profile_path(target_profile_name)
            
            if not backup_path.exists():
                self.logger.error(f"Backup not found: {backup_path}")
                return False
            
            # Clear target profile first
            if target_path.exists():
                shutil.rmtree(target_path)
            
            # Copy backup to target
            shutil.copytree(backup_path, target_path)
            self.logger.info(f"Profile restored: {backup_path} -> {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore profile from {backup_name}: {e}")
            return False
    
    def get_profile_info(self, profile_name: str = "default") -> Dict[str, Any]:
        """
        Get information about a browser profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Dictionary with profile information
        """
        try:
            profile_path = self.get_profile_path(profile_name)
            
            info = {
                'name': profile_name,
                'path': str(profile_path),
                'exists': profile_path.exists(),
                'size_mb': 0,
                'last_modified': None,
                'has_metadata': False
            }
            
            if profile_path.exists():
                # Calculate total size
                total_size = sum(f.stat().st_size for f in profile_path.rglob('*') if f.is_file())
                info['size_mb'] = round(total_size / (1024 * 1024), 2)
                
                # Get last modified time
                info['last_modified'] = profile_path.stat().st_mtime
                
                # Check for metadata
                metadata_file = profile_path / "session_metadata.json"
                info['has_metadata'] = metadata_file.exists()
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get profile info for {profile_name}: {e}")
            return {'name': profile_name, 'error': str(e)} 