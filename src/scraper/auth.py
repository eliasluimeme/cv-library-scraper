"""
Authentication manager for CV-Library scraper.
Handles login, session management, and credential validation with persistent browser profiles.
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
from .browser_profile import BrowserProfileManager


class AuthenticationManager:
    """
    Manages authentication with CV-Library recruiter portal using persistent browser profiles.
    
    This approach maintains complete browser session state (cookies, local storage, cache, etc.)
    to comply with single-session policies and avoid repeated authentication challenges.
    """
    
    # CV-Library URLs and selectors
    BASE_URL = "https://www.cv-library.co.uk"
    LOGIN_URL = "https://www.cv-library.co.uk/recruiter/login"
    DASHBOARD_URL = "https://www.cv-library.co.uk/recruiter/"
    RECRUITER_URL = "https://www.cv-library.co.uk/recruiter"
    
    # Login form selectors (updated for actual CV-Library site)
    USERNAME_SELECTOR = "input[name='email'], input[type='email'], #email, #username, input[placeholder*='email'], input[placeholder*='Email']"
    PASSWORD_SELECTOR = "input[name='password'], input[type='password'], #password, input[placeholder*='password'], input[placeholder*='Password']"
    LOGIN_BUTTON_SELECTOR = "button[type='submit'], input[type='submit'], .login-button, .btn-login, button:contains('Login'), button:contains('Sign in'), .btn-primary"
    
    # Success/failure detection selectors
    DASHBOARD_INDICATORS = [
        ".dashboard", "#dashboard", ".recruiter-dashboard",
        "text='Dashboard'", "text='Welcome'", ".user-menu", ".nav-user",
        "text='CV Search'", "text='My Account'", ".main-nav"
    ]
    ERROR_INDICATORS = [
        ".error", ".alert-danger", ".login-error", ".form-error",
        "text='Invalid'", "text='Error'", "text='Failed'", "text='incorrect'",
        ".alert-error", ".error-message"
    ]
    
    def __init__(self, settings: Settings):
        """Initialize authentication manager with profile support."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.is_authenticated = False
        
        # Initialize browser profile manager
        self.profile_manager = BrowserProfileManager(settings)
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            min_delay=settings.scraping.delay_min,
            max_delay=settings.scraping.delay_max,
            requests_per_minute=settings.scraping.requests_per_minute
        )
        
        # Session persistence (legacy cookie support)
        self.session_file = Path(settings.session.session_path) / "auth_session.json"
        self.session_cookies = {}
        
    def _setup_webdriver(self) -> bool:
        """
        Set up WebDriver with optimized performance and minimal logging.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we already have a working driver
            if self.driver:
                try:
                    # Test if the existing driver is still responsive
                    self.driver.current_url
                    self.logger.info("Reusing existing WebDriver instance")
                    return True
                except Exception as e:
                    self.logger.info(f"Existing WebDriver not responsive: {e}, creating new one")
                    # Close the old driver properly
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
            
            # Load session metadata silently
            session_metadata = self.profile_manager.load_session_metadata()
            
            # Get browser options with persistent profile
            options = self.profile_manager.create_chrome_options_with_profile("default")
            
            # Use cached ChromeDriver path (this should be fast now)
            driver_path = self._get_chromedriver_path()
            if not driver_path:
                return False
            
            # Initialize WebDriver with minimal logging
            import logging
            webdriver_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
            webdriver_logger.setLevel(logging.CRITICAL)
            
            service = ChromeService(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Apply stealth settings
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebDriver setup failed: {e}")
            return False
    
    def _get_chromedriver_path(self) -> Optional[str]:
        """Get ChromeDriver path optimized for Docker environment."""
        try:
            import logging
            import os
            from pathlib import Path
            
            # In Docker, prefer system ChromeDriver first
            system_chromedriver = "/usr/local/bin/chromedriver"
            if Path(system_chromedriver).exists() and os.access(system_chromedriver, os.X_OK):
                self.logger.info(f"Using system ChromeDriver: {system_chromedriver}")
                return system_chromedriver
            
            # Fallback to other system locations
            system_paths = [
                "/usr/bin/chromedriver",
                "/opt/homebrew/bin/chromedriver",
                "/usr/local/bin/chromedriver"
            ]
            
            for path in system_paths:
                if Path(path).exists() and os.access(path, os.X_OK):
                    self.logger.info(f"Using system ChromeDriver: {path}")
                    return path
            
            # Check if we have a cached path that still works
            cache_file = Path.home() / '.cv_scraper_chromedriver_cache'
            if cache_file.exists():
                try:
                    cached_path = cache_file.read_text().strip()
                    if Path(cached_path).exists() and os.access(cached_path, os.X_OK):
                        if Path(cached_path).stat().st_size > 1000:
                            return cached_path
                except Exception:
                    pass
            
            # If not in Docker or system ChromeDriver not found, try webdriver-manager
            try:
                logging.getLogger('WDM').setLevel(logging.WARNING)
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                self.logger.info(f"ChromeDriver path returned by manager: {driver_path}")
                
                # Apply the path-fixing logic for webdriver-manager
                if "THIRD_PARTY_NOTICES" in driver_path:
                    self.logger.info("Fixing webdriver-manager path issue...")
                    driver_dir = Path(driver_path).parent
                    
                    possible_paths = [
                        driver_dir / "chromedriver",
                        driver_dir / "chromedriver.exe",
                    ]
                    
                    for possible_path in possible_paths:
                        if possible_path.exists():
                            if not os.access(possible_path, os.X_OK):
                                try:
                                    os.chmod(possible_path, 0o755)
                                    self.logger.info(f"Made ChromeDriver executable: {possible_path}")
                                except Exception as chmod_error:
                                    self.logger.warning(f"Could not make ChromeDriver executable: {chmod_error}")
                                    continue
                            
                            if os.access(possible_path, os.X_OK):
                                fixed_path = str(possible_path)
                                cache_file.write_text(fixed_path)
                                self.logger.info(f"Found actual ChromeDriver at: {fixed_path}")
                                return fixed_path
                    else:
                        # Search recursively
                        for chromedriver_file in driver_dir.rglob("chromedriver*"):
                            if (chromedriver_file.is_file() and 
                                "THIRD_PARTY" not in str(chromedriver_file)):
                                
                                if not os.access(chromedriver_file, os.X_OK):
                                    try:
                                        os.chmod(chromedriver_file, 0o755)
                                        self.logger.info(f"Made ChromeDriver executable: {chromedriver_file}")
                                    except Exception as chmod_error:
                                        self.logger.warning(f"Could not make ChromeDriver executable: {chmod_error}")
                                        continue
                                
                                if os.access(chromedriver_file, os.X_OK):
                                    fixed_path = str(chromedriver_file)
                                    cache_file.write_text(fixed_path)
                                    self.logger.info(f"Found ChromeDriver recursively at: {fixed_path}")
                                    return fixed_path
                        
                        self.logger.warning(f"Could not find actual chromedriver executable in {driver_dir}")
                
                # Verify the driver path is actually an executable
                if not os.path.isfile(driver_path) or not os.access(driver_path, os.X_OK):
                    self.logger.warning(f"ChromeDriver at {driver_path} is not executable")
                    raise Exception(f"ChromeDriver at {driver_path} is not executable")
                
                cache_file.write_text(driver_path)
                return driver_path
                
            except Exception as e:
                self.logger.warning(f"ChromeDriverManager failed: {e}")
            
            self.logger.error("Could not find ChromeDriver")
            return None
            
        except Exception as e:
            self.logger.error(f"ChromeDriver setup failed: {e}")
            return None
    
    def _is_firefox_available(self) -> bool:
        """Check if Firefox browser is installed."""
        import os
        import shutil
        
        # Check common Firefox locations on macOS
        firefox_paths = [
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            "/Applications/Firefox.app/Contents/MacOS/firefox-bin"
        ]
        
        # Check if Firefox is in PATH
        if shutil.which("firefox"):
            return True
        
        # Check common installation paths
        for path in firefox_paths:
            if os.path.exists(path):
                return True
        
        return False
    
    def _setup_chrome_driver_with_profile(self, profile_name: str) -> bool:
        """Setup Chrome WebDriver with persistent profile."""
        try:
            # Use profile manager to create Chrome options
            if self.settings.browser.profile.enable_persistent_profile:
                chrome_options = self.profile_manager.create_chrome_options_with_profile(profile_name)
                self.logger.info(f"Using persistent profile: {profile_name}")
            else:
                chrome_options = self._create_basic_chrome_options()
                self.logger.info("Using temporary profile (persistent profiles disabled)")
            
            # Try to get ChromeDriver with better error handling
            try:
                self.logger.info("Installing/updating ChromeDriver...")
                driver_path = ChromeDriverManager().install()
                self.logger.info(f"ChromeDriver path returned by manager: {driver_path}")
                
                # Fix the common webdriver-manager bug where it returns the wrong file
                import os
                from pathlib import Path
                
                # If the path points to THIRD_PARTY_NOTICES, find the actual chromedriver
                if "THIRD_PARTY_NOTICES" in driver_path:
                    self.logger.info("Fixing webdriver-manager path issue...")
                    driver_dir = Path(driver_path).parent
                    
                    # Look for the actual chromedriver executable
                    possible_paths = [
                        driver_dir / "chromedriver",
                        driver_dir / "chromedriver.exe",
                    ]
                    
                    for possible_path in possible_paths:
                        if possible_path.exists() and os.access(possible_path, os.X_OK):
                            driver_path = str(possible_path)
                            self.logger.info(f"Found actual ChromeDriver at: {driver_path}")
                            break
                    else:
                        # If not found in the same directory, search recursively
                        for chromedriver_file in driver_dir.rglob("chromedriver*"):
                            if chromedriver_file.is_file() and "THIRD_PARTY" not in str(chromedriver_file) and os.access(chromedriver_file, os.X_OK):
                                driver_path = str(chromedriver_file)
                                self.logger.info(f"Found ChromeDriver recursively at: {driver_path}")
                                break
                        else:
                            raise Exception(f"Could not find actual chromedriver executable in {driver_dir}")
                
                # Verify the driver path is actually an executable
                if not os.path.isfile(driver_path) or not os.access(driver_path, os.X_OK):
                    raise Exception(f"ChromeDriver at {driver_path} is not executable")
                
                service = ChromeService(driver_path)
                
            except Exception as driver_error:
                self.logger.warning(f"ChromeDriverManager failed: {driver_error}")
                self.logger.info("Trying to use system ChromeDriver...")
                
                # Try to use system chromedriver
                try:
                    service = ChromeService()  # Let Selenium find chromedriver in PATH
                except Exception as system_error:
                    self.logger.error(f"System ChromeDriver also failed: {system_error}")
                    raise Exception("Could not find or install ChromeDriver")
            
            # Create the Chrome driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Remove webdriver property for stealth
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as stealth_error:
                self.logger.debug(f"Could not apply stealth script: {stealth_error}")
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.settings.browser.timeout)
            self.driver.implicitly_wait(10)
            
            self.logger.info("Chrome WebDriver with persistent profile setup successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Chrome WebDriver setup failed: {e}")
            self.logger.info("You may need to install Chrome browser or try Firefox instead")
            return False
    
    def _setup_firefox_driver_with_profile(self, profile_name: str) -> bool:
        """Setup Firefox WebDriver with persistent profile."""
        try:
            # Use profile manager to create Firefox options
            if self.settings.browser.profile.enable_persistent_profile:
                firefox_options = self.profile_manager.create_firefox_options_with_profile(profile_name)
                self.logger.info(f"Using persistent profile: {profile_name}")
            else:
                firefox_options = self._create_basic_firefox_options()
                self.logger.info("Using temporary profile (persistent profiles disabled)")
            
            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            
            self.driver.set_page_load_timeout(self.settings.browser.timeout)
            self.driver.implicitly_wait(10)
            
            self.logger.info("Firefox WebDriver with persistent profile setup successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Firefox WebDriver setup failed: {e}")
            return False
    
    def _create_basic_chrome_options(self) -> ChromeOptions:
        """Create basic Chrome options without persistent profile."""
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
        
        return chrome_options
    
    def _create_basic_firefox_options(self) -> FirefoxOptions:
        """Create basic Firefox options without persistent profile."""
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
        
        return firefox_options
    
    def _navigate_to_login_page(self) -> bool:
        """
        Navigate to CV-Library login page.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # First try to go to the recruiter page
            self.logger.info("Navigating to CV-Library recruiter page")
            self.rate_limiter.wait_if_needed()
            
            self.driver.get(self.RECRUITER_URL)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            current_url = self.driver.current_url.lower()
            self.logger.info(f"Current URL after navigating to recruiter: {current_url}")
            
            # Check if we're already logged in (on dashboard or other recruiter pages)
            if any(indicator in current_url for indicator in ["recruiter", "dashboard"]):
                # Check if this looks like a logged-in page
                page_title = self.driver.title.lower()
                page_source = self.driver.page_source.lower()
                
                # Look for indicators that we're logged in
                logged_in_indicators = [
                    "account home", "dashboard", "search cvs", "logout", "my account",
                    "recruiter portal", "cv search", "candidate search"
                ]
                
                login_indicators = [
                    "login", "sign in", "email", "password", "authenticate"
                ]
                
                logged_in_count = sum(1 for indicator in logged_in_indicators 
                                     if indicator in page_title or indicator in page_source)
                login_count = sum(1 for indicator in login_indicators 
                                 if indicator in page_title or indicator in page_source)
                
                self.logger.info(f"Page analysis - Logged in indicators: {logged_in_count}, Login indicators: {login_count}")
                
                if logged_in_count > login_count and logged_in_count >= 2:
                    self.logger.info("Appears to be already logged in based on page content")
                    self.rate_limiter.on_success()
                    return True
            
            # Check if we're already on a login page or redirected to login
            if any(word in current_url for word in ["login", "signin"]):
                self.logger.info("Already on login page")
                self.rate_limiter.on_success()
                return True
            
            # If not on login page, try to find and click login link
            login_link_selectors = [
                "a[href*='login']", ".login", "#login", "a:contains('Login')", 
                "a:contains('Sign in')", ".btn-login", "a[href*='/recruiter/login']"
            ]
            
            login_clicked = False
            for selector in login_link_selectors:
                try:
                    if ":contains(" in selector:
                        # Skip text-based selectors for now
                        continue
                    login_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if login_element.is_displayed():
                        self.logger.info(f"Found login link with selector: {selector}")
                        login_element.click()
                        time.sleep(2)
                        login_clicked = True
                        break
                except NoSuchElementException:
                    continue
            
            if not login_clicked:
                # Try direct navigation to login URL
                self.logger.info("Login link not found, navigating directly to login URL")
                self.driver.get(self.LOGIN_URL)
                time.sleep(3)
            
            # Verify we're on the login page
            current_url = self.driver.current_url.lower()
            self.logger.info(f"Final URL: {current_url}")
            
            if "login" in current_url or "signin" in current_url:
                self.logger.info("Successfully navigated to login page")
                self.rate_limiter.on_success()
                return True
            else:
                self.logger.warning(f"Unexpected page URL: {current_url}")
                # Still try to continue - maybe the page structure is different
                return True
                
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
            # Add debug information about the page
            self.logger.info("Searching for login form elements...")
            self.logger.debug(f"Page title: {self.driver.title}")
            
            # Look for all forms on the page
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            self.logger.info(f"Found {len(forms)} forms on the page")
            
            # Look for all input elements
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            self.logger.info(f"Found {len(inputs)} input elements on the page")
            
            for i, input_elem in enumerate(inputs):
                try:
                    input_type = input_elem.get_attribute("type") or "text"
                    input_name = input_elem.get_attribute("name") or "no-name"
                    input_id = input_elem.get_attribute("id") or "no-id"
                    input_placeholder = input_elem.get_attribute("placeholder") or "no-placeholder"
                    self.logger.debug(f"Input {i}: type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}")
                except Exception as e:
                    self.logger.debug(f"Could not get attributes for input {i}: {e}")
            
            # Try multiple selectors for username field
            username_element = None
            username_selectors = self.USERNAME_SELECTOR.split(", ")
            self.logger.info(f"Trying {len(username_selectors)} selectors for username field")
            
            for selector in username_selectors:
                try:
                    selector = selector.strip()
                    self.logger.debug(f"Trying username selector: {selector}")
                    username_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"Found username field with selector: {selector}")
                    break
                except NoSuchElementException:
                    self.logger.debug(f"Username selector failed: {selector}")
                    continue
            
            # If still not found, try to find by input attributes
            if not username_element:
                self.logger.info("Trying alternative username detection methods...")
                for input_elem in inputs:
                    try:
                        input_type = input_elem.get_attribute("type") or "text"
                        input_name = input_elem.get_attribute("name") or ""
                        input_placeholder = input_elem.get_attribute("placeholder") or ""
                        
                        if (input_type.lower() in ["email", "text"] and 
                            ("email" in input_name.lower() or "user" in input_name.lower() or
                             "email" in input_placeholder.lower() or "user" in input_placeholder.lower())):
                            username_element = input_elem
                            self.logger.info(f"Found username field by attributes: type={input_type}, name={input_name}")
                            break
                    except Exception:
                        continue
            
            if not username_element:
                self.logger.error("Could not find username/email field")
                return None, None, None
            
            # Try multiple selectors for password field
            password_element = None
            password_selectors = self.PASSWORD_SELECTOR.split(", ")
            self.logger.info(f"Trying {len(password_selectors)} selectors for password field")
            
            for selector in password_selectors:
                try:
                    selector = selector.strip()
                    self.logger.debug(f"Trying password selector: {selector}")
                    password_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"Found password field with selector: {selector}")
                    break
                except NoSuchElementException:
                    self.logger.debug(f"Password selector failed: {selector}")
                    continue
            
            # If still not found, try to find by input type
            if not password_element:
                self.logger.info("Trying alternative password detection methods...")
                for input_elem in inputs:
                    try:
                        input_type = input_elem.get_attribute("type") or ""
                        if input_type.lower() == "password":
                            password_element = input_elem
                            self.logger.info("Found password field by type='password'")
                            break
                    except Exception:
                        continue
            
            if not password_element:
                self.logger.error("Could not find password field")
                return None, None, None
            
            # Try multiple selectors for submit button
            submit_button = None
            submit_selectors = self.LOGIN_BUTTON_SELECTOR.split(", ")
            self.logger.info(f"Trying {len(submit_selectors)} selectors for submit button")
            
            for selector in submit_selectors:
                try:
                    selector = selector.strip()
                    if ":contains(" in selector:
                        # Skip text-based selectors for now
                        continue
                    self.logger.debug(f"Trying submit selector: {selector}")
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.logger.info(f"Found submit button with selector: {selector}")
                    break
                except NoSuchElementException:
                    self.logger.debug(f"Submit selector failed: {selector}")
                    continue
            
            # If still not found, look for buttons in the same form as the username/password
            if not submit_button:
                self.logger.info("Trying alternative submit button detection methods...")
                try:
                    # Find the form containing the username field
                    form = username_element.find_element(By.XPATH, "./ancestor::form")
                    buttons = form.find_elements(By.TAG_NAME, "button")
                    buttons.extend(form.find_elements(By.CSS_SELECTOR, "input[type='submit']"))
                    
                    for button in buttons:
                        button_type = button.get_attribute("type") or ""
                        button_text = button.text.lower()
                        if (button_type.lower() in ["submit", ""] and 
                            any(word in button_text for word in ["login", "sign", "submit", ""]) or
                            button_type.lower() == "submit"):
                            submit_button = button
                            self.logger.info(f"Found submit button in form: text='{button.text}', type='{button_type}'")
                            break
                except Exception as e:
                    self.logger.debug(f"Could not find form or buttons: {e}")
            
            if not submit_button:
                self.logger.error("Could not find submit button")
                return None, None, None
            
            self.logger.info("Successfully found all login form elements")
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
            # Wait a bit for page to process and redirect
            self.logger.info("Waiting for login result...")
            time.sleep(5)
            
            # Get current page information
            current_url = self.driver.current_url.lower()
            page_title = self.driver.title.lower()
            self.logger.info(f"After login - URL: {current_url}")
            self.logger.info(f"After login - Page title: {page_title}")
            
            # Quick check for obvious success indicators in URL
            success_url_indicators = ["dashboard", "recruiter", "home", "profile", "search", "cv-search"]
            if any(indicator in current_url for indicator in success_url_indicators):
                # Additional verification - check if we're not still on login page
                if not any(fail_indicator in current_url for fail_indicator in ["login", "signin", "auth"]):
                    self.logger.info(f"Login success detected: URL contains success indicator and not on login page")
                    return "success"
            
            # Check page title for success indicators
            success_title_indicators = ["dashboard", "recruiter", "cv library", "search", "home", "welcome"]
            if any(indicator in page_title for indicator in success_title_indicators):
                # Make sure it's not a login page title
                if not any(fail_indicator in page_title for fail_indicator in ["login", "signin", "sign in"]):
                    self.logger.info(f"Login success detected: Page title indicates success")
                    return "success"
            
            # Check for presence of login form (indicates we're still on login page)
            try:
                # Look for login form elements - if they exist, login likely failed
                login_forms = self.driver.find_elements(By.CSS_SELECTOR, "form")
                for form in login_forms:
                    form_html = form.get_attribute("innerHTML").lower()
                    if any(indicator in form_html for indicator in ["password", "email", "login", "signin"]):
                        self.logger.info("Login failure detected: Still on login page with login form")
                        return "failed"
            except Exception as e:
                self.logger.debug(f"Could not check for login form: {e}")
            
            # Check for success indicators in page elements
            for indicator in self.DASHBOARD_INDICATORS:
                try:
                    if indicator.startswith("text="):
                        # Text-based detection
                        text_to_find = indicator.replace("text=", "")
                        if text_to_find.lower() in self.driver.page_source.lower():
                            self.logger.info(f"Login success detected: found text '{text_to_find}' in page source")
                            return "success"
                    else:
                        # CSS selector-based detection
                        elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements and any(elem.is_displayed() for elem in elements):
                            self.logger.info(f"Login success detected: found visible element '{indicator}'")
                            return "success"
                except Exception as e:
                    self.logger.debug(f"Could not check success indicator '{indicator}': {e}")
                    continue
            
            # Check for error indicators
            for indicator in self.ERROR_INDICATORS:
                try:
                    if indicator.startswith("text="):
                        # Text-based detection
                        text_to_find = indicator.replace("text=", "")
                        if text_to_find.lower() in self.driver.page_source.lower():
                            self.logger.error(f"Login failure detected: found error text '{text_to_find}'")
                            return "failed"
                    else:
                        # CSS selector-based detection
                        elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements and any(elem.is_displayed() for elem in elements):
                            error_text = elements[0].text if elements[0].text else "Error element found"
                            self.logger.error(f"Login failure detected: found error element '{indicator}': {error_text}")
                            return "failed"
                except Exception as e:
                    self.logger.debug(f"Could not check error indicator '{indicator}': {e}")
                    continue
            
            # Enhanced URL-based detection
            if any(fail_indicator in current_url for fail_indicator in ["login", "signin", "auth", "error"]):
                self.logger.error(f"Login failure detected: URL indicates failure or still on login page")
                return "failed"
            
            # Check for common success page elements
            success_elements = [
                "nav", ".nav", "#nav", ".navigation", ".header-nav",
                ".user-menu", ".profile-menu", ".account-menu",
                ".search-form", ".cv-search", ".job-search",
                ".dashboard-content", ".main-content", ".recruiter-content"
            ]
            
            for selector in success_elements:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(elem.is_displayed() for elem in elements):
                        self.logger.info(f"Login success detected: found navigation/content element '{selector}'")
                        return "success"
                except Exception:
                    continue
            
            # Check page source for keywords that indicate successful login
            page_source_lower = self.driver.page_source.lower()
            
            # Success keywords
            success_keywords = [
                "dashboard", "welcome", "logout", "sign out", "my account",
                "cv search", "candidate search", "job posting", "recruiter"
            ]
            
            success_count = sum(1 for keyword in success_keywords if keyword in page_source_lower)
            
            # Failure keywords
            failure_keywords = [
                "invalid credentials", "login failed", "incorrect password",
                "email not found", "authentication failed", "please try again"
            ]
            
            failure_count = sum(1 for keyword in failure_keywords if keyword in page_source_lower)
            
            if success_count >= 2 and failure_count == 0:
                self.logger.info(f"Login success detected: page contains {success_count} success keywords")
                return "success"
            elif failure_count > 0:
                self.logger.error(f"Login failure detected: page contains {failure_count} failure keywords")
                return "failed"
            
            # Final check - if URL changed significantly from login page, assume success
            if (not any(indicator in current_url for indicator in ["login", "signin"]) and 
                "cv-library.co.uk" in current_url):
                self.logger.info("Login success detected: URL changed from login page to CV-Library domain")
                return "success"
            
            # If we get here, result is unclear
            self.logger.warning(f"Login result unclear - URL: {current_url}, Title: {page_title}")
            self.logger.warning(f"Success keywords found: {success_count}, Failure keywords found: {failure_count}")
            
            # Save page source for debugging if needed
            try:
                debug_file = self.session_file.parent / "debug_login_page.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.logger.info(f"Page source saved to {debug_file} for debugging")
            except Exception as e:
                self.logger.debug(f"Could not save debug page source: {e}")
            
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
        Ultra-fast login with persistent session support.
        
        Args:
            username: CV-Library username (optional, will use settings if not provided)
            password: CV-Library password (optional, will use settings if not provided)
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            if not self._setup_webdriver():
                return False
            
            # Quick authentication check - single URL test
            self.driver.get("https://www.cv-library.co.uk/recruiter")
            time.sleep(1)
            
            current_url = self.driver.current_url.lower()
            if "recruiter" in current_url and "login" not in current_url:
                return True  # Already authenticated
            
            # Need to login - use provided credentials or settings
            login_username = username or self.settings.credentials['username']
            login_password = password or self.settings.credentials['password']
            
            if not login_username or not login_password:
                self.logger.error("Missing credentials")
                return False
            
            # Perform fast login
            self.driver.get(self.LOGIN_URL)
            time.sleep(1)
            
            # Find and fill form quickly
            email_field = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
            )
            email_field.clear()
            email_field.send_keys(login_username)
            
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_field.clear()
            password_field.send_keys(login_password)
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            submit_button.click()
            
            # Quick success check
            time.sleep(2)
            final_url = self.driver.current_url.lower()
            success = "recruiter" in final_url and "login" not in final_url
            
            if success and self.settings.browser.profile.enable_persistent_profile:
                # Save minimal session metadata
                self._save_session_metadata({
                    'login_time': time.time(),
                    'username': login_username
                })
            
            return success
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False
    
    def _quick_auth_check(self) -> bool:
        """
        Quick check if already authenticated - optimized for speed.
        
        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Try to access dashboard directly
            self.driver.get("https://www.cv-library.co.uk/recruiter")
            time.sleep(1)  # Minimal wait
            
            # Quick URL check
            current_url = self.driver.current_url.lower()
            if "recruiter" in current_url and "login" not in current_url:
                self.logger.info("Dashboard accessible - authenticated")
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Quick auth check failed: {e}")
            return False
    
    def _perform_login(self, username: str, password: str) -> bool:
        """
        Perform login with optimized flow.
        
        Args:
            username: CV-Library username
            password: CV-Library password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Navigate to login page
            self.driver.get(self.LOGIN_URL)
            time.sleep(1)
            
            # Find and fill login form
            try:
                # Find email field
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], #email"))
                )
                email_field.clear()
                email_field.send_keys(username)
                
                # Find password field
                password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password'], #password")
                password_field.clear()
                password_field.send_keys(password)
                
                # Find and click submit button
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit'], .btn-login")
                submit_button.click()
                
                # Wait for redirect
                time.sleep(3)
                
                # Quick success check
                current_url = self.driver.current_url.lower()
                if "recruiter" in current_url and "login" not in current_url:
                    self.logger.info("✅ Login successful")
                    
                    # Save session metadata
                    if self.settings.browser.profile.enable_persistent_profile:
                        self._save_session_metadata({
                            'login_time': time.time(),
                            'username': username,
                            'login_url': self.driver.current_url,
                            'login_method': 'fresh_login'
                        })
                    
                    return True
                else:
                    self.logger.error("❌ Login failed - not redirected to dashboard")
                    return False
                    
            except Exception as e:
                self.logger.error(f"❌ Login form interaction failed: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Login process failed: {e}")
            return False
    
    def _check_existing_session(self) -> bool:
        """
        Check if there's an existing valid session in the persistent profile.
        
        Returns:
            True if valid session exists, False otherwise
        """
        try:
            if not self.settings.browser.profile.enable_persistent_profile:
                return False
            
            # Load session metadata
            profile_name = self.settings.browser.profile.profile_name
            metadata = self.profile_manager.load_session_metadata(profile_name)
            
            if not metadata:
                return False
            
            # Check if session is too old
            max_age_seconds = self.settings.browser.profile.max_profile_age_hours * 3600
            if time.time() - metadata.get('login_time', 0) > max_age_seconds:
                self.logger.info("Persistent session is too old")
                return False
            
            # Navigate to dashboard to test session
            self.rate_limiter.wait_if_needed()
            self.driver.get(self.DASHBOARD_URL)
            time.sleep(3)
            
            # Check if we're still logged in
            if self._quick_auth_check():
                self.logger.info("Existing persistent session is valid")
                self.rate_limiter.on_success()
                return True
            else:
                self.logger.info("Persistent session is invalid, fresh login required")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking existing session: {e}")
            return False
    
    def _save_session_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Save session metadata using the profile manager.
        
        Args:
            metadata: Dictionary containing session metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.settings.browser.profile.enable_persistent_profile:
                return self.profile_manager.save_session_metadata(metadata)
            else:
                # Fallback to legacy cookie saving
                return self._save_session_cookies()
        except Exception as e:
            self.logger.error(f"Failed to save session metadata: {e}")
            return False
    
    def logout(self) -> bool:
        """
        Logout from CV-Library with profile management.
        
        Returns:
            True if logout successful, False otherwise
        """
        logout_attempted = False
        logout_success = False
        
        try:
            if self.driver:
                self.logger.info("Attempting to logout from CV-Library")
                
                # Try to find and click logout link
                logout_selectors = [
                    "a[href*='logout']", ".logout", "#logout",
                    "text='Logout'", "text='Sign out'", "text='Log out'",
                    ".user-menu a[href*='logout']", ".nav-user a[href*='logout']",
                    "a:contains('Logout')", "a:contains('Sign out')"
                ]
                
                for selector in logout_selectors:
                    try:
                        if selector.startswith("text=") or ":contains(" in selector:
                            # Skip text-based detection for now - would need more complex implementation
                            continue
                        else:
                            logout_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for logout_element in logout_elements:
                                if logout_element.is_displayed() and logout_element.is_enabled():
                                    WebDriverUtils.safe_click(self.driver, logout_element)
                                    self.logger.info(f"Logout link clicked using selector: {selector}")
                                    logout_attempted = True
                                    time.sleep(2)  # Wait for logout to process
                                    break
                        if logout_attempted:
                            break
                    except Exception as e:
                        self.logger.debug(f"Logout selector '{selector}' failed: {e}")
                        continue
                
                if not logout_attempted:
                    self.logger.warning("Could not find logout link, but will still clear session data")
                
                # Handle profile cleanup based on settings
                if self.settings.browser.profile.enable_persistent_profile:
                    if self.settings.browser.profile.clear_on_logout:
                        # Clear the entire profile
                        profile_name = self.settings.browser.profile.profile_name
                        self.profile_manager.clear_profile(profile_name)
                        self.logger.info("Profile cleared on logout")
                    else:
                        # Just clear session metadata but keep profile data
                        self._clear_session_metadata()
                        self.logger.info("Session metadata cleared, profile data preserved")
                    logout_success = True
                else:
                    # Legacy approach - clear cookies and session data
                    try:
                        self.driver.delete_all_cookies()
                        self.logger.info("Browser cookies cleared")
                        logout_success = True
                    except Exception as cookie_error:
                        self.logger.warning(f"Could not clear cookies: {cookie_error}")
                    
                    # Clear saved session file
                    try:
                        if self.session_file.exists():
                            self.session_file.unlink()
                            self.logger.info("Session file deleted")
                    except Exception as file_error:
                        self.logger.warning(f"Could not delete session file: {file_error}")
                
                # Reset authentication state
                self.is_authenticated = False
                self.session_cookies = {}
                
                # Verify logout by checking current page
                if logout_attempted:
                    try:
                        current_url = self.driver.current_url.lower()
                        if any(indicator in current_url for indicator in ["login", "signin", "home", "www.cv-library.co.uk"]):
                            self.logger.info("Logout verified: redirected to public page")
                            logout_success = True
                        else:
                            self.logger.warning(f"Logout verification unclear: current URL is {current_url}")
                            logout_success = True  # Assume success since we cleared session data
                    except Exception as verify_error:
                        self.logger.debug(f"Could not verify logout: {verify_error}")
                        logout_success = True  # Assume success since we cleared session data
                
                self.logger.info("Logout process completed" + (" successfully" if logout_success else " with warnings"))
                return logout_success
            
            else:
                self.logger.info("No active driver, marking as logged out")
                self.is_authenticated = False
                return True
            
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
        
        finally:
            # Always reset authentication state, even if logout failed
            self.is_authenticated = False
            self.session_cookies = {}
        
        return logout_success
    
    def _clear_session_metadata(self) -> bool:
        """
        Clear session metadata from profile.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if (self.settings.browser.profile.enable_persistent_profile and 
                self.profile_manager.current_profile_path):
                metadata_file = self.profile_manager.current_profile_path / "session_metadata.json"
                if metadata_file.exists():
                    metadata_file.unlink()
                    self.logger.info("Session metadata cleared")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to clear session metadata: {e}")
            return False
    
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