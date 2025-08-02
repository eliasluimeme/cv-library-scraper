"""
Search manager for CV-Library scraper.
Handles search form interaction, result parsing, and pagination.
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from pathlib import Path

from ..config.settings import Settings
from ..models.search_result import SearchResult, SearchResultCollection
from ..models.cv_data import CVData, CandidateInfo
from .utils import WebDriverUtils, RateLimiter


class SearchManager:
    """
    Manages search functionality for CV-Library recruiter portal.
    """
    
    # CV-Library search URLs and selectors
    SEARCH_URL = "https://www.cv-library.co.uk/recruiter/candidate-search"
    ADVANCED_SEARCH_URL = "https://www.cv-library.co.uk/recruiter/candidate-search/advanced"
    RESULTS_URL_PATTERN = "https://www.cv-library.co.uk/recruiter/candidate-search/results"
    
    # Search form selectors (updated for actual CV-Library interface)
    KEYWORDS_SELECTOR = "input[name='keywords'], #keywords, .keywords-input, input[placeholder*='keyword']"
    LOCATION_SELECTOR = "input[name='location'], #location, .location-input, input[placeholder*='location']"
    SALARY_MIN_SELECTOR = "select[name='salary_min'], #salary_min, .salary-from"
    SALARY_MAX_SELECTOR = "select[name='salary_max'], #salary_max, .salary-to"
    JOB_TYPE_SELECTOR = "select[name='job_type'], #job_type, .job-type"
    INDUSTRY_SELECTOR = "select[name='industry'], #industry, .industry"
    MINIMUM_MATCH_SELECTOR = "select[name='minimum_match'], #minimum_match, .minimum-match"
    SEARCH_BUTTON_SELECTOR = "button[type='submit'], input[type='submit'], .search-btn, button.btn-primary"
    
    # Results page selectors (updated for actual CV-Library structure)
    RESULTS_CONTAINER_SELECTOR = ".search-result, .candidate-result, .result-row, tr"
    RESULT_ITEM_SELECTOR = ".search-result, .candidate-result, .result-row, tbody tr"
    
    # Individual result selectors (cleaned up for CV-Library structure)
    CV_TITLE_SELECTOR = "h3 a, .candidate-name a, .result-title a, td a[href*='/cv/']"
    CV_LINK_SELECTOR = "a[href*='/cv/'], .view-cv, .candidate-name a"
    CANDIDATE_NAME_SELECTOR = "h3, .candidate-name, .result-title, td:first-child"
    LOCATION_RESULT_SELECTOR = ".location, .candidate-location, td:nth-child(2)"
    SALARY_RESULT_SELECTOR = ".salary, .candidate-salary, td:nth-child(3)"
    EXPERIENCE_SELECTOR = ".experience, .years-exp, td:nth-child(4)"
    SKILLS_SELECTOR = ".skills, .key-skills, .job-title, td:nth-child(5)"
    SUMMARY_SELECTOR = ".summary, .profile, .description, td:last-child"
    
    # Pagination selectors
    PAGINATION_CONTAINER_SELECTOR = ".pagination, .pager, .page-nav"
    NEXT_PAGE_SELECTOR = ".next, .pagination-next, a[rel='next'], a:contains('Next')"
    PREV_PAGE_SELECTOR = ".prev, .pagination-prev, a[rel='prev'], a:contains('Previous')"
    PAGE_NUMBER_SELECTOR = ".page-number, .pagination a, .pager a"
    CURRENT_PAGE_SELECTOR = ".current, .active, .pagination .active"
    
    def __init__(self, settings: Settings, driver: webdriver.Chrome):
        """Initialize search manager."""
        self.settings = settings
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(
            min_delay=settings.scraping.delay_min,
            max_delay=settings.scraping.delay_max,
            requests_per_minute=settings.scraping.requests_per_minute
        )
        
        # Search state
        self.current_search_params = {}
        self.current_page = 1
        self.total_results = 0
        self.results_per_page = 0
        
    def navigate_to_search_page(self) -> bool:
        """
        Navigate to CV-Library search page.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Navigating to CV-Library search page")
            self.rate_limiter.wait_if_needed()
            
            # Check if we're already on a search page
            current_url = self.driver.current_url.lower()
            if "candidate-search" in current_url or "cv-search" in current_url:
                self.logger.info("Already on search page")
                return True
            
            # If we're on the dashboard, look for "Search CVs" button
            if "recruiter" in current_url and "search" not in current_url:
                self.logger.info("On dashboard page, looking for 'Search CVs' button")
                
                # Try to find and click the "Search CVs" button
                search_cv_selectors = [
                    "a:contains('Search CVs')",
                    ".search-cvs",
                    "a[href*='candidate-search']",
                    "a[href*='cv-search']",
                    ".btn:contains('Search')",
                    "button:contains('Search CVs')"
                ]
                
                search_button_clicked = False
                
                # Look for links and buttons with "Search CVs" text
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                
                for element in all_links + all_buttons:
                    try:
                        element_text = (element.text or "").lower()
                        href = (element.get_attribute("href") or "").lower()
                        
                        if (("search cvs" in element_text or "search cv" in element_text) and 
                            element.is_displayed() and element.is_enabled()):
                            self.logger.info(f"Found 'Search CVs' button/link: {element.text}")
                            element.click()
                            search_button_clicked = True
                            break
                        elif "candidate-search" in href or "cv-search" in href:
                            self.logger.info(f"Found search link via href: {href}")
                            element.click()
                            search_button_clicked = True
                            break
                    except Exception as e:
                        self.logger.debug(f"Could not click element: {e}")
                        continue
                
                if search_button_clicked:
                    # Wait for page to load
                    time.sleep(3)
                    WebDriverWait(self.driver, 15).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                else:
                    # Fallback: direct navigation
                    self.logger.info("Could not find 'Search CVs' button, navigating directly")
                    self.driver.get(self.SEARCH_URL)
            else:
                # Direct navigation to search URL
                self.driver.get(self.SEARCH_URL)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            current_url = self.driver.current_url.lower()
            self.logger.info(f"Current URL after navigating to search: {current_url}")
            
            # Check if we're on the search page
            if any(indicator in current_url for indicator in ["search", "cv-search", "candidate-search"]):
                self.logger.info("Successfully navigated to search page")
                self.rate_limiter.on_success()
                return True
            else:
                self.logger.warning(f"Unexpected page URL: {current_url}")
                return False
                
        except TimeoutException:
            self.logger.error("Timeout while loading search page")
            self.rate_limiter.on_error()
            return False
        except Exception as e:
            self.logger.error(f"Failed to navigate to search page: {e}")
            self.rate_limiter.on_error()
            return False
    
    def _dismiss_modals(self) -> bool:
        """
        Dismiss any modal dialogs that might be blocking form interaction.
        
        Returns:
            True if any modals were dismissed, False otherwise
        """
        dismissed_any = False
        
        try:
            # Common modal dismissal selectors for CV-Library
            modal_dismiss_selectors = [
                # Generic close buttons
                ".modal__close", 
                ".modal-close",
                ".close-modal",
                "button[data-dismiss='modal']",
                ".modal .close",
                ".modal-header .close",
                
                # X buttons
                ".modal .btn-close",
                ".modal button:contains('×')",
                ".modal [aria-label='Close']",
                
                # CV-Library specific
                ".modal button:contains('OK')",
                ".modal button:contains('Got it')",
                ".modal button:contains('Continue')",
                ".modal .btn-primary:contains('OK')",
                
                # Overlay clicks (as last resort)
                ".modal-backdrop",
                ".modal-overlay"
            ]
            
            # Try to find and dismiss any visible modals
            for selector in modal_dismiss_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            self.logger.info(f"Dismissing modal using selector: {selector}")
                            
                            # Scroll into view and click
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(0.3)
                            element.click()
                            time.sleep(0.5)  # Wait for modal to close
                            
                            dismissed_any = True
                            break
                except Exception as e:
                    self.logger.debug(f"Modal selector {selector} failed: {e}")
                    continue
                
                if dismissed_any:
                    break
            
            # If no standard close buttons worked, try ESC key
            if not dismissed_any:
                try:
                    # Check if any modal is still visible
                    modal_elements = self.driver.find_elements(By.CSS_SELECTOR, ".modal, .modal-dialog, [role='dialog']")
                    for modal in modal_elements:
                        if modal.is_displayed():
                            self.logger.info("Trying ESC key to dismiss modal")
                            from selenium.webdriver.common.keys import Keys
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.5)
                            dismissed_any = True
                            break
                except Exception as e:
                    self.logger.debug(f"ESC key modal dismissal failed: {e}")
            
            if dismissed_any:
                self.logger.info("Successfully dismissed modal dialog(s)")
                time.sleep(1)  # Extra wait for page to stabilize
            
            return dismissed_any
            
        except Exception as e:
            self.logger.warning(f"Error while dismissing modals: {e}")
            return False

    def find_search_form_elements(self) -> Optional[Dict[str, Any]]:
        """
        Find search form elements on the page.
        
        Returns:
            Dictionary with form elements or None if not found
        """
        try:
            self.logger.info("Searching for search form elements...")
            elements = {}
            
            # Debug: Log all input and select elements
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            all_selects = self.driver.find_elements(By.TAG_NAME, "select")
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            
            self.logger.debug(f"Found {len(all_inputs)} input elements, {len(all_selects)} select elements, {len(all_buttons)} button elements")
            
            # Log details of form elements for debugging
            for i, inp in enumerate(all_inputs[:10]):  # Limit to first 10 for brevity
                try:
                    name = inp.get_attribute("name") or "no-name"
                    id_attr = inp.get_attribute("id") or "no-id"
                    type_attr = inp.get_attribute("type") or "text"
                    placeholder = inp.get_attribute("placeholder") or ""
                    self.logger.debug(f"Input {i}: name='{name}', id='{id_attr}', type='{type_attr}', placeholder='{placeholder}'")
                except Exception:
                    continue
            
            # Find keywords field - try multiple approaches
            keywords_found = False
            
            # Method 1: Try standard selectors
            for selector in self.KEYWORDS_SELECTOR.split(", "):
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    elements['keywords'] = element
                    self.logger.info(f"Found keywords field with selector: {selector.strip()}")
                    keywords_found = True
                    break
                except NoSuchElementException:
                    continue
            
            # Method 2: Try to find by looking for the largest text input (keywords field is usually prominent)
            if not keywords_found:
                text_inputs = [inp for inp in all_inputs if inp.get_attribute("type") in ["text", None, ""]]
                if text_inputs:
                    # Find the most likely keywords field (usually the first large text input)
                    for inp in text_inputs:
                        try:
                            # Check if it's visible and has reasonable size
                            if inp.is_displayed():
                                elements['keywords'] = inp
                                name = inp.get_attribute("name") or "unknown"
                                self.logger.info(f"Found keywords field by heuristic: input with name='{name}'")
                                keywords_found = True
                                break
                        except Exception:
                            continue
            
            # Find location field
            location_found = False
            for selector in self.LOCATION_SELECTOR.split(", "):
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    elements['location'] = element
                    self.logger.info(f"Found location field with selector: {selector.strip()}")
                    location_found = True
                    break
                except NoSuchElementException:
                    continue
            
            # Try alternative location detection
            if not location_found:
                for inp in all_inputs:
                    try:
                        name = (inp.get_attribute("name") or "").lower()
                        placeholder = (inp.get_attribute("placeholder") or "").lower()
                        if ("location" in name or "location" in placeholder) and inp.is_displayed():
                            elements['location'] = inp
                            self.logger.info(f"Found location field by name/placeholder matching")
                            break
                    except Exception:
                        continue
            
            # Find salary dropdowns
            for selector in self.SALARY_MIN_SELECTOR.split(", "):
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    elements['salary_min'] = element
                    self.logger.info(f"Found salary min field with selector: {selector.strip()}")
                    break
                except NoSuchElementException:
                    continue
            
            for selector in self.SALARY_MAX_SELECTOR.split(", "):
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    elements['salary_max'] = element
                    self.logger.info(f"Found salary max field with selector: {selector.strip()}")
                    break
                except NoSuchElementException:
                    continue
            
            # Find search button - try multiple approaches
            search_button_found = False
            
            # Method 1: Look for "View results" button specifically
            for button in all_buttons:
                try:
                    button_text = (button.text or "").lower()
                    if "view results" in button_text and button.is_displayed():
                        elements['search_button'] = button
                        self.logger.info(f"Found 'View results' button")
                        search_button_found = True
                        break
                except Exception:
                    continue
            
            # Method 2: Try CSS selectors
            if not search_button_found:
                for selector in self.SEARCH_BUTTON_SELECTOR.split(", "):
                    try:
                        if ":contains(" in selector:
                            continue  # Skip text-based selectors for now
                        element = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                        if element.is_displayed():
                            elements['search_button'] = element
                            self.logger.info(f"Found search button with selector: {selector.strip()}")
                            search_button_found = True
                            break
                    except NoSuchElementException:
                        continue
            
            # Method 3: Look for any submit button
            if not search_button_found:
                submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                for button in submit_buttons:
                    try:
                        if button.is_displayed():
                            elements['search_button'] = button
                            self.logger.info("Found submit button as search button")
                            search_button_found = True
                            break
                    except Exception:
                        continue
            
            # Validate required elements
            if not keywords_found:
                self.logger.error("Could not find keywords search field")
                # Try to save page source for debugging
                try:
                    debug_file = Path("debug_search_page.html")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.info(f"Page source saved to {debug_file} for debugging")
                except Exception:
                    pass
                return None
            
            if not search_button_found:
                self.logger.error("Could not find search button")
                return None
            
            self.logger.info(f"Successfully found {len(elements)} search form elements")
            return elements
            
        except Exception as e:
            self.logger.error(f"Error finding search form elements: {e}")
            return None
    
    def fill_search_form(self, keywords: List[str], location: Optional[str] = None, 
                        salary_min: Optional[int] = None, salary_max: Optional[int] = None) -> bool:
        """
        Fill the search form with provided criteria.
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            salary_min: Minimum salary (optional)
            salary_max: Maximum salary (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First, dismiss any modal dialogs that might be blocking the form
            self._dismiss_modals()
            
            # Helper function to safely interact with elements
            def safe_element_interaction(element_key, action_func):
                """Safely interact with an element, refinding if stale."""
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        elements = self.find_search_form_elements()
                        if not elements or element_key not in elements:
                            return False
                        return action_func(elements[element_key])
                    except Exception as e:
                        if "stale element" in str(e).lower() and attempt < max_retries - 1:
                            self.logger.warning(f"Stale element detected for {element_key}, retrying...")
                            time.sleep(1)
                            continue
                        else:
                            raise e
                return False
            
            # Fill keywords
            keywords_text = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            
            def fill_keywords(element):
                element.clear()
                time.sleep(0.5)
                element.send_keys(keywords_text)
                self.logger.info(f"Entered keywords: {keywords_text}")
                return True
            
            if not safe_element_interaction('keywords', fill_keywords):
                self.logger.error("Failed to fill keywords field")
                return False
            
            # Fill location if provided
            if location:
                def fill_location(element):
                    element.clear()
                    time.sleep(0.5)
                    element.send_keys(location)
                    self.logger.info(f"Entered location: {location}")
                    return True
                
                if not safe_element_interaction('location', fill_location):
                    self.logger.warning("Failed to fill location field (optional)")
            
            # Fill minimum salary if provided
            if salary_min:
                def fill_salary_min(element):
                    if element.tag_name.lower() == 'select':
                        # Handle dropdown
                        select = Select(element)
                        # Try to find closest value
                        for option in select.options:
                            if option.get_attribute('value') and int(option.get_attribute('value')) >= salary_min:
                                select.select_by_value(option.get_attribute('value'))
                                break
                    else:
                        # Handle input field
                        element.clear()
                        element.send_keys(str(salary_min))
                    self.logger.info(f"Set minimum salary: {salary_min}")
                    return True
                
                if not safe_element_interaction('salary_min', fill_salary_min):
                    self.logger.warning("Failed to fill minimum salary field (optional)")
            
            # Fill maximum salary if provided
            if salary_max:
                def fill_salary_max(element):
                    if element.tag_name.lower() == 'select':
                        # Handle dropdown
                        select = Select(element)
                        # Try to find closest value
                        for option in reversed(select.options):
                            if option.get_attribute('value') and int(option.get_attribute('value')) <= salary_max:
                                select.select_by_value(option.get_attribute('value'))
                                break
                    else:
                        # Handle input field
                        element.clear()
                        element.send_keys(str(salary_max))
                    self.logger.info(f"Set maximum salary: {salary_max}")
                    return True
                
                if not safe_element_interaction('salary_max', fill_salary_max):
                    self.logger.warning("Failed to fill maximum salary field (optional)")
            
            # Store search parameters
            self.current_search_params = {
                'keywords': keywords,
                'location': location,
                'salary_min': salary_min,
                'salary_max': salary_max
            }
            
            self.logger.info("Search form filled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill search form: {e}")
            return False
    
    def submit_search(self) -> bool:
        """
        Submit the search form.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use safe element interaction for submit button too
            def click_search_button(element):
                WebDriverUtils.safe_click(self.driver, element)
                self.logger.info("Search form submitted")
                return True
            
            # Helper function to safely interact with elements
            def safe_element_interaction_submit(element_key, action_func):
                """Safely interact with an element, refinding if stale."""
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        elements = self.find_search_form_elements()
                        if not elements or element_key not in elements:
                            return False
                        return action_func(elements[element_key])
                    except Exception as e:
                        if "stale element" in str(e).lower() and attempt < max_retries - 1:
                            self.logger.warning(f"Stale element detected for {element_key}, retrying...")
                            time.sleep(1)
                            continue
                        else:
                            raise e
                return False
            
            if not safe_element_interaction_submit('search_button', click_search_button):
                self.logger.error("Failed to click search button")
                return False
            
            # Wait for results page to load
            time.sleep(3)
            self.rate_limiter.wait_if_needed()
            
            # Verify we're on the results page
            current_url = self.driver.current_url.lower()
            self.logger.info(f"After search submission, current URL: {current_url}")
            
            if any(indicator in current_url for indicator in ["search", "results", "cv"]):
                self.logger.info("Search submitted successfully, on results page")
                self.rate_limiter.on_success()
                return True
            else:
                self.logger.warning(f"Unexpected page after search: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to submit search: {e}")
            self.rate_limiter.on_error()
            return False
    
    def search_cvs(self, keywords: List[str], location: Optional[str] = None,
                  salary_min: Optional[int] = None, salary_max: Optional[int] = None) -> bool:
        """
        Perform optimized CV search with minimal steps.
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in (optional)
            salary_min: Minimum salary (optional)
            salary_max: Maximum salary (optional)
            
        Returns:
            True if search was successful, False otherwise
        """
        try:
            # Store search parameters for later use
            self.last_search_keywords = keywords
            self.last_search_location = location
            
            self.logger.info("🔍 Starting CV search for keywords: %s", keywords)
            
            # STEP 1: Navigate directly to search page
            self.logger.info("Step 1: Navigating to search page")
            self.driver.get(self.SEARCH_URL)
            time.sleep(1)  # Reduced wait time
            
            # STEP 2: Fill search form (streamlined)
            self.logger.info("Step 2: Filling search form")
            if not self._fill_search_form_streamlined(keywords, location, salary_min, salary_max):
                return False
            
            # STEP 3: Submit search (streamlined)
            self.logger.info("Step 3: Submitting search")
            if not self._submit_search_streamlined():
                return False
                
            self.logger.info("✅ CV search completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"CV search failed: {e}")
            return False
    
    def _fill_search_form_streamlined(self, keywords: List[str], location: Optional[str] = None,
                                    salary_min: Optional[int] = None, salary_max: Optional[int] = None) -> bool:
        """
        Fill search form using known working selectors with minimal waits.
        """
        try:
            # Keywords field - this is the main search field
            keywords_text = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            
            # Find keywords field quickly
            keywords_field = None
            
            # Try direct selectors without waiting
            for selector in [
                "input.boolean__input",  # The actual visible input field
                "input[name='keywords']", 
                "#keywords", 
                "textarea[name='keywords']"
            ]:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed() and element.is_enabled():
                        keywords_field = element
                        self.logger.info(f"✅ Found keywords field: {selector}")
                        break
                except Exception:
                    continue
            
            # Fallback: look for any large text input
            if not keywords_field:
                text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea")
                for inp in text_inputs:
                    try:
                        if (inp.is_displayed() and inp.is_enabled() and 
                            not inp.get_attribute("readonly") and
                            inp.size['width'] > 200):
                            keywords_field = inp
                            self.logger.info("✅ Found keywords field using fallback")
                            break
                    except Exception:
                        continue
            
            if not keywords_field:
                self.logger.error("❌ Could not find keywords field")
                return False
            
            # Fill keywords with minimal interaction
            try:
                keywords_field.click()
                keywords_field.clear()
                keywords_field.send_keys(keywords_text)
                self.logger.info(f"✅ Entered keywords: {keywords_text}")
            except Exception as e:
                self.logger.error(f"❌ Failed to fill keywords: {e}")
                return False
            
            # Skip location field search if not provided (saves time)
            if location:
                location_field = None
                for selector in ["input[name='location']", "#location"]:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.is_displayed() and element.is_enabled():
                            location_field = element
                            break
                    except Exception:
                        continue
                
                if location_field:
                    try:
                        location_field.click()
                        location_field.clear()
                        location_field.send_keys(location)
                        self.logger.info(f"✅ Entered location: {location}")
                    except Exception as e:
                        self.logger.debug(f"Could not fill location: {e}")
                else:
                    self.logger.debug("Location field not found")
            
            # Store search parameters
            self.current_search_params = {
                'keywords': keywords,
                'location': location,
                'salary_min': salary_min,
                'salary_max': salary_max
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fill search form: {e}")
            return False
    
    def _submit_search_streamlined(self) -> bool:
        """
        Submit the search form using the fastest method possible.
        
        Returns:
            True if search was submitted successfully, False otherwise
        """
        try:
            self.logger.info("Submitting search form...")
            
            # Find and click search button (no wait)
            search_button = None
            
            # Try direct button selectors (fastest)
            button_selectors = [
                "input[value*='View results']",
                "input[type='submit']",
                "button[type='submit']",
                ".search-button",
                "#search-submit"
            ]
            
            for selector in button_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_displayed() and button.is_enabled():
                        search_button = button
                        break
                except Exception:
                    continue
            
            if not search_button:
                self.logger.error("Could not find search submit button")
                return False
            
            # Submit using JavaScript (fastest and most reliable)
            try:
                self.driver.execute_script("arguments[0].click();", search_button)
                self.logger.info("✅ Search form submitted")
                
                # Minimal wait for results to load (further reduced)
                time.sleep(1)
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to submit search: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Search submission failed: {e}")
            return False
    
    def _detect_total_pages(self) -> int:
        """
        Detect the total number of pages from CV-Library's pagination.
        
        Returns:
            Total number of pages (default: 1 if not detected)
        """
        try:
            # Common pagination selectors for CV-Library
            pagination_selectors = [
                ".pagination",
                ".pager", 
                ".page-nav",
                ".pagination-container",
                "[class*='pagination']",
                "[class*='pager']"
            ]
            
            for selector in pagination_selectors:
                try:
                    pagination_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if not pagination_container.is_displayed():
                        continue
                    
                    # Method 1: Look for "Page X of Y" text
                    pagination_text = pagination_container.text.lower()
                    
                    # Pattern: "page 1 of 15" or "1 of 15 pages"
                    import re
                    page_of_pattern = re.search(r'(?:page\s+)?(\d+)\s+of\s+(\d+)(?:\s+pages?)?', pagination_text)
                    if page_of_pattern:
                        total_pages = int(page_of_pattern.group(2))
                        self.logger.info(f"Found total pages from 'X of Y' pattern: {total_pages}")
                        return total_pages
                    
                    # Method 2: Look for numbered page links
                    page_links = pagination_container.find_elements(By.CSS_SELECTOR, "a")
                    page_numbers = []
                    
                    for link in page_links:
                        try:
                            link_text = link.text.strip()
                            # Skip non-numeric links (Next, Previous, etc.)
                            if link_text.isdigit():
                                page_numbers.append(int(link_text))
                        except (ValueError, AttributeError):
                            continue
                    
                    if page_numbers:
                        total_pages = max(page_numbers)
                        self.logger.info(f"Found total pages from page links: {total_pages}")
                        return total_pages
                    
                    # Method 3: Look for last page link
                    last_page_selectors = [
                        "a[title*='last']",
                        "a[aria-label*='last']", 
                        ".last",
                        "a:contains('Last')",
                        ".pagination-last"
                    ]
                    
                    for last_selector in last_page_selectors:
                        try:
                            if ":contains(" in last_selector:
                                continue  # Skip text-based selectors for now
                            last_link = pagination_container.find_element(By.CSS_SELECTOR, last_selector)
                            href = last_link.get_attribute('href')
                            if href:
                                # Extract page number from URL
                                page_match = re.search(r'[?&]page=(\d+)', href)
                                if page_match:
                                    total_pages = int(page_match.group(1))
                                    self.logger.info(f"Found total pages from last page link: {total_pages}")
                                    return total_pages
                        except NoSuchElementException:
                            continue
                    
                    # Method 4: JavaScript-based detection
                    js_total_pages = self.driver.execute_script("""
                        // Look for pagination info in the DOM
                        const paginationTexts = Array.from(document.querySelectorAll('.pagination, .pager, .page-nav, [class*="pagination"]'))
                            .map(el => el.textContent.toLowerCase());
                        
                        for (let text of paginationTexts) {
                            // Pattern: "page 1 of 15"
                            const match = text.match(/(?:page\\s+)?(\\d+)\\s+of\\s+(\\d+)(?:\\s+pages?)?/);
                            if (match) {
                                return parseInt(match[2]);
                            }
                        }
                        
                        // Look for the highest numbered page link
                        const pageLinks = Array.from(document.querySelectorAll('.pagination a, .pager a'))
                            .map(a => a.textContent.trim())
                            .filter(text => /^\\d+$/.test(text))
                            .map(text => parseInt(text));
                        
                        return pageLinks.length > 0 ? Math.max(...pageLinks) : 1;
                    """)
                    
                    if js_total_pages and js_total_pages > 1:
                        self.logger.info(f"Found total pages via JavaScript: {js_total_pages}")
                        return js_total_pages
                        
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.debug(f"Error checking pagination with selector {selector}: {e}")
                    continue
            
            # Method 5: Check for results count and estimate pages
            try:
                results_info_selectors = [
                    ".results-info",
                    ".search-results-count", 
                    ".results-count",
                    "[class*='results']",
                    ".search-summary"
                ]
                
                for selector in results_info_selectors:
                    try:
                        results_info = self.driver.find_element(By.CSS_SELECTOR, selector)
                        info_text = results_info.text.lower()
                        
                        # Pattern: "showing 1-20 of 1,234 results"
                        results_match = re.search(r'(?:showing\s+)?(?:\d+\s*[-–]\s*\d+\s+of\s+)?(\d{1,3}(?:,\d{3})*)\s+(?:results?|candidates?)', info_text)
                        if results_match:
                            total_results = int(results_match.group(1).replace(',', ''))
                            results_per_page = 20  # CV-Library default
                            estimated_pages = (total_results + results_per_page - 1) // results_per_page
                            self.logger.info(f"Estimated total pages from results count: {estimated_pages} (based on {total_results} results)")
                            return estimated_pages
                            
                    except NoSuchElementException:
                        continue
            except Exception as e:
                self.logger.debug(f"Error estimating pages from results count: {e}")
            
            self.logger.info("Could not detect total pages, defaulting to 1")
            return 1
            
        except Exception as e:
            self.logger.warning(f"Error detecting total pages: {e}")
            return 1

    def parse_search_results(self) -> SearchResultCollection:
        """
        Parse search results from the current page with enhanced debugging.
        
        Returns:
            SearchResultCollection containing parsed results
        """
        try:
            start_time = time.time()
            self.logger.info("🔍 Parsing search results with enhanced debugging...")
            
            # Save search results page HTML for debugging
            try:
                debug_html_path = Path("downloaded_cvs") / "debug_search_page.html"
                debug_html_path.parent.mkdir(exist_ok=True)
                with open(debug_html_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                self.logger.info(f"📄 Saved search page HTML for debugging: {debug_html_path}")
            except Exception as e:
                self.logger.warning(f"Could not save debug HTML: {e}")
            
            # Save visible text for debugging
            try:
                debug_text_path = Path("downloaded_cvs") / "debug_search_text.txt"
                with open(debug_text_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.find_element(By.TAG_NAME, "body").text)
                self.logger.info(f"📄 Saved search page text for debugging: {debug_text_path}")
            except Exception as e:
                self.logger.warning(f"Could not save debug text: {e}")
            
            # Find result elements using the optimized approach
            result_elements = self._find_result_elements()
            self.logger.info(f"🔍 Found {len(result_elements)} result elements on page")
            
            if not result_elements:
                self.logger.warning("❌ No result elements found")
                return SearchResultCollection(
                    results=[],
                    search_keywords=getattr(self, 'last_search_keywords', []),
                    total_pages=self._detect_total_pages()
                )
            
            # Process each result element individually with enhanced debugging
            parsed_results = []
            for i, element in enumerate(result_elements, 1):
                try:
                    self.logger.debug(f"🔍 Processing result element {i}/{len(result_elements)}")
                    
                    # Save individual result element HTML for debugging (first 3 only to avoid spam)
                    if i <= 3:
                        try:
                            debug_element_path = Path("downloaded_cvs") / f"debug_result_element_{i}.html"
                            with open(debug_element_path, 'w', encoding='utf-8') as f:
                                f.write(element.get_attribute('outerHTML'))
                            self.logger.debug(f"📄 Saved result element {i} HTML: {debug_element_path}")
                        except Exception as e:
                            self.logger.debug(f"Could not save element HTML: {e}")
                    
                    result = self._parse_single_candidate(element, i)
                    if result:
                        parsed_results.append(result)
                        self.logger.debug(f"✅ Successfully parsed result {i}: {result.name} (ID: {result.cv_id})")
                    else:
                        self.logger.warning(f"❌ Failed to parse result {i}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error processing result element {i}: {e}")
                    continue
            
            # Create and return collection
            collection = SearchResultCollection(
                results=parsed_results,
                search_keywords=getattr(self, 'last_search_keywords', []),
                total_pages=self._detect_total_pages()
            )
            
            duration = time.time() - start_time
            self.logger.info(f"⚡ Successfully parsed {len(parsed_results)} results in {duration:.2f}s (Individual processing)")
            
            # Log detailed summary
            self.logger.info("📊 === SEARCH RESULTS PARSING SUMMARY ===")
            self.logger.info(f"🔸 Total results found: {len(parsed_results)}")
            for i, result in enumerate(parsed_results[:5], 1):  # Log first 5 results
                self.logger.info(f"🔸 Result {i}: {result.name} | ID: {result.cv_id} | Match: {result.profile_match_percentage}")
            
            return collection
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing search results: {e}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return SearchResultCollection(
                results=[],
                search_keywords=getattr(self, 'last_search_keywords', []),
                total_pages=1
            )
    
    def _parse_single_result(self, result_element, index: int) -> Optional[SearchResult]:
        """
        Parse a single search result element.
        
        Args:
            result_element: WebElement containing the result
            index: Index of this result
            
        Returns:
            SearchResult object or None if parsing failed
        """
        try:
            # Extract CV link and ID
            cv_link = None
            cv_id = None
            
            for selector in self.CV_LINK_SELECTOR.split(", "):
                try:
                    link_element = result_element.find_element(By.CSS_SELECTOR, selector.strip())
                    cv_link = link_element.get_attribute("href")
                    if cv_link:
                        # Extract CV ID from URL
                        cv_id_match = re.search(r'/cv/(\d+)', cv_link)
                        if cv_id_match:
                            cv_id = cv_id_match.group(1)
                        break
                except NoSuchElementException:
                    continue
            
            # Extract candidate name/title
            candidate_name = None
            for selector in [self.CV_TITLE_SELECTOR, self.CANDIDATE_NAME_SELECTOR]:
                for sub_selector in selector.split(", "):
                    try:
                        name_element = result_element.find_element(By.CSS_SELECTOR, sub_selector.strip())
                        candidate_name = name_element.text.strip()
                        if candidate_name:
                            break
                    except NoSuchElementException:
                        continue
                if candidate_name:
                    break
            
            # Extract location
            location = None
            for selector in self.LOCATION_RESULT_SELECTOR.split(", "):
                try:
                    location_element = result_element.find_element(By.CSS_SELECTOR, selector.strip())
                    location = location_element.text.strip()
                    if location:
                        break
                except NoSuchElementException:
                    continue
            
            # Extract salary
            salary = None
            for selector in self.SALARY_RESULT_SELECTOR.split(", "):
                try:
                    salary_element = result_element.find_element(By.CSS_SELECTOR, selector.strip())
                    salary = salary_element.text.strip()
                    if salary:
                        break
                except NoSuchElementException:
                    continue
            
            # Extract experience
            experience = None
            for selector in self.EXPERIENCE_SELECTOR.split(", "):
                try:
                    exp_element = result_element.find_element(By.CSS_SELECTOR, selector.strip())
                    experience = exp_element.text.strip()
                    if experience:
                        break
                except NoSuchElementException:
                    continue
            
            # Extract skills
            skills = []
            for selector in self.SKILLS_SELECTOR.split(", "):
                try:
                    skills_element = result_element.find_element(By.CSS_SELECTOR, selector.strip())
                    skills_text = skills_element.text.strip()
                    if skills_text:
                        # Split skills by common delimiters
                        skills = [skill.strip() for skill in re.split(r'[,;|•]', skills_text) if skill.strip()]
                        break
                except NoSuchElementException:
                    continue
            
            # Extract summary
            summary = None
            for selector in self.SUMMARY_SELECTOR.split(", "):
                try:
                    summary_element = result_element.find_element(By.CSS_SELECTOR, selector.strip())
                    summary = summary_element.text.strip()
                    if summary:
                        break
                except NoSuchElementException:
                    continue
            
            # Create SearchResult object
            if candidate_name or cv_link:  # At least one required field
                result = SearchResult(
                    cv_id=cv_id or f"unknown_{index}",
                    name=candidate_name or "Unknown",  # Use 'name' instead of 'candidate_name'
                    location=location,
                    salary=salary,
                    experience_level=experience,  # Use 'experience_level' instead of 'experience'
                    skills=skills,
                    summary=summary,
                    profile_url=cv_link,  # Use 'profile_url' instead of 'cv_url'
                    search_keywords=self.current_search_params.get('keywords', []),
                    search_rank=index + 1  # Use 'search_rank' instead of 'result_position'
                )
                
                self.logger.debug(f"Parsed result {index}: {candidate_name}")
                return result
            else:
                self.logger.warning(f"Result {index} missing required fields")
                return None
                
        except Exception as e:
            self.logger.warning(f"Failed to parse result {index}: {e}")
            return None
    
    def go_to_page(self, page_number: int) -> bool:
        """
        Navigate to a specific page number.
        
        Args:
            page_number: The page number to navigate to (1-based)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if page_number < 1:
                self.logger.warning(f"Invalid page number: {page_number}")
                return False
            
            # Method 1: Try to find direct page link
            page_link_selectors = [
                f"a[href*='page={page_number}']",
                f".pagination a:contains('{page_number}')",
                f".pager a:contains('{page_number}')",
                f".page-nav a[data-page='{page_number}']"
            ]
            
            for selector in page_link_selectors:
                try:
                    if ":contains(" in selector:
                        continue  # Skip text-based selectors for now
                    page_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if page_link.is_displayed() and page_link.is_enabled():
                        self.logger.info(f"Navigating to page {page_number} using direct link")
                        WebDriverUtils.safe_click(self.driver, page_link)
                        time.sleep(2)  # Wait for page to load
                        return True
                except NoSuchElementException:
                    continue
            
            # Method 2: JavaScript-based navigation
            try:
                # Look for pagination links and click the correct one
                js_result = self.driver.execute_script(f"""
                    // Find all pagination links
                    const pageLinks = Array.from(document.querySelectorAll('.pagination a, .pager a, .page-nav a'));
                    
                    // Look for link with the specific page number
                    for (let link of pageLinks) {{
                        if (link.textContent.trim() === '{page_number}') {{
                            link.click();
                            return true;
                        }}
                    }}
                    
                    // If direct link not found, try to construct URL
                    const currentUrl = window.location.href;
                    const pageParam = 'page={page_number}';
                    
                    let newUrl;
                    if (currentUrl.includes('page=')) {{
                        newUrl = currentUrl.replace(/page=\\d+/, pageParam);
                    }} else {{
                        const separator = currentUrl.includes('?') ? '&' : '?';
                        newUrl = currentUrl + separator + pageParam;
                    }}
                    
                    window.location.href = newUrl;
                    return true;
                """)
                
                if js_result:
                    self.logger.info(f"Navigated to page {page_number} using JavaScript")
                    time.sleep(3)  # Wait for page to load
                    return True
                    
            except Exception as e:
                self.logger.debug(f"JavaScript navigation failed: {e}")
            
            # Method 3: URL manipulation
            try:
                current_url = self.driver.current_url
                
                # Add or update page parameter
                if 'page=' in current_url:
                    import re
                    new_url = re.sub(r'page=\d+', f'page={page_number}', current_url)
                else:
                    separator = '&' if '?' in current_url else '?'
                    new_url = f"{current_url}{separator}page={page_number}"
                
                self.logger.info(f"Navigating to page {page_number} via URL: {new_url}")
                self.driver.get(new_url)
                time.sleep(2)
                return True
                
            except Exception as e:
                self.logger.error(f"URL navigation to page {page_number} failed: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to navigate to page {page_number}: {e}")
            return False

    def get_current_page_number(self) -> int:
        """
        Get the current page number.
        
        Returns:
            Current page number (1-based)
        """
        try:
            # Method 1: Look for active/current page indicator
            current_page_selectors = [
                ".pagination .active",
                ".pagination .current", 
                ".pager .active",
                ".pager .current",
                ".page-nav .current",
                "[class*='pagination'] [class*='active']",
                "[class*='pagination'] [class*='current']"
            ]
            
            for selector in current_page_selectors:
                try:
                    current_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    page_text = current_element.text.strip()
                    if page_text.isdigit():
                        page_number = int(page_text)
                        self.logger.debug(f"Current page detected from active element: {page_number}")
                        return page_number
                except NoSuchElementException:
                    continue
            
            # Method 2: Extract from URL
            try:
                current_url = self.driver.current_url
                import re
                page_match = re.search(r'[?&]page=(\d+)', current_url)
                if page_match:
                    page_number = int(page_match.group(1))
                    self.logger.debug(f"Current page detected from URL: {page_number}")
                    return page_number
            except Exception as e:
                self.logger.debug(f"Could not extract page from URL: {e}")
            
            # Method 3: JavaScript detection
            try:
                js_page = self.driver.execute_script(r"""
                    // Look for active page indicator
                    const activeElements = document.querySelectorAll('.pagination .active, .pager .active, .current');
                    for (let el of activeElements) {
                        const text = el.textContent.trim();
                        if (/^\d+$/.test(text)) {
                            return parseInt(text);
                        }
                    }
                    
                    // Extract from URL
                    const urlMatch = window.location.href.match(/[?&]page=(\d+)/);
                    return urlMatch ? parseInt(urlMatch[1]) : 1;
                """)
                
                if js_page:
                    self.logger.debug(f"Current page detected via JavaScript: {js_page}")
                    return js_page
            except Exception as e:
                self.logger.debug(f"JavaScript page detection failed: {e}")
            
            # Default to page 1
            self.logger.debug("Could not detect current page, defaulting to 1")
            return 1
            
        except Exception as e:
            self.logger.warning(f"Error detecting current page: {e}")
            return 1

    def has_next_page(self) -> bool:
        """
        Check if there are more pages of results.
        
        Returns:
            True if next page exists, False otherwise
        """
        try:
            for selector in self.NEXT_PAGE_SELECTOR.split(", "):
                try:
                    if ":contains(" in selector:
                        continue  # Skip text-based selectors
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    if next_button.is_enabled() and next_button.is_displayed():
                        return True
                except NoSuchElementException:
                    continue
            return False
        except Exception as e:
            self.logger.debug(f"Error checking for next page: {e}")
            return False
    
    def go_to_next_page(self) -> bool:
        """
        Navigate to the next page of results.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.has_next_page():
                return False
            
            for selector in self.NEXT_PAGE_SELECTOR.split(", "):
                try:
                    if ":contains(" in selector:
                        continue  # Skip text-based selectors
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector.strip())
                    if next_button.is_enabled() and next_button.is_displayed():
                        WebDriverUtils.safe_click(self.driver, next_button)
                        self.current_page += 1
                        time.sleep(3)  # Wait for page to load
                        self.logger.info(f"Moved to page {self.current_page}")
                        return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to go to next page: {e}")
            return False
    
    def get_all_results(self, max_pages: int = 5) -> SearchResultCollection:
        """
        Get all search results from multiple pages.
        
        Args:
            max_pages: Maximum number of pages to crawl
            
        Returns:
            SearchResultCollection with all results
        """
        try:
            all_results = []
            page_count = 0
            
            while page_count < max_pages:
                self.logger.info(f"Parsing results from page {self.current_page}")
                
                # Parse current page
                page_results = self.parse_search_results()
                all_results.extend(page_results.results)
                
                # Check for next page
                if not self.has_next_page():
                    self.logger.info("No more pages available")
                    break
                
                # Go to next page
                if not self.go_to_next_page():
                    self.logger.info("Could not navigate to next page")
                    break
                
                page_count += 1
                self.rate_limiter.wait_if_needed()
            
            self.logger.info(f"Collected {len(all_results)} results from {page_count + 1} pages")
            
            return SearchResultCollection(
                results=all_results,
                search_keywords=self.current_search_params.get('keywords', []),
                search_location=self.current_search_params.get('location'),
                page_number=self.current_page,
                total_found=len(all_results)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get all results: {e}")
            return SearchResultCollection(
                results=[], 
                search_keywords=self.current_search_params.get('keywords', []),
                search_location=self.current_search_params.get('location')
            ) 

    def _parse_single_result_optimized(self, result_element, index: int) -> Optional[SearchResult]:
        """
        Ultra-fast parsing of a single search result element with improved accuracy.
        
        Args:
            result_element: WebElement containing the result
            index: Index of this result
            
        Returns:
            SearchResult object or None if parsing failed
        """
        try:
            cv_link = None
            cv_id = None
            candidate_name = "Unknown"
            
            # Strategy 1: Extract all links from the result element first
            all_links = result_element.find_elements(By.TAG_NAME, "a")
            cv_links = []
            
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    if href and "/cv/" in href:
                        cv_links.append((link, href))
                except Exception:
                    continue
            
            # Strategy 2: Find the main candidate name link
            if cv_links:
                # Use the first CV link found
                main_link, cv_link = cv_links[0]
                
                try:
                    # Try to get candidate name from the link text
                    link_text = main_link.text.strip()
                    
                    # If link text is not a good candidate name, look for the name in nearby elements
                    if (not link_text or 
                        link_text.lower() in ["view cv", "view", "cv"] or 
                        len(link_text) < 4):
                        
                        # Strategy 2a: Look for candidate name in parent elements
                        try:
                            parent = main_link.find_element(By.XPATH, "./..")
                            if parent.tag_name.lower() == "h3":
                                # The h3 might contain the full name
                                h3_text = parent.text.strip()
                                if h3_text and h3_text != link_text:
                                    candidate_name = h3_text.replace(link_text, "").strip()
                                    if not candidate_name:
                                        candidate_name = h3_text
                        except Exception:
                            pass
                        
                        # Strategy 2b: Parse from result element structure
                        if candidate_name == "Unknown":
                            try:
                                # Get all text from the result and parse it
                                result_text = result_element.text
                                lines = [line.strip() for line in result_text.split('\n') if line.strip()]
                                
                                # Find potential candidate name (usually first meaningful line)
                                for line in lines[:4]:  # Check first 4 lines
                                    if (line and 
                                        len(line) > 4 and 
                                        len(line) < 50 and  # Reasonable name length
                                        line.lower() not in ["view cv", "view", "cv", "location", "salary", "job title"] and
                                        not line.startswith("£") and
                                        not any(word in line.lower() for word in [
                                            "experience", "years", "willing", "location:", "salary:", 
                                            "job type:", "driving", "west midlands", "birmingham"
                                        ]) and
                                        not re.match(r'^\d+', line) and  # Doesn't start with numbers
                                        " " in line):  # Contains space (likely a full name)
                                        
                                        candidate_name = line
                                        break
                            except Exception:
                                pass
                    else:
                        candidate_name = link_text
                    
                    # Extract CV ID from URL
                    if cv_link:
                        cv_id_match = re.search(r'/cv/(\d+)', cv_link)
                        if cv_id_match:
                            cv_id = cv_id_match.group(1)
                
                except Exception as e:
                    self.logger.debug(f"Error extracting candidate name: {e}")
            
            # Fallback if no CV links found
            if not cv_links:
                try:
                    result_text = result_element.text
                    lines = [line.strip() for line in result_text.split('\n') if line.strip()]
                    
                    # Look for a line that looks like a name
                    for line in lines[:3]:
                        if (line and 
                            len(line) > 4 and 
                            len(line) < 50 and
                            " " in line and  # Has space
                            not line.startswith("£") and
                            not any(word in line.lower() for word in ["location", "salary", "view"])):
                            candidate_name = line
                            break
                except Exception:
                    pass
            
            # Set fallback values
            if candidate_name == "Unknown" or not candidate_name:
                candidate_name = f"Candidate_{index+1}"
            
            if not cv_id:
                cv_id = f"candidate_{index}_{int(time.time())}"
            
            # Quick extraction of other essential fields
            location = None
            salary = None
            skills = []
            summary = None
            
            try:
                result_text = result_element.text
                
                # Fast location extraction
                location_patterns = [
                    r"Location:\s*([^\n\r]+)",
                    r"Town:\s*([^\n\r]+)"
                ]
                for pattern in location_patterns:
                    match = re.search(pattern, result_text, re.IGNORECASE)
                    if match:
                        location = match.group(1).strip()
                        break
                
                # Fast salary extraction
                if "£" in result_text:
                    salary_match = re.search(r'£[\d,]+(?:\s*-\s*£[\d,]+)?(?:\s*k)?(?:\s*per\s*annum)?', result_text, re.IGNORECASE)
                    if salary_match:
                        salary = salary_match.group(0)
                
                # Fast skills extraction (look for common tech skills)
                skill_keywords = [
                    "Python", "Django", "React", "JavaScript", "Java", "C++", "SQL", "AWS", 
                    "Node.js", "Angular", "Vue", "PHP", "Ruby", "Go", "Kotlin", "Swift",
                    "Docker", "Kubernetes", "Git", "Linux", "Windows", "MySQL", "PostgreSQL"
                ]
                
                text_lower = result_text.lower()
                for skill in skill_keywords:
                    if skill.lower() in text_lower:
                        skills.append(skill)
                
                # Extract summary (usually the job title line)
                lines = result_text.split('\n')
                for line in lines[1:4]:  # Skip first line (name), check next few
                    line = line.strip()
                    if (line and 
                        len(line) > 10 and 
                        len(line) < 100 and
                        not line.startswith("£") and
                        not any(word in line.lower() for word in ["location:", "salary:", "willing to travel"])):
                        summary = line
                        break
                
            except Exception as e:
                self.logger.debug(f"Error extracting additional fields: {e}")
            
            # Create SearchResult with extracted data
            result = SearchResult(
                cv_id=cv_id,
                name=candidate_name,
                location=location,
                salary=salary,
                experience_level=None,  # Skip for speed
                skills=skills,
                summary=summary,
                profile_url=cv_link,
                search_keywords=self.current_search_params.get('keywords', []),
                search_rank=index + 1
            )
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Failed to parse result {index}: {e}")
            return None 

    def _parse_single_result_ultra_fast(self, result_element, index: int) -> Optional[SearchResult]:
        """
        Ultra-fast parsing focused on speed over completeness.
        
        Args:
            result_element: WebElement containing the result
            index: Index of this result
            
        Returns:
            SearchResult object or None if parsing failed
        """
        try:
            # Single DOM access to get all text content
            result_text = result_element.text
            if not result_text:
                return None
            
            # Single DOM access to get all links
            try:
                cv_links = result_element.find_elements(By.CSS_SELECTOR, "a[href*='/cv/']")
                cv_link = cv_links[0].get_attribute("href") if cv_links else None
                cv_id = re.search(r'/cv/(\d+)', cv_link).group(1) if cv_link and re.search(r'/cv/(\d+)', cv_link) else f"candidate_{index}_{int(time.time())}"
            except Exception:
                cv_link = None
                cv_id = f"candidate_{index}_{int(time.time())}"
            
            # Fast text parsing - split only once
            lines = [line.strip() for line in result_text.split('\n') if line.strip()]
            
            # Extract candidate name (first meaningful line)
            candidate_name = "Unknown"
            for line in lines[:3]:
                if (line and 
                    len(line) > 4 and 
                    len(line) < 60 and
                    " " in line and
                    not line.startswith("£") and
                    "location" not in line.lower() and
                    "salary" not in line.lower() and
                    "view" not in line.lower()):
                    candidate_name = line
                    break
            
            if candidate_name == "Unknown":
                candidate_name = f"Candidate_{index+1}"
            
            # Fast regex-based extraction (single pass)
            location = None
            salary = None
            
            # Location pattern (single regex)
            location_match = re.search(r'(?:Location|Town):\s*([^\n\r,]+)', result_text, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
            
            # Salary pattern (single regex)  
            salary_match = re.search(r'£[\d,]+(?:\s*-\s*£[\d,]+)?(?:\s*k)?', result_text, re.IGNORECASE)
            if salary_match:
                salary = salary_match.group(0)
            
            # Essential skills only (minimal processing)
            essential_skills = ["Python", "Java", "React", "JavaScript", "SQL", "AWS"]
            skills = [skill for skill in essential_skills if skill.lower() in result_text.lower()]
            
            # Create result with minimal data
            return SearchResult(
                cv_id=cv_id,
                name=candidate_name,
                location=location,
                salary=salary,
                experience_level=None,
                skills=skills,
                summary=None,  # Skip for speed
                profile_url=cv_link,
                search_keywords=self.current_search_params.get('keywords', []),
                search_rank=index + 1
            )
            
        except Exception as e:
            self.logger.debug(f"Fast parse failed for result {index}: {e}")
            return None 

    def _find_result_elements(self) -> List[webdriver.remote.webelement.WebElement]:
        """
        Find all individual result elements on the current page.
        
        Returns:
            List of WebElement objects for each search result.
        """
        try:
            # Use the defined selector for individual results
            result_elements = self.driver.find_elements(By.CSS_SELECTOR, self.RESULT_ITEM_SELECTOR)
            return result_elements
        except NoSuchElementException:
            return []
        except Exception as e:
            self.logger.error(f"Error finding result elements: {e}")
            return [] 

    def _parse_single_candidate(self, result_element: webdriver.remote.webelement.WebElement, index: int) -> Optional[SearchResult]:
        """
        Parse a single search result element into a comprehensive SearchResult object with enhanced debugging.
        
        Args:
            result_element: WebElement containing the result
            index: Index of this result (1-based)
            
        Returns:
            SearchResult object or None if parsing failed
        """
        try:
            # Get the full text content of this result element for parsing
            element_text = result_element.text.strip()
            element_html = result_element.get_attribute('innerHTML')
            
            self.logger.debug(f"🔍 Parsing candidate {index}: Element text preview: '{element_text[:100]}...'")
            
            # Initialize all variables for comprehensive extraction
            extracted_data = {
                'cv_id': None,
                'name': None,
                'location': None,
                'town': None,
                'county': None,
                'salary': None,
                'expected_salary': None,
                'skills': [],
                'main_skills': [],
                'profile_url': None,
                'current_job_title': None,
                'desired_job_title': None,
                'job_type': None,
                'date_available': None,
                'willing_to_travel': None,
                'willing_to_relocate': None,
                'uk_driving_licence': None,
                'profile_match_percentage': None,
                'profile_cv_last_updated': None,
                'last_viewed_date': None,
                'quickview_ref': None,
                'chosen_industries': [],
                'cv_keywords': None,
                'fluent_languages': [],
                'summary': None
            }
            
            # Method 1: Extract from links (most reliable for CV ID and URL)
            cv_links = result_element.find_elements(By.CSS_SELECTOR, "a[href*='/cv/']")
            if cv_links:
                link = cv_links[0]
                href = link.get_attribute('href')
                self.logger.debug(f"🔍 Found CV link: {href}")
                
                if href:
                    # Extract CV ID from URL
                    cv_id_match = re.search(r'/cv/(\d+)', href)
                    if cv_id_match:
                        extracted_data['cv_id'] = cv_id_match.group(1)
                        extracted_data['profile_url'] = href
                        self.logger.debug(f"✅ Extracted CV ID: {extracted_data['cv_id']}")
            
            # If no CV ID found, skip this result
            if not extracted_data['cv_id']:
                self.logger.warning(f"No CV ID found for result {index}")
                return None
            
            # Method 2: Enhanced text-based extraction using the patterns we see in debug
            self.logger.debug(f"🔍 Element text structure: {element_text[:300]}...")
            
            # Extract candidate name (usually the first substantial text line)
            text_lines = [line.strip() for line in element_text.split('\n') if line.strip()]
            
            # Look for name patterns - usually comes before match percentage
            for i, line in enumerate(text_lines):
                # Skip common UI elements and find the actual name
                if (line and len(line) > 3 and len(line) < 60 and
                    not line.lower().startswith(('add note', 'select', 'location', 'willing', 'salary', 
                                               'job title', 'uk driving', 'desired role', 'job type', 
                                               'date available', 'skills:', 'cv keywords:', 'last viewed:',
                                               'view cv', 'profile/cv last updated')) and
                    not re.search(r'^\d+%\s*match$', line, re.IGNORECASE) and
                    not line.startswith(('£', 'http', 'www')) and
                    not re.search(r'^\d{2}/\d{2}/\d{4}', line)):  # Not a date
                    
                    extracted_data['name'] = line
                    self.logger.debug(f"✅ Extracted name: {extracted_data['name']}")
                    break
            
            # Extract specific fields using direct text search
            field_patterns = [
                # Location information
                (r'Location\s*([^\n\r]+)', 'location'),
                (r'Salary\s*([^\n\r]+)', 'salary'),
                (r'Job Title\s*([^\n\r]+)', 'current_job_title'),
                (r'Desired Role\s*([^\n\r]+)', 'desired_job_title'),
                (r'Job Type\s*([^\n\r]+)', 'job_type'),
                (r'Date Available\s*([^\n\r]+)', 'date_available'),
                (r'Willing to Travel\s*([^\n\r]+)', 'willing_to_travel'),
                (r'Willing to Relocate\s*([^\n\r]+)', 'willing_to_relocate'),
                (r'UK Driving Licence\s*([^\n\r]+)', 'uk_driving_licence'),
                
                # Profile metadata
                (r'(\d+%\s*Match)', 'profile_match_percentage'),
                (r'Profile/CV Last Updated:\s*([^\n\r]+)', 'profile_cv_last_updated'),
                (r'Last Viewed:\s*([^\n\r]+)', 'last_viewed_date'),
                
                # Skills and keywords  
                (r'Skills:\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=CV Keywords:|Last Viewed:|View CV|$)', 'skills_text'),
                (r'CV Keywords:\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=Last Viewed:|View CV|$)', 'cv_keywords'),
            ]
            
            for pattern, field_name in field_patterns:
                match = re.search(pattern, element_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    self.logger.debug(f"🔍 Found {field_name}: '{value[:50]}...'")
                    
                    if field_name == 'skills_text':
                        # Parse skills from the skills text
                        if value:
                            # Split by common separators and clean up
                            skill_candidates = re.split(r'[,\n\r]+', value)
                            skills = []
                            for skill in skill_candidates:
                                skill = skill.strip()
                                if (skill and len(skill) > 2 and len(skill) < 50 and
                                    not skill.lower().startswith(('cv keywords', 'last viewed', 'view cv'))):
                                    skills.append(skill)
                            extracted_data['skills'] = skills[:15]  # Limit to 15
                            extracted_data['summary'] = value  # Keep full text as summary
                            self.logger.debug(f"✅ Extracted {len(skills)} skills")
                    else:
                        extracted_data[field_name] = value
            
            # Parse location into town and county if possible
            if extracted_data['location']:
                location_parts = extracted_data['location'].split(',')
                if len(location_parts) >= 2:
                    extracted_data['town'] = location_parts[0].strip()
                    extracted_data['county'] = location_parts[1].strip()
                elif len(location_parts) == 1:
                    extracted_data['town'] = location_parts[0].strip()
            
            # Method 3: DOM-based extraction for additional fields
            try:
                # Look for specific elements within this result
                name_elements = result_element.find_elements(By.CSS_SELECTOR, "h3, .candidate-name, .name, strong")
                for elem in name_elements:
                    if elem.text and len(elem.text) > 3 and not extracted_data['name']:
                        potential_name = elem.text.strip()
                        if not potential_name.lower().startswith(('view cv', 'add note', 'select')):
                            extracted_data['name'] = potential_name
                            break
                
                # Look for match percentage elements
                if not extracted_data['profile_match_percentage']:
                    match_elements = result_element.find_elements(By.CSS_SELECTOR, "[class*='match'], .percentage")
                    for elem in match_elements:
                        if elem.text and '%' in elem.text:
                            extracted_data['profile_match_percentage'] = elem.text.strip()
                            break
                        
            except Exception as e:
                self.logger.debug(f"❌ Error in DOM-based extraction: {e}")
            
            # Create SearchResult object with all extracted data
            search_result = SearchResult(
                cv_id=extracted_data['cv_id'],
                name=extracted_data['name'] or "Unknown",
                location=extracted_data['location'],
                town=extracted_data['town'],
                county=extracted_data['county'],
                salary=extracted_data['salary'],
                expected_salary=extracted_data['expected_salary'],
                skills=extracted_data['skills'],
                main_skills=extracted_data['main_skills'],
                profile_url=extracted_data['profile_url'],
                current_job_title=extracted_data['current_job_title'],
                desired_job_title=extracted_data['desired_job_title'],
                job_type=extracted_data['job_type'],
                date_available=extracted_data['date_available'],
                willing_to_travel=extracted_data['willing_to_travel'],
                willing_to_relocate=extracted_data['willing_to_relocate'],
                uk_driving_licence=extracted_data['uk_driving_licence'],
                profile_match_percentage=extracted_data['profile_match_percentage'],
                profile_cv_last_updated=extracted_data['profile_cv_last_updated'],
                last_viewed_date=extracted_data['last_viewed_date'],
                quickview_ref=extracted_data['quickview_ref'],
                chosen_industries=extracted_data['chosen_industries'],
                cv_keywords=extracted_data['cv_keywords'],
                fluent_languages=extracted_data['fluent_languages'],
                summary=extracted_data['summary'],
                search_rank=index
            )
            
            self.logger.debug(f"✅ Successfully parsed candidate {index}: {search_result.name} | CV ID: {search_result.cv_id} | Match: {search_result.profile_match_percentage} | Last Viewed: {search_result.last_viewed_date}")
            return search_result
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing candidate {index}: {e}")
            import traceback
            self.logger.debug(f"❌ Traceback: {traceback.format_exc()}")
            return None

    def _extract_all_results_with_javascript(self) -> List[Dict[str, Any]]:
        """
        Extract all search results using JavaScript for maximum speed.
        
        Returns:
            List of dictionaries containing search result data
        """
        try:
            # JavaScript code to extract all search result data in one operation
            js_extraction_code = """
            const results = [];
            const searchResults = document.querySelectorAll('.search-result');
            
            searchResults.forEach((result, index) => {
                try {
                    // Extract name from CV link
                    const nameLink = result.querySelector('a[href*="/cv/"]');
                    const name = nameLink ? nameLink.textContent.trim() : 'Unknown';
                    const profileUrl = nameLink ? nameLink.href : '';
                    
                    // Extract all text content for parsing
                    const resultText = result.textContent || '';
                    
                    // Extract location (common patterns)
                    const locationMatch = resultText.match(/(?:Location|Based in|Located in)\\s*:?\\s*([^\\n\\r,]+)/i) ||
                                        resultText.match(/(?:Location|Based in|Located in)\\s*:?\\s*([^\\n\\r,]+)/i) ||
                                        resultText.match(/\\b([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*(?:,\\s*[A-Z]{2,})?(?:,\\s*UK)?)\\b/);
                    const location = locationMatch ? locationMatch[1].trim() : 'Not specified';
                    
                    // Extract experience (years)
                    const expMatch = resultText.match(/(\\d+)\\s*(?:years?|yrs?)\\s*(?:of\\s*)?(?:experience|exp)/i) ||
                                   resultText.match(/(?:experience|exp)\\s*:?\\s*(\\d+)\\s*(?:years?|yrs?)/i);
                    const experience = expMatch ? expMatch[1] + ' years' : 'Not specified';
                    
                    // Extract salary (if mentioned)
                    const salaryMatch = resultText.match(/£([\\d,]+)(?:\\s*(?:-|to)\\s*£?([\\d,]+))?/i);
                    const salary = salaryMatch ? '£' + salaryMatch[0].replace('£', '') : 'Not specified';
                    
                    // Extract skills (look for common patterns)
                    const skillsText = resultText.toLowerCase();
                    const foundSkills = [];
                    const skillKeywords = [
                        'python', 'javascript', 'java', 'react', 'angular', 'vue', 'node.js', 'django', 'flask',
                        'sql', 'mysql', 'postgresql', 'mongodb', 'aws', 'azure', 'docker', 'kubernetes',
                        'git', 'linux', 'html', 'css', 'typescript', 'php', 'c++', 'c#', '.net', 'ruby'
                    ];
                    
                    skillKeywords.forEach(skill => {
                        if (skillsText.includes(skill)) {
                            foundSkills.push(skill);
                        }
                    });
                    
                    results.push({
                        name: name,
                        profileUrl: profileUrl,
                        location: location,
                        experience: experience,
                        salary: salary,
                        skills: foundSkills,
                        searchRank: index + 1,
                        resultText: resultText.substring(0, 500) // First 500 chars for additional parsing if needed
                    });
                } catch (e) {
                    console.log('Error parsing result ' + index + ':', e);
                }
            });
            
            return results;
            """
            
            # Execute JavaScript and get results
            results = self.driver.execute_script(js_extraction_code)
            self.logger.info(f"JavaScript extracted {len(results)} results in bulk")
            return results
            
        except Exception as e:
            self.logger.error(f"JavaScript bulk extraction failed: {e}")
            return [] 

    def _parse_search_results_dom_fallback(self) -> SearchResultCollection:
        """
        Fallback method to parse search results using DOM-based extraction.
        This is slower but more robust for cases where JavaScript extraction fails.
        """
        try:
            self.logger.info("⚡ Parsing search results (DOM fallback mode)")
            start_time = time.time()
            
            # Wait briefly for page to be ready
            time.sleep(0.5)
            
            # Find all result items on the page
            result_items = self.driver.find_elements(By.CSS_SELECTOR, self.RESULT_ITEM_SELECTOR)
            
            search_results = []
            for index, result_element in enumerate(result_items):
                search_result = self._parse_single_result(result_element, index)
                if search_result:
                    search_results.append(search_result)
                else:
                    self.logger.debug(f"DOM fallback failed to parse result {index}")
            
            parse_time = time.time() - start_time
            self.logger.info(f"⚡ Successfully parsed {len(search_results)} results in {parse_time:.2f}s (DOM fallback)")
            
            # Detect total pages for pagination
            total_pages = self._detect_total_pages()
            
            return SearchResultCollection(
                results=search_results,
                search_keywords=getattr(self, 'last_search_keywords', []),
                search_location=getattr(self, 'last_search_location', None),
                total_found=len(search_results),
                page_number=1,
                total_pages=total_pages
            )
            
        except Exception as e:
            self.logger.error(f"DOM fallback parsing failed: {e}")
            return SearchResultCollection(results=[]) 