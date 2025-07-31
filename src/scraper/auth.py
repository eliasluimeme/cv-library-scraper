"""
Authentication manager for CV-Library scraper.
Handles login, session management, and credential validation.
"""

import logging
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

from ..config.settings import Settings
from .utils import WebDriverUtils, RateLimiter


class AuthenticationManager:
    """
    Manages authentication with CV-Library recruiter portal.
    """
    
    # CV-Library URLs and selectors
    BASE_URL = "https://www.cv-library.co.uk"
    LOGIN_URL = "https://www.cv-library.co.uk/recruiters/login"
    DASHBOARD_URL = "https://www.cv-library.co.uk/recruiters/dashboard"
    
    # Login form selectors (may need adjustment based on actual site)
    USERNAME_SELECTOR = "input[name='email'], input[type='email'], #email, #username"
    PASSWORD_SELECTOR = "input[name='password'], input[type='password'], #password"
    LOGIN_BUTTON_SELECTOR = "button[type='submit'], input[type='submit'], .login-button, .btn-login"
    
    # Success/failure detection selectors
    DASHBOARD_INDICATORS = [
        ".dashboard", "#dashboard", ".recruiter-dashboard",
        "text='Dashboard'", "text='Welcome'", ".user-menu"
    ]
    ERROR_INDICATORS = [
        ".error", ".alert-danger", ".login-error", 
        "text='Invalid'", "text='Error'", "text='Failed'"
    ]
    
    def __init__(self, settings: Settings):
        """Initialize authentication manager."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.is_authenticated = False
        self.session_cookies = {}
        self.rate_limiter = RateLimiter(
            min_delay=settings.scraping.delay_min,
            max_delay=settings.scraping.delay_max,
            requests_per_minute=settings.scraping.requests_per_minute
        )
        
        # Session persistence
        self.session_file = Path(settings.session.session_path) / "auth_session.json"
        
    def _setup_webdriver(self) -> bool:
        """
        Set up WebDriver based on configuration.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Setting up {self.settings.browser.browser_type} WebDriver")
            
            if self.settings.browser.browser_type.lower() == "chrome":
                return self._setup_chrome_driver()
            elif self.settings.browser.browser_type.lower() == "firefox":
                return self._setup_firefox_driver()
            else:
                self.logger.error(f"Unsupported browser: {self.settings.browser.browser_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}")
            return False
    
    def _setup_chrome_driver(self) -> bool:
        """Setup Chrome WebDriver with appropriate options."""
        try:
            chrome_options = ChromeOptions()
            
            # Basic options
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
            
            # Install and setup ChromeDriver
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.set_page_load_timeout(self.settings.browser.timeout)
            self.driver.implicitly_wait(10)
            
            self.logger.info("Chrome WebDriver setup successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Chrome WebDriver setup failed: {e}")
            return False
    
    def _setup_firefox_driver(self) -> bool:
        """Setup Firefox WebDriver with appropriate options."""
        try:
            firefox_options = FirefoxOptions()
            
            if self.settings.browser.headless:
                firefox_options.add_argument("--headless")
            
            firefox_options.add_argument(f"--width={self.settings.browser.window_width}")
            firefox_options.add_argument(f"--height={self.settings.browser.window_height}")
            
            # Set user agent
            firefox_options.set_preference("general.useragent.override", self.settings.browser.user_agent)
            
            # Additional privacy and security preferences
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference('useAutomationExtension', False)
            
            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            
            self.driver.set_page_load_timeout(self.settings.browser.timeout)
            self.driver.implicitly_wait(10)
            
            self.logger.info("Firefox WebDriver setup successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Firefox WebDriver setup failed: {e}")
            return False
    
    def _navigate_to_login_page(self) -> bool:
        """
        Navigate to CV-Library login page.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Navigating to CV-Library login page")
            self.rate_limiter.wait_if_needed()
            
            self.driver.get(self.LOGIN_URL)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Verify we're on the login page
            current_url = self.driver.current_url.lower()
            if "login" in current_url or "signin" in current_url:
                self.logger.info("Successfully navigated to login page")
                self.rate_limiter.on_success()
                return True
            else:
                self.logger.warning(f"Unexpected page URL: {current_url}")
                return False
                
        except TimeoutException:
            self.logger.error("Timeout while loading login page")
            self.rate_limiter.on_error()
            return False
        except Exception as e:
            self.logger.error(f"Failed to navigate to login page: {e}")
            self.rate_limiter.on_error()
            return False
    
    def _find_login_form_elements(self) -> tuple:
        """
        Find username, password, and submit button elements.
        
        Returns:
            Tuple of (username_element, password_element, submit_button) or (None, None, None)
        """
        try:
            # Try multiple selectors for username field
            username_element = None
            for selector in self.USERNAME_SELECTOR.split(", "):
                try:
                    username_element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    self.logger.debug(f"Found username field with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not username_element:
                self.logger.error("Could not find username/email field")
                return None, None, None
            
            # Try multiple selectors for password field
            password_element = None
            for selector in self.PASSWORD_SELECTOR.split(", "):
                try:
                    password_element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    self.logger.debug(f"Found password field with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not password_element:
                self.logger.error("Could not find password field")
                return None, None, None
            
            # Try multiple selectors for submit button
            submit_button = None
            for selector in self.LOGIN_BUTTON_SELECTOR.split(", "):
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    self.logger.debug(f"Found submit button with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                self.logger.error("Could not find submit button")
                return None, None, None
            
            return username_element, password_element, submit_button
            
        except Exception as e:
            self.logger.error(f"Error finding login form elements: {e}")
            return None, None, None
    
    def _fill_login_form(self, username: str, password: str) -> bool:
        """
        Fill in the login form with credentials.
        
        Args:
            username: Username/email for login
            password: Password for login
            
        Returns:
            True if successful, False otherwise
        """
        try:
            username_element, password_element, submit_button = self._find_login_form_elements()
            
            if not all([username_element, password_element, submit_button]):
                return False
            
            # Clear and fill username
            username_element.clear()
            time.sleep(0.5)
            username_element.send_keys(username)
            self.logger.debug("Username entered")
            
            # Clear and fill password
            password_element.clear()
            time.sleep(0.5)
            password_element.send_keys(password)
            self.logger.debug("Password entered")
            
            # Small delay before submitting
            time.sleep(1)
            
            # Submit the form
            WebDriverUtils.safe_click(self.driver, submit_button)
            self.logger.info("Login form submitted")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill login form: {e}")
            return False
    
    def _detect_login_result(self) -> str:
        """
        Detect if login was successful or failed.
        
        Returns:
            'success', 'failed', or 'unknown'
        """
        try:
            # Wait a bit for page to process
            time.sleep(3)
            
            # Check for success indicators
            for indicator in self.DASHBOARD_INDICATORS:
                try:
                    if indicator.startswith("text="):
                        # Text-based detection
                        text_to_find = indicator.replace("text=", "")
                        if text_to_find.lower() in self.driver.page_source.lower():
                            self.logger.info(f"Login success detected: found text '{text_to_find}'")
                            return "success"
                    else:
                        # CSS selector-based detection
                        element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                        if element:
                            self.logger.info(f"Login success detected: found element '{indicator}'")
                            return "success"
                except NoSuchElementException:
                    continue
            
            # Check for error indicators
            for indicator in self.ERROR_INDICATORS:
                try:
                    if indicator.startswith("text="):
                        # Text-based detection
                        text_to_find = indicator.replace("text=", "")
                        if text_to_find.lower() in self.driver.page_source.lower():
                            self.logger.error(f"Login failure detected: found text '{text_to_find}'")
                            return "failed"
                    else:
                        # CSS selector-based detection
                        element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                        if element and element.is_displayed():
                            self.logger.error(f"Login failure detected: found element '{indicator}'")
                            return "failed"
                except NoSuchElementException:
                    continue
            
            # Check URL for dashboard or similar
            current_url = self.driver.current_url.lower()
            if any(word in current_url for word in ["dashboard", "recruiter", "home", "profile"]):
                self.logger.info(f"Login success detected: URL changed to {current_url}")
                return "success"
            
            # Check if still on login page (indicates failure)
            if any(word in current_url for word in ["login", "signin", "auth"]):
                self.logger.error(f"Login failure detected: still on login page {current_url}")
                return "failed"
            
            self.logger.warning("Login result unclear - could not detect success or failure")
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Error detecting login result: {e}")
            return "unknown"
    
    def _save_session_cookies(self):
        """Save current session cookies for later use."""
        try:
            cookies = self.driver.get_cookies()
            session_data = {
                'cookies': cookies,
                'url': self.driver.current_url,
                'timestamp': time.time()
            }
            
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            self.logger.info(f"Session cookies saved to {self.session_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session cookies: {e}")
    
    def _load_session_cookies(self) -> bool:
        """Load and apply saved session cookies."""
        try:
            if not self.session_file.exists():
                self.logger.info("No saved session file found")
                return False
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session is too old (1 hour)
            if time.time() - session_data.get('timestamp', 0) > 3600:
                self.logger.info("Saved session is too old, will perform fresh login")
                return False
            
            # Navigate to CV-Library first
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            
            # Apply cookies
            for cookie in session_data.get('cookies', []):
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    self.logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")
            
            # Navigate to dashboard to verify session
            self.driver.get(self.DASHBOARD_URL)
            time.sleep(3)
            
            # Check if we're successfully logged in
            if self._detect_login_result() == "success":
                self.logger.info("Successfully restored session from cookies")
                return True
            else:
                self.logger.info("Saved session cookies are invalid")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load session cookies: {e}")
            return False
    
    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Login to CV-Library.
        
        Args:
            username: CV-Library username (optional, will use settings if not provided)
            password: CV-Library password (optional, will use settings if not provided)
            
        Returns:
            True if authentication successful, False otherwise
        """
        # Use provided credentials or fallback to settings
        username = username or self.settings.credentials.get('username')
        password = password or self.settings.credentials.get('password')
        
        if not username or not password:
            self.logger.error("Username and password are required for authentication")
            return False
        
        try:
            # Setup WebDriver if not already done
            if not self.driver:
                if not self._setup_webdriver():
                    return False
            
            # Try to restore previous session first
            if self._load_session_cookies():
                self.is_authenticated = True
                return True
            
            # Fresh login required
            self.logger.info("Performing fresh login to CV-Library")
            
            # Navigate to login page
            if not self._navigate_to_login_page():
                return False
            
            # Fill and submit login form
            if not self._fill_login_form(username, password):
                return False
            
            # Wait and detect login result
            time.sleep(5)  # Give time for page to process
            
            login_result = self._detect_login_result()
            
            if login_result == "success":
                self.logger.info("Login successful!")
                self.is_authenticated = True
                self._save_session_cookies()
                self.rate_limiter.on_success()
                return True
            elif login_result == "failed":
                self.logger.error("Login failed - check credentials")
                self.is_authenticated = False
                self.rate_limiter.on_error()
                return False
            else:
                self.logger.warning("Login result unclear - assuming failure")
                self.is_authenticated = False
                return False
                
        except Exception as e:
            self.logger.error(f"Login process failed: {e}")
            self.is_authenticated = False
            self.rate_limiter.on_error()
            return False
    
    def logout(self) -> bool:
        """
        Logout from CV-Library.
        
        Returns:
            True if logout successful, False otherwise
        """
        try:
            if self.driver:
                # Try to find and click logout link
                logout_selectors = [
                    "a[href*='logout']", ".logout", "#logout",
                    "text='Logout'", "text='Sign out'", "text='Log out'"
                ]
                
                for selector in logout_selectors:
                    try:
                        if selector.startswith("text="):
                            # Text-based detection would need more complex implementation
                            continue
                        else:
                            logout_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if logout_element.is_displayed():
                                WebDriverUtils.safe_click(self.driver, logout_element)
                                self.logger.info("Logout link clicked")
                                time.sleep(2)
                                break
                    except NoSuchElementException:
                        continue
                
                # Clear cookies and session data
                self.driver.delete_all_cookies()
                if self.session_file.exists():
                    self.session_file.unlink()
                
                self.is_authenticated = False
                self.logger.info("Logout completed")
                return True
            
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            
        self.is_authenticated = False
        return True  # Consider logout successful even if there were errors
    
    def verify_session(self) -> bool:
        """
        Verify current session is still valid.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            if not self.driver or not self.is_authenticated:
                return False
            
            # Navigate to dashboard to check session
            self.rate_limiter.wait_if_needed()
            self.driver.get(self.DASHBOARD_URL)
            time.sleep(3)
            
            # Check if we're still logged in
            result = self._detect_login_result()
            if result == "success":
                self.logger.debug("Session verification successful")
                self.rate_limiter.on_success()
                return True
            else:
                self.logger.warning("Session verification failed - need to re-authenticate")
                self.is_authenticated = False
                self.rate_limiter.on_error()
                return False
                
        except Exception as e:
            self.logger.error(f"Session verification failed: {e}")
            self.is_authenticated = False
            return False
    
    def close(self):
        """Clean up WebDriver resources."""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.logger.info("WebDriver closed")
        except Exception as e:
            self.logger.error(f"Error closing WebDriver: {e}")
    
    def get_driver(self):
        """Get the current WebDriver instance."""
        return self.driver 