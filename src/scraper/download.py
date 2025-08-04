"""
Download manager for CV-Library scraper.
Handles CV downloading from search results with tab management.
"""

import logging
import time
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from datetime import datetime

from ..config.settings import Settings
from ..models.search_result import SearchResultCollection, SearchResult
from ..models.cv_data import CVData, CandidateInfo
from .utils import WebDriverUtils, RateLimiter, FileUtils


class DownloadManager:
    """
    Manages CV downloading from CV-Library search results.
    Handles tab switching, CV downloads, and file management.
    """
    
    # Download selectors
    VIEW_CV_SELECTORS = [
        "a:contains('View CV')", 
        ".view-cv", 
        "a[href*='/cv/']",
        ".cv-link",
        "button:contains('View CV')"
    ]
    
    DOWNLOAD_CV_SELECTORS = [
        "a:contains('Download CV')",
        ".download-cv",
        "button:contains('Download')",
        "a[href*='download']",
        ".btn-download",
        "input[value*='Download']"
    ]
    
    # Alternative download selectors for different page layouts
    DOWNLOAD_ALTERNATIVES = [
        ".recruiter-options a:contains('Download')",
        ".cv-actions a:contains('Download')",
        ".candidate-actions button:contains('Download')",
        "#download-cv-btn",
        ".download-button"
    ]
    
    def __init__(self, settings: Settings):
        """Initialize download manager."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(
            min_delay=settings.scraping.delay_min,
            max_delay=settings.scraping.delay_max,
            requests_per_minute=settings.scraping.requests_per_minute
        )
        
        # Download tracking
        self.downloaded_cvs = []
        self.failed_downloads = []
        self.download_count = 0
        self.target_quantity = settings.download.max_quantity
        
        # File management (defer directory creation)
        self.download_path = Path(settings.download.download_path)
        self._directory_created = False
        
    def download_cvs_from_results(self, driver: webdriver.Chrome, 
                                search_results: SearchResultCollection,
                                max_downloads: Optional[int] = None) -> List[CVData]:
        """
        Download CVs from search results with session recovery.
        
        Args:
            driver: Selenium WebDriver instance
            search_results: Collection of search results
            max_downloads: Maximum number of CVs to download (overrides settings)
            
        Returns:
            List of successfully downloaded CVData objects
        """
        try:
            if max_downloads:
                self.target_quantity = max_downloads
                
            self.logger.info(f"🔄 Starting CV downloads for {len(search_results.results)} candidates")
            self.logger.info(f"📊 Target quantity: {self.target_quantity}")
            
            # Get the main window handle
            main_window = driver.current_window_handle
            
            # Process each search result
            for i, result in enumerate(search_results.results):
                if self.download_count >= self.target_quantity:
                    self.logger.info(f"✅ Reached target download quantity: {self.target_quantity}")
                    break
                    
                self.logger.info(f"📥 Processing candidate {i+1}/{len(search_results.results)}: {result.name}")
                
                try:
                    # Check session validity before each download
                    try:
                        driver.current_url  # Test if session is still valid
                    except Exception as session_error:
                        self.logger.warning(f"Session invalid before download {i+1}: {session_error}")
                        self.logger.info("Attempting to recover session...")
                        
                        # Try to recover by navigating back to search results
                        try:
                            # Get available windows
                            available_windows = driver.window_handles
                            if available_windows:
                                # Switch to the first available window
                                driver.switch_to.window(available_windows[0])
                                main_window = available_windows[0]  # Update main window reference
                                
                                # Navigate back to search results (use the profile URL to reconstruct search page)
                                search_base_url = "https://www.cv-library.co.uk/recruiter/candidate-search/results"
                                driver.get(search_base_url)
                                time.sleep(2)
                                
                                self.logger.info("✅ Session recovered, continuing downloads")
                            else:
                                self.logger.error("No browser windows available, cannot recover session")
                                break
                                
                        except Exception as recovery_error:
                            self.logger.error(f"Session recovery failed: {recovery_error}")
                            self.logger.info("Stopping download process due to unrecoverable session")
                            break
                    
                    # Download CV for this candidate
                    cv_data = self._download_single_cv(driver, result, main_window)
                    
                    if cv_data:
                        self.downloaded_cvs.append(cv_data)
                        self.download_count += 1
                        self.logger.info(f"✅ Successfully downloaded CV for {result.name} ({self.download_count}/{self.target_quantity})")
                    else:
                        self.failed_downloads.append(result)
                        self.logger.warning(f"❌ Failed to download CV for {result.name}")
                    
                    # Rate limiting between downloads (optimized for speed)
                    if self.download_count < self.target_quantity:  # Only wait if we have more to do
                        time.sleep(0.5)  # Reduced from 2s to 0.5s for faster processing
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing candidate {result.name}: {e}")
                    self.failed_downloads.append(result)
                    
                    # Check if it's a session-related error
                    if "invalid session id" in str(e).lower() or "no such session" in str(e).lower():
                        self.logger.warning("Session-related error detected, attempting recovery...")
                        try:
                            # Simple recovery attempt
                            available_windows = driver.window_handles
                            if available_windows:
                                driver.switch_to.window(available_windows[0])
                                main_window = available_windows[0]
                                time.sleep(1)
                                continue
                            else:
                                self.logger.error("Cannot recover from session error, stopping downloads")
                                break
                        except:
                            self.logger.error("Session recovery failed, stopping downloads")
                            break
                    
                    continue
            
            self.logger.info(f"🎉 Download session completed!")
            self.logger.info(f"✅ Successfully downloaded: {len(self.downloaded_cvs)} CVs")
            self.logger.info(f"❌ Failed downloads: {len(self.failed_downloads)} CVs")
            
            return self.downloaded_cvs
            
        except Exception as e:
            self.logger.error(f"❌ Download process failed: {e}")
            return self.downloaded_cvs
    
    def _download_single_cv(self, driver: webdriver.Chrome, 
                          search_result: SearchResult, 
                          main_window: str) -> Optional[CVData]:
        """
        Download CV for a single candidate with optimized speed and timing instrumentation.
        
        Args:
            driver: Selenium WebDriver instance
            search_result: Search result for the candidate
            main_window: Handle of the main search results window
            
        Returns:
            CVData object if successful, None otherwise
        """
        try:
            step_start = time.time()
            total_start = time.time()
            
            # Step 1: Open CV profile (optimized)
            self.logger.info(f"Step 1: Opening CV profile for {search_result.name}")
            
            if not self._click_view_cv_button(search_result, driver):
                self.logger.error(f"Could not open CV profile for {search_result.name}")
                return None
            
            step1_time = time.time() - step_start
            self.logger.debug(f"⏱️ Step 1 completed in {step1_time:.2f}s")
            
            # Step 2: Switch to the new tab (optimized wait)
            step_start = time.time()
            self.logger.info("Step 2: Switching to candidate profile tab")
            
            if not self._switch_to_candidate_tab(driver, main_window):
                self.logger.error("Failed to switch to candidate profile tab")
                return None
            
            step2_time = time.time() - step_start
            self.logger.debug(f"⏱️ Step 2 completed in {step2_time:.2f}s")
            
            # Step 3: Fast extraction of candidate information
            step_start = time.time()
            self.logger.info("Step 3: Extracting candidate information")
            candidate_info = self._extract_candidate_details(driver)
            
            step3_time = time.time() - step_start
            self.logger.debug(f"⏱️ Step 3 completed in {step3_time:.2f}s")
            
            # Step 4: Download the CV (optimized)
            step_start = time.time()
            self.logger.info("Step 4: Downloading CV file")
            download_success = self._click_download_cv_button(driver)
            
            # Step 4.5: Wait for download to complete if download was initiated
            if download_success:
                self.logger.info("Step 4.5: Waiting for download completion...")
                download_completed = self._wait_for_download_completion(timeout=5)
                if not download_completed:
                    self.logger.warning("Download may not have completed within timeout")
            
            step4_time = time.time() - step_start
            self.logger.debug(f"⏱️ Step 4 completed in {step4_time:.2f}s")
            
            # Step 5: Quick return to main window
            step_start = time.time()
            self.logger.info("Step 5: Returning to search results")
            self._close_tab_and_return(driver, main_window)
            
            step5_time = time.time() - step_start
            total_time = time.time() - total_start
            self.logger.info(f"⏱️ Step 5 completed in {step5_time:.2f}s | Total: {total_time:.2f}s")
            
            # Create result regardless of download success (we still got candidate info)
            cv_data = CVData(
                cv_id=search_result.cv_id,
                candidate=candidate_info,  # Use 'candidate' instead of 'candidate_info'
                search_keywords=search_result.search_keywords,
                search_location=search_result.location,
                url=search_result.profile_url,  # Use 'url' instead of 'cv_url'
                download_status="completed" if download_success else "failed",
                download_timestamp=datetime.now() if download_success else None,
                file_path=self.download_path if download_success else None
            )
            
            # Save candidate data to file (this is valuable even if CV download failed)
            try:
                self._ensure_download_directory()
                candidate_data_file = self.download_path / f"candidate_{search_result.cv_id}_{int(time.time())}.json"
                
                # Ensure data consistency between search_result and candidate_info
                consistent_location = candidate_info.location or search_result.location
                consistent_name = candidate_info.name if candidate_info.name != "Unknown" else search_result.name
                
                # Get salary from candidate_info if available, otherwise from search_result
                consistent_salary = candidate_info.salary_expectation or search_result.salary
                
                # Prepare comprehensive candidate data with improved consistency
                candidate_data = {
                    'search_result': {
                        # ONLY the 7 essential fields from search cards
                        'cv_id': search_result.cv_id,
                        'name': search_result.name,
                        'search_rank': search_result.search_rank,
                        'profile_url': search_result.profile_url,
                        'profile_match_percentage': search_result.profile_match_percentage,
                        'profile_cv_last_updated': search_result.profile_cv_last_updated,
                        'last_viewed_date': search_result.last_viewed_date,
                        'search_keywords': search_result.search_keywords if search_result.search_keywords else []
                    },
                    'candidate_info': {
                        # Essential identification
                        'name': consistent_name,
                        'quickview_ref': candidate_info.quickview_ref,
                        
                        # Profile metadata (from top of profile page)
                        'date_registered': candidate_info.date_registered,
                        'profile_last_updated': candidate_info.profile_last_updated,
                        'last_active': candidate_info.last_active,  # Fix: use last_active instead of last_active_date
                        
                        # Personal & Job Details table (as shown in the interface)
                        'personal_job_details': {
                            'town': candidate_info.town,
                            'county': candidate_info.county,
                            'location': consistent_location,
                            'main_phone': candidate_info.main_phone,
                            'optional_phone': candidate_info.optional_phone,
                            'email': candidate_info.email,
                            'current_job_title': candidate_info.current_job_title,
                            'desired_job_title': candidate_info.desired_job_title,
                            'job_type': candidate_info.job_type,
                            'willing_to_travel': candidate_info.willing_to_travel,
                            'willing_to_relocate': candidate_info.willing_to_relocate,
                            'uk_driving_licence': candidate_info.uk_driving_licence,
                            'date_available': candidate_info.date_available,
                            'fluent_languages': candidate_info.fluent_languages if candidate_info.fluent_languages else [],
                            'expected_salary': candidate_info.expected_salary
                        },
                        
                        # Professional sections (as shown in the interface)
                        'candidates_chosen_industries': candidate_info.chosen_industries if candidate_info.chosen_industries else [],
                        'candidates_main_skills': candidate_info.main_skills if candidate_info.main_skills else []
                    }
                }
                
                with open(candidate_data_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(candidate_data, f, indent=2, ensure_ascii=False)
                    
                self.logger.info(f"✅ Saved enhanced candidate data to: {candidate_data_file}")
                
                # Log data quality summary
                quality_score = candidate_data['metadata']['data_quality']['data_completeness']
                self.logger.info(f"📊 Data quality score: {quality_score:.2f} | Name: {consistent_name} | Location: {consistent_location}")
                
            except Exception as save_error:
                self.logger.warning(f"Could not save candidate data: {save_error}")
            
            # Update rate limiter based on success
            if download_success:
                self.rate_limiter.on_success()
                self.logger.info(f"✅ Successfully processed {search_result.name}")
            else:
                self.rate_limiter.on_error()
                self.logger.warning(f"⚠️ Extracted data but failed to download CV for {search_result.name}")
            
            return cv_data
                
        except Exception as e:
            self.logger.error(f"Error processing CV for {search_result.name}: {e}")
            # Ensure we return to main window even if there's an error
            try:
                self._close_tab_and_return(driver, main_window)
            except:
                pass
            return None
    
    def _click_view_cv_button(self, search_result: SearchResult, driver: webdriver.Chrome) -> bool:
        """
        Navigate to CV profile using the most reliable method available.
        
        Args:
            search_result: SearchResult object containing profile URL
            driver: Selenium WebDriver instance
            
        Returns:
            True if profile opened successfully, False otherwise
        """
        try:
            if search_result.profile_url:
                # Method 1: Direct URL navigation (most reliable)
                self.logger.info(f"Opening CV profile via direct URL: {search_result.cv_id}")
                driver.execute_script(f"window.open('{search_result.profile_url}', '_blank');")
                
                # Reduced wait for new tab to open - from 1s to 0.3s
                time.sleep(0.3)
                
                # Verify new tab opened
                if len(driver.window_handles) > 1:
                    return True
                else:
                    self.logger.warning("New tab did not open, trying alternative method")
                    
            # Method 2: Fallback - try to find and click view CV button on current page
            try:
                view_cv_selectors = [
                    f"a[href*='{search_result.cv_id}']",  # Link containing CV ID
                    "a:contains('View CV')",
                    ".view-cv",
                    "a[href*='/cv/']"
                ]
                
                for selector in view_cv_selectors:
                    try:
                        # Skip text-based selectors for now (not supported by CSS)
                        if ":contains(" in selector:
                            continue
                            
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                # Check if this element is related to our specific CV
                                href = element.get_attribute('href')
                                if href and search_result.cv_id in href:
                                    # Open in new tab using JavaScript
                                    driver.execute_script("arguments[0].target='_blank'; arguments[0].click();", element)
                                    time.sleep(1)
                                    
                                    if len(driver.window_handles) > 1:
                                        return True
                    except Exception as e:
                        self.logger.debug(f"Selector {selector} failed: {e}")
                        continue
                        
            except Exception as fallback_error:
                self.logger.debug(f"Fallback method failed: {fallback_error}")
            
            # Method 3: Last resort - direct navigation in same tab (not ideal but works)
            if search_result.profile_url:
                self.logger.warning("Using direct navigation as last resort")
                driver.get(search_result.profile_url)
                time.sleep(2)
                return True
                
            self.logger.error(f"All methods failed to open CV profile for {search_result.name}")
            return False
                
        except Exception as e:
            self.logger.error(f"Failed to open CV profile: {e}")
            return False
    
    def _switch_to_candidate_tab(self, driver: webdriver.Chrome, main_window: str) -> bool:
        """
        Switch to the newly opened candidate profile tab with optimized speed.
        
        Args:
            driver: Selenium WebDriver instance
            main_window: Handle of the main window
            
        Returns:
            True if successfully switched, False otherwise
        """
        try:
            # Wait for new tab to open (much shorter timeout)
            WebDriverWait(driver, 3).until(lambda d: len(d.window_handles) > 1)
            
            # Find the new tab
            all_windows = driver.window_handles
            for window in all_windows:
                if window != main_window:
                    driver.switch_to.window(window)
                    self.logger.info("✅ Switched to candidate profile tab")
                    
                    # Minimal wait for basic page load - reduced from 1s to 0.3s
                    time.sleep(0.3)
                    
                    return True
            
            self.logger.error("Could not find new tab")
            return False
            
        except TimeoutException:
            self.logger.error("Timeout waiting for new tab to open")
            return False
        except Exception as e:
            self.logger.error(f"Error switching to candidate tab: {e}")
            return False
    
    def _extract_candidate_details(self, driver: webdriver.Chrome) -> CandidateInfo:
        """
        Extract comprehensive candidate information from the CV-Library profile page with enhanced debugging.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            CandidateInfo object with extracted details
        """
        try:
            self.logger.info("🔍 Starting comprehensive candidate details extraction with debugging...")
            
            # Save the profile page HTML for debugging
            try:
                self._ensure_download_directory()
                debug_html_path = self.download_path / "debug_profile_page.html"
                with open(debug_html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                self.logger.info(f"📄 Saved profile page HTML for debugging: {debug_html_path}")
            except Exception as e:
                self.logger.warning(f"Could not save debug HTML: {e}")
            
            # Get both page source and page text for more robust extraction
            page_text = driver.page_source
            visible_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Save visible text for debugging
            try:
                debug_text_path = self.download_path / "debug_profile_text.txt"
                with open(debug_text_path, 'w', encoding='utf-8') as f:
                    f.write(visible_text)
                self.logger.info(f"📄 Saved visible text for debugging: {debug_text_path}")
            except Exception as e:
                self.logger.warning(f"Could not save debug text: {e}")
            
            # Initialize all fields for comprehensive extraction
            extracted_data = {
                'name': "Unknown",
                'title': None,
                'current_job_title': None,
                'desired_job_title': None,
                'town': None,
                'county': None,
                'location': None,
                'main_phone': None,
                'optional_phone': None,
                'email': None,
                'salary_expectation': None,
                'expected_salary': None,
                'job_type': None,
                'willing_to_travel': None,
                'willing_to_relocate': None,
                'uk_driving_licence': None,
                'date_available': None,
                'fluent_languages': [],
                'chosen_industries': [],
                'main_skills': [],
                'skills': [],
                'cv_keywords': None,
                'profile_last_updated': None,
                'date_registered': None,
                'last_viewed_date': None,
                'quickview_ref': None,
                'profile_match_percentage': None,
                'contact_info': {}
            }
            
            self.logger.info("🧑 === EXTRACTING CANDIDATE NAME ===")
            # Extract candidate name (multiple methods)
            try:
                # Method 1: From page title
                page_title = driver.title
                self.logger.debug(f"🔍 Page title: {page_title}")
                if " - " in page_title:
                    potential_name = page_title.split(" - ")[0].strip()
                    if len(potential_name) > 3 and len(potential_name) < 50:
                        extracted_data['name'] = potential_name
                        self.logger.info(f"✅ Extracted name from title: {extracted_data['name']}")
                
                # Method 2: From h1 or main heading
                if extracted_data['name'] == "Unknown":
                    try:
                        headings = driver.find_elements(By.CSS_SELECTOR, "h1, h2, .candidate-name, .profile-name")
                        self.logger.debug(f"🔍 Found {len(headings)} heading elements")
                        for i, heading in enumerate(headings):
                            heading_text = heading.text.strip()
                            self.logger.debug(f"🔍 Heading {i+1}: '{heading_text}'")
                            if (heading_text and len(heading_text) > 3 and len(heading_text) < 60 and
                                not heading_text.lower().startswith(('cv for', 'profile', 'candidate'))):
                                extracted_data['name'] = heading_text
                                self.logger.info(f"✅ Extracted name from heading: {extracted_data['name']}")
                                break
                    except Exception as e:
                        self.logger.debug(f"❌ Error extracting from headings: {e}")
                        
            except Exception as e:
                self.logger.warning(f"❌ Error extracting candidate name: {e}")
                extracted_data['name'] = "Unknown"
            
            self.logger.info("🏢 === EXTRACTING JOB DETAILS ===")
            # Enhanced extraction using comprehensive patterns
            try:
                # Extract job titles (both current and desired)
                title_patterns = [
                    (r'Current Job Title[:\s]*([^<\n\r]+?)(?=\s*Desired|County|$)', 'current_job_title'),
                    (r'Desired Job Title[:\s]*([^<\n\r]+?)(?=\s*Job Type|County|$)', 'desired_job_title'),
                    (r'Job Title[:\s]*([^<\n\r]+?)(?=\s*Willing|County|$)', 'title'),
                ]
                
                for pattern, field_name in title_patterns:
                    title_match = re.search(pattern, visible_text, re.IGNORECASE | re.MULTILINE)
                    if title_match:
                        potential_title = title_match.group(1).strip()
                        self.logger.debug(f"🔍 Found {field_name} match: '{potential_title}'")
                        # Filter out CSS/HTML artifacts
                        if (potential_title and 
                            not re.search(r'^\d+px|;$|^#|class=|style=', potential_title) and
                            len(potential_title) > 3 and len(potential_title) < 100):
                            extracted_data[field_name] = potential_title
                            if field_name == 'current_job_title':
                                extracted_data['title'] = potential_title  # Use current job title as main title
                            self.logger.info(f"✅ Extracted {field_name}: {extracted_data[field_name]}")
                
                self.logger.info("📍 === EXTRACTING LOCATION INFORMATION ===")
                # Extract location information (town and county)
                location_patterns = [
                    (r'Town[:\s]*([^<\n\r]+?)(?=\s*County|Main Phone|$)', 'town'),
                    (r'County[:\s]*([^<\n\r]+?)(?=\s*Main Phone|Current|$)', 'county'),
                ]
                
                for pattern, field_name in location_patterns:
                    location_match = re.search(pattern, visible_text, re.IGNORECASE)
                    if location_match:
                        potential_location = location_match.group(1).strip()
                        self.logger.debug(f"🔍 Found {field_name} match: '{potential_location}'")
                        # Filter out HTML/CSS artifacts
                        if (potential_location and 
                            not re.search(r'^html|lang|px|;$|^#|class=|style=', potential_location) and
                            len(potential_location) > 2 and len(potential_location) < 50):
                            extracted_data[field_name] = potential_location
                            self.logger.info(f"✅ Extracted {field_name}: {extracted_data[field_name]}")
                
                # Combine town and county for full location
                if extracted_data['town'] and extracted_data['county']:
                    extracted_data['location'] = f"{extracted_data['town']}, {extracted_data['county']}"
                elif extracted_data['town']:
                    extracted_data['location'] = extracted_data['town']
                elif extracted_data['county']:
                    extracted_data['location'] = extracted_data['county']
                
                self.logger.info(f"✅ Final location: {extracted_data['location']}")
                
                self.logger.info("📞 === EXTRACTING CONTACT INFORMATION ===")
                # Extract contact information by clicking "View contact details" links
                # Note: CV-Library reveals ALL contact info when clicking any "View contact details" link
                contact_revealed = False
                updated_page_text = visible_text
                
                # Try to click any "View contact details" link to reveal all contact information
                try:
                    self.logger.debug("🔍 Looking for any 'View contact details' link...")
                    
                    contact_link_selectors = [
                        "//a[contains(text(), 'View contact details')]",
                        "//button[contains(text(), 'View contact details')]",
                        "//*[contains(text(), 'View contact details')]"
                    ]
                    
                    contact_link = None
                    for selector in contact_link_selectors:
                        try:
                            elements = driver.find_elements(By.XPATH, selector)
                            if elements:
                                contact_link = elements[0]
                                self.logger.debug("✅ Found contact details link")
                                break
                        except Exception as e:
                            self.logger.debug(f"❌ Selector failed: {e}")
                            continue
                    
                    if contact_link:
                        try:
                            # Get initial page content for comparison
                            initial_text = driver.find_element(By.TAG_NAME, "body").text
                            
                            # Scroll to the element and click it
                            driver.execute_script("arguments[0].scrollIntoView(true);", contact_link)
                            time.sleep(0.5)
                            
                            # Click the link to reveal ALL contact details
                            contact_link.click()
                            time.sleep(2)  # Wait for the contact details to load
                            
                            # Get updated page content
                            updated_page_text = driver.find_element(By.TAG_NAME, "body").text
                            contact_revealed = True
                            
                            self.logger.debug("✅ Successfully clicked contact details link - all contact info should now be revealed")
                            
                            # Save the revealed content for debugging
                            try:
                                debug_revealed_path = self.download_path / "debug_revealed_all_contacts.txt"
                                with open(debug_revealed_path, 'w', encoding='utf-8') as f:
                                    f.write(f"=== INITIAL CONTENT ===\n{initial_text}\n\n")
                                    f.write(f"=== UPDATED CONTENT ===\n{updated_page_text}")
                                self.logger.debug(f"📄 Saved revealed contact content: {debug_revealed_path}")
                            except Exception as e:
                                self.logger.debug(f"Could not save revealed content: {e}")
                                
                        except Exception as e:
                            self.logger.debug(f"❌ Error clicking contact link: {e}")
                    else:
                        self.logger.debug("❌ No contact details link found")
                        
                except Exception as e:
                    self.logger.debug(f"❌ Error in contact link detection: {e}")
                
                # Now extract ALL contact information from the updated page content
                contact_fields = [
                    ('Main Phone', 'main_phone'),
                    ('Optional Phone', 'optional_phone'),
                    ('Email', 'email')
                ]
                
                for field_label, field_key in contact_fields:
                    try:
                        self.logger.debug(f"🔍 Extracting {field_label} from revealed content...")
                        
                        if field_key == 'email':
                            # Enhanced email extraction patterns
                            email_patterns = [
                                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                                r'[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                            ]
                            
                            # Look in the updated page text and specific email-containing elements
                            search_texts = [updated_page_text]
                            
                            # Also try to find email in specific elements that might have been revealed
                            try:
                                email_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '@')]")
                                for elem in email_elements:
                                    elem_text = elem.text.strip()
                                    if elem_text and '@' in elem_text:
                                        search_texts.append(elem_text)
                                        search_texts.append(elem.get_attribute('textContent') or '')
                            except Exception:
                                pass
                            
                            for search_text in search_texts:
                                if not search_text:
                                    continue
                                    
                                for pattern in email_patterns:
                                    email_matches = re.findall(pattern, search_text)
                                    for email in email_matches:
                                        email = email.strip()
                                        # Filter out CV-Library system emails and check validity
                                        if (email and '@' in email and '.' in email and
                                            not any(domain in email.lower() for domain in 
                                                   ['cv-library', 'aspirepeople', 'noreply', 'no-reply', 'system', 'admin']) and
                                            len(email) > 5 and len(email) < 100):
                                            extracted_data[field_key] = email
                                            extracted_data['contact_info'][field_key] = email
                                            self.logger.info(f"✅ Extracted {field_label}: {email}")
                                            break
                                    if extracted_data[field_key]:
                                        break
                                if extracted_data[field_key]:
                                    break
                                    
                        elif field_key in ['main_phone', 'optional_phone']:
                            # Enhanced phone extraction patterns
                            phone_patterns = [
                                r'\+44\s?\d{1,4}\s?\d{3,4}\s?\d{3,4}',  # UK format with +44
                                r'0\d{1,4}\s?\d{3,4}\s?\d{3,4}',       # UK format starting with 0
                                r'\(\d{3,5}\)\s?\d{3,4}\s?\d{3,4}',    # Format with area code in brackets
                                r'\d{4,5}\s?\d{3,4}\s?\d{3,4}',        # General format
                                r'\+\d{1,3}\s?\d{3,4}\s?\d{3,4}\s?\d{3,4}',  # International format
                                r'\d{11}',  # 11-digit UK mobile
                                r'\d{5}\s?\d{6}',  # 5+6 digit format
                                r'\d{4}\s?\d{3}\s?\d{4}'  # 4+3+4 format
                            ]
                            
                            # Look for phone numbers in the updated content
                            search_texts = [updated_page_text]
                            
                            # Also try to find phone numbers in specific elements
                            try:
                                phone_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '0') or contains(text(), '+') or contains(text(), '44')]")
                                for elem in phone_elements:
                                    elem_text = elem.text.strip()
                                    if elem_text and (elem_text.startswith(('0', '+', '44')) or any(char.isdigit() for char in elem_text)):
                                        search_texts.append(elem_text)
                            except Exception:
                                pass
                            
                            for search_text in search_texts:
                                if not search_text:
                                    continue
                                    
                                for pattern in phone_patterns:
                                    phone_matches = re.findall(pattern, search_text)
                                    for phone in phone_matches:
                                        phone = phone.strip()
                                        # Basic validation - must be reasonable length
                                        clean_phone = re.sub(r'[^\d+]', '', phone)
                                        if (phone and len(clean_phone) >= 10 and len(clean_phone) <= 15 and
                                            not phone.startswith(('2025', '2024', '2023')) and  # Filter out years
                                            clean_phone not in ['01012345678', '07123456789']):  # Filter out obvious test numbers
                                            
                                            # For main phone, take the first valid number
                                            # For optional phone, take a different number if main phone already exists
                                            if field_key == 'main_phone' and not extracted_data['main_phone']:
                                                extracted_data[field_key] = phone
                                                extracted_data['contact_info'][field_key] = phone
                                                self.logger.info(f"✅ Extracted {field_label}: {phone}")
                                                break
                                            elif field_key == 'optional_phone' and phone != extracted_data.get('main_phone'):
                                                extracted_data[field_key] = phone
                                                extracted_data['contact_info'][field_key] = phone
                                                self.logger.info(f"✅ Extracted {field_label}: {phone}")
                                                break
                                    if extracted_data[field_key]:
                                        break
                                if extracted_data[field_key]:
                                    break
                                    
                    except Exception as e:
                        self.logger.debug(f"❌ Error extracting {field_label}: {e}")
                
                # Look for additional contact information that might be visible
                self.logger.debug("🔍 Looking for additional contact information...")
                
                # LinkedIn profile
                try:
                    linkedin_patterns = [
                        r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+',
                        r'linkedin\.com/in/[a-zA-Z0-9-]+',
                        r'LinkedIn:\s*([^\s\n]+)',
                        r'linkedin:\s*([^\s\n]+)'
                    ]
                    
                    for pattern in linkedin_patterns:
                        linkedin_match = re.search(pattern, updated_page_text, re.IGNORECASE)
                        if linkedin_match:
                            linkedin_url = linkedin_match.group(0) if linkedin_match.group(0).startswith('http') else f"https://{linkedin_match.group(0)}"
                            extracted_data['contact_info']['linkedin'] = linkedin_url
                            self.logger.info(f"✅ Extracted LinkedIn: {linkedin_url}")
                            break
                except Exception as e:
                    self.logger.debug(f"❌ Error extracting LinkedIn: {e}")
                
                # Website/Portfolio
                try:
                    website_patterns = [
                        r'https?://(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?',
                        r'Portfolio:\s*(https?://[^\s\n]+)',
                        r'Website:\s*(https?://[^\s\n]+)'
                    ]
                    
                    for pattern in website_patterns:
                        website_matches = re.findall(pattern, updated_page_text, re.IGNORECASE)
                        for website in website_matches:
                            if not any(domain in website.lower() for domain in ['cv-library', 'linkedin']):
                                extracted_data['contact_info']['website'] = website
                                self.logger.info(f"✅ Extracted Website: {website}")
                                break
                        if 'website' in extracted_data['contact_info']:
                            break
                except Exception as e:
                    self.logger.debug(f"❌ Error extracting website: {e}")
                
                # GitHub profile
                try:
                    github_patterns = [
                        r'https?://(?:www\.)?github\.com/[a-zA-Z0-9-]+',
                        r'github\.com/[a-zA-Z0-9-]+',
                        r'GitHub:\s*([^\s\n]+)',
                        r'github:\s*([^\s\n]+)'
                    ]
                    
                    for pattern in github_patterns:
                        github_match = re.search(pattern, updated_page_text, re.IGNORECASE)
                        if github_match:
                            github_url = github_match.group(0) if github_match.group(0).startswith('http') else f"https://{github_match.group(0)}"
                            extracted_data['contact_info']['github'] = github_url
                            self.logger.info(f"✅ Extracted GitHub: {github_url}")
                            break
                except Exception as e:
                    self.logger.debug(f"❌ Error extracting GitHub: {e}")
                
                # Fallback: Try to extract contact info from visible text patterns if nothing was revealed
                if not any([extracted_data['main_phone'], extracted_data['optional_phone'], extracted_data['email']]):
                    self.logger.debug("🔄 Trying fallback contact extraction from visible text...")
                    
                    # Email fallback
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', visible_text)
                    if email_match:
                        email = email_match.group(0)
                        if not any(domain in email.lower() for domain in ['cv-library', 'noreply']):
                            extracted_data['email'] = email
                            extracted_data['contact_info']['email'] = email
                            self.logger.info(f"✅ Extracted email (fallback): {email}")
                    
                    # Phone fallback
                    phone_match = re.search(r'(\+44\s?\d{1,4}\s?\d{3,4}\s?\d{3,4}|0\d{1,4}\s?\d{3,4}\s?\d{3,4})', visible_text)
                    if phone_match:
                        phone = phone_match.group(0)
                        extracted_data['main_phone'] = phone
                        extracted_data['contact_info']['main_phone'] = phone
                        self.logger.info(f"✅ Extracted phone (fallback): {phone}")
                
                # Log final contact info summary
                if extracted_data['contact_info']:
                    self.logger.info(f"📞 Final contact info extracted: {list(extracted_data['contact_info'].keys())}")
                else:
                    self.logger.info("📞 No contact information could be extracted")
                
                self.logger.info("💼 === EXTRACTING JOB PREFERENCES ===")
                # Extract job preferences
                job_pref_patterns = [
                    (r'Job Type[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Willing|UK|$)', 'job_type'),
                    (r'Willing to Travel[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Willing to Relocate|UK|$)', 'willing_to_travel'),
                    (r'Willing to Relocate[:\s]*\n?\s*([^<\n\r]+?)(?=\s*UK|Date|$)', 'willing_to_relocate'),
                    (r'UK Driving Licence[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Expected|Date|Fluent|Candidates|$)', 'uk_driving_licence'),
                    (r'Date Available[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Expected|Fluent|$)', 'date_available'),
                    (r'Expected Salary[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Fluent|Candidates|$)', 'expected_salary'),
                    (r'Fluent Languages[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Candidates|$)', 'fluent_languages'),
                    # Additional patterns for better extraction
                    (r'Date Registered[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Profile|Last|$)', 'date_registered'),
                    (r'Profile/CV Last Updated[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Last Active|$)', 'profile_last_updated'),
                    (r'Last Active[:\s]*\n?\s*([^<\n\r]+?)(?=\s*Personal|$)', 'last_active'),
                    (r'Quickview Ref#?[:\s]*\n?\s*(\d+)', 'quickview_ref'),
                ]
                
                for pattern, field_name in job_pref_patterns:
                    pref_match = re.search(pattern, visible_text, re.IGNORECASE)
                    if pref_match:
                        pref_value = pref_match.group(1).strip()
                        self.logger.debug(f"🔍 Found {field_name} match: '{pref_value}'")
                        if field_name == 'fluent_languages':
                            extracted_data[field_name] = [lang.strip() for lang in pref_value.split(',') if lang.strip()]
                        elif field_name == 'expected_salary':
                            extracted_data[field_name] = pref_value
                            extracted_data['salary_expectation'] = pref_value  # For compatibility
                        elif field_name == 'profile_last_updated':
                            extracted_data['profile_last_updated'] = pref_value
                            extracted_data['profile_cv_last_updated'] = pref_value  # For compatibility
                        elif field_name == 'last_active':
                            extracted_data['last_active'] = pref_value
                            extracted_data['last_active_date'] = pref_value  # For compatibility
                        elif field_name == 'quickview_ref':
                            extracted_data['quickview_ref'] = pref_value
                        else:
                            extracted_data[field_name] = pref_value
                        self.logger.info(f"✅ Extracted {field_name}: {extracted_data[field_name]}")
                        
                        # Clean up N/A values
                        if extracted_data.get(field_name) and extracted_data[field_name].upper() in ['N/A', 'NOT SPECIFIED', 'NONE']:
                            extracted_data[field_name] = None
                
                self.logger.info("🛠️ === EXTRACTING PROFESSIONAL DETAILS ===")
                # Extract professional details with enhanced debugging
                prof_patterns = [
                    (r'Candidates Chosen Industries[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=Candidates\s*Main\s*Skills|$)', 'chosen_industries'),
                    (r'Candidates Main Skills[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=CV\s*Keywords|Document|$)', 'main_skills'),
                    (r'CV Keywords[:\s]*([^\n\r]+(?:\n[^\n\r]+)*?)(?=Experienced|Role|$)', 'cv_keywords'),
                ]
                
                # Also try to find these sections using DOM elements and direct text parsing
                try:
                    # Extract main skills from the text structure we see in debug
                    # Looking for the pattern after "Candidates Main Skills"
                    main_skills_start = visible_text.find("Candidates Main Skills")
                    if main_skills_start != -1:
                        # Get text after "Candidates Main Skills"
                        after_main_skills = visible_text[main_skills_start + len("Candidates Main Skills"):]
                        # Find where it ends (at "Recruiter Options" or similar)
                        end_markers = ["Recruiter Options", "Download CV", "Document", "Plain Text"]
                        skills_end = len(after_main_skills)
                        for marker in end_markers:
                            marker_pos = after_main_skills.find(marker)
                            if marker_pos != -1 and marker_pos < skills_end:
                                skills_end = marker_pos
                        
                        skills_text = after_main_skills[:skills_end].strip()
                        self.logger.debug(f"🔍 Raw skills text: '{skills_text[:200]}...'")
                        
                        # Split by newlines and filter valid skills
                        if skills_text:
                            skill_lines = [line.strip() for line in skills_text.split('\n') if line.strip()]
                            valid_skills = []
                            for skill in skill_lines:
                                # Filter out UI elements and keep actual skills
                                if (skill and len(skill) > 2 and len(skill) < 50 and
                                    not skill.lower() in ['recruiter options', 'download cv', 'video interview', 
                                                         'email cv', 'add note', 'save cv', 'print cv', 'report',
                                                         'document', 'plain text', 'notes', 'view contact'] and
                                    not skill.startswith(('http', 'www', 'The contact'))):
                                    valid_skills.append(skill)
                            
                            if valid_skills and not extracted_data['main_skills']:
                                extracted_data['main_skills'] = valid_skills[:15]  # Limit to 15
                                self.logger.info(f"✅ Extracted main_skills from text parsing: {extracted_data['main_skills']}")
                
                    # Extract chosen industries similarly
                    industries_start = visible_text.find("Candidates Chosen Industries")
                    if industries_start != -1:
                        after_industries = visible_text[industries_start + len("Candidates Chosen Industries"):]
                        # Find where it ends (at "Candidates Main Skills")
                        industries_end = after_industries.find("Candidates Main Skills")
                        if industries_end == -1:
                            industries_end = 100  # Fallback
                        
                        industries_text = after_industries[:industries_end].strip()
                        self.logger.debug(f"🔍 Raw industries text: '{industries_text}'")
                        
                        if industries_text:
                            industry_lines = [line.strip() for line in industries_text.split('\n') 
                                            if line.strip() and len(line.strip()) > 2]
                            if industry_lines and not extracted_data['chosen_industries']:
                                extracted_data['chosen_industries'] = industry_lines[:10]  # Limit to 10
                                self.logger.info(f"✅ Extracted chosen_industries from text parsing: {extracted_data['chosen_industries']}")
                
                    # Look for skills sections using DOM elements
                    skills_sections = driver.find_elements(By.CSS_SELECTOR, 
                        ".candidate-skills, .main-skills, [class*='skill'], .skills-list, .skills")
                    self.logger.debug(f"🔍 Found {len(skills_sections)} potential skills sections")
                    
                    for i, section in enumerate(skills_sections):
                        section_text = section.text.strip()
                        if section_text and len(section_text) > 5:
                            self.logger.debug(f"🔍 Skills section {i+1}: '{section_text[:100]}...'")
                            
                except Exception as e:
                    self.logger.debug(f"❌ Error extracting skills from text parsing: {e}")
                
                # Extract using regex patterns as fallback
                for pattern, field_name in prof_patterns:
                    prof_match = re.search(pattern, visible_text, re.IGNORECASE | re.DOTALL)
                    if prof_match:
                        prof_value = prof_match.group(1).strip()
                        self.logger.debug(f"🔍 Found {field_name} match: '{prof_value[:100]}...'")
                        if field_name in ['chosen_industries', 'main_skills']:
                            extracted_items = [item.strip() for item in re.split(r'[,\n\r]', prof_value) if item.strip()]
                            if not extracted_data[field_name]:  # Only update if not already extracted
                                extracted_data[field_name] = extracted_items
                                self.logger.info(f"✅ Extracted {field_name}: {extracted_data[field_name]}")
                        else:
                            extracted_data[field_name] = prof_value
                            self.logger.info(f"✅ Extracted {field_name}: {extracted_data[field_name][:100]}...")
                
                # Enhanced salary extraction - we saw "Expected Salary" in the text
                if not extracted_data['expected_salary']:
                    salary_start = visible_text.find("Expected Salary")
                    if salary_start != -1:
                        after_salary = visible_text[salary_start + len("Expected Salary"):]
                        # Look for the next few lines
                        salary_lines = after_salary.split('\n')[:3]  # Check next 3 lines
                        for line in salary_lines:
                            line = line.strip()
                            if line and '£' in line and len(line) < 50:
                                extracted_data['expected_salary'] = line
                                extracted_data['salary_expectation'] = line  # For compatibility
                                self.logger.info(f"✅ Extracted expected_salary from text: {extracted_data['expected_salary']}")
                                break
                
                self.logger.info("📅 === EXTRACTING PROFILE METADATA ===")
                # Extract profile metadata
                metadata_patterns = [
                    (r'Date Registered[:\s]*([^<\n\r]+?)(?=\s*Profile|Last|$)', 'date_registered'),
                    (r'Profile/CV Last Updated[:\s]*([^<\n\r]+?)(?=\s*Last|$)', 'profile_last_updated'),
                    (r'Last Active[:\s]*([^<\n\r]+?)(?=\s*$)', 'last_viewed_date'),
                    (r'Quickview Ref[#\s]*(\d+)', 'quickview_ref'),
                    (r'(\d+%\s*Match)', 'profile_match_percentage'),
                ]
                
                for pattern, field_name in metadata_patterns:
                    meta_match = re.search(pattern, visible_text, re.IGNORECASE)
                    if meta_match:
                        meta_value = meta_match.group(1).strip()
                        self.logger.debug(f"🔍 Found {field_name} match: '{meta_value}'")
                        extracted_data[field_name] = meta_value
                        self.logger.info(f"✅ Extracted {field_name}: {extracted_data[field_name]}")
                
                self.logger.info("🔧 === FALLBACK SKILLS EXTRACTION ===")
                # Fallback skills extraction if main_skills is empty
                if not extracted_data['main_skills']:
                    self.logger.info("🔄 No main_skills found, trying fallback extraction...")
                    skill_sources = [visible_text, page_text]
                    
                    essential_skills = [
                        "Python", "Java", "JavaScript", "React", "Angular", "Vue", "Node.js", "TypeScript",
                        "SQL", "MySQL", "PostgreSQL", "MongoDB", "AWS", "Azure", "GCP", "Docker", 
                        "Kubernetes", "Git", "Jenkins", "CI/CD", "Linux", "Windows", "HTML", "CSS",
                        "PHP", "Ruby", "Go", "Swift", "Kotlin", "C++", "C#", ".NET", "Django", "Flask",
                        "Spring", "Laravel", "Express", "Redux", "GraphQL", "REST", "API", "pandas",
                        "NumPy", "Terraform", "Ansible", "Redis", "ElasticSearch", "Kafka"
                    ]
                    
                    found_skills = set()
                    for source in skill_sources:
                        if source:
                            # Look for exact skill matches
                            for skill in essential_skills:
                                if re.search(rf'\b{re.escape(skill)}\b', source, re.IGNORECASE):
                                    found_skills.add(skill)
                    
                    extracted_data['skills'] = list(found_skills)[:15]  # Limit to 15 skills
                    self.logger.info(f"✅ Fallback skills extraction: {extracted_data['skills']}")
                
                # Combine main_skills and skills for comprehensive list
                all_skills = list(set(extracted_data['main_skills'] + extracted_data['skills']))  # Remove duplicates
                extracted_data['skills'] = all_skills
                self.logger.info(f"✅ Final combined skills: {len(all_skills)} total")
                        
            except Exception as e:
                self.logger.error(f"❌ Error in detailed extraction: {e}")
                import traceback
                self.logger.debug(f"❌ Traceback: {traceback.format_exc()}")
            
            # Log extraction summary
            self.logger.info("📊 === EXTRACTION SUMMARY ===")
            for key, value in extracted_data.items():
                if isinstance(value, list):
                    self.logger.info(f"🔸 {key}: {len(value)} items")
                elif value:
                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    self.logger.info(f"🔸 {key}: {display_value}")
                else:
                    self.logger.info(f"🔸 {key}: None/Empty")
            
            # Create comprehensive CandidateInfo with all extracted data
            candidate_info = CandidateInfo(
                name=extracted_data['name'],
                title=extracted_data['title'],
                current_job_title=extracted_data['current_job_title'],
                desired_job_title=extracted_data['desired_job_title'],
                town=extracted_data['town'],
                county=extracted_data['county'],
                location=extracted_data['location'],
                main_phone=extracted_data['main_phone'],
                optional_phone=extracted_data['optional_phone'],
                email=extracted_data['email'],
                salary_expectation=extracted_data['salary_expectation'],
                expected_salary=extracted_data['expected_salary'],
                job_type=extracted_data['job_type'],
                willing_to_travel=extracted_data['willing_to_travel'],
                willing_to_relocate=extracted_data['willing_to_relocate'],
                uk_driving_licence=extracted_data['uk_driving_licence'],
                date_available=extracted_data['date_available'],
                fluent_languages=extracted_data['fluent_languages'],
                chosen_industries=extracted_data['chosen_industries'],
                main_skills=extracted_data['main_skills'],
                skills=extracted_data['skills'],
                cv_keywords=extracted_data['cv_keywords'],
                profile_last_updated=extracted_data['profile_last_updated'],
                date_registered=extracted_data['date_registered'],
                last_active=extracted_data['last_active'],  # Add the missing last_active field
                last_viewed_date=extracted_data['last_viewed_date'],
                quickview_ref=extracted_data['quickview_ref'],
                profile_match_percentage=extracted_data['profile_match_percentage'],
                contact_info=extracted_data['contact_info']
            )
            
            self.logger.info(f"✅ Comprehensive extraction complete - Name: {extracted_data['name']}, Title: {extracted_data['title']}, Location: {extracted_data['location']}, Skills: {len(extracted_data['skills'])}, Industries: {len(extracted_data['chosen_industries'])}")
            return candidate_info
            
        except Exception as e:
            self.logger.error(f"❌ Critical error extracting candidate details: {e}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return CandidateInfo(name="Unknown")
    
    def _click_download_cv_button(self, driver: webdriver.Chrome) -> bool:
        """
        Find and click download CV button using optimized detection.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            True if download initiated, False otherwise
        """
        try:
            # Strategy 1: Look for direct download links (fastest)
            download_selectors = [
                "a[href*='/download/'][target='_doc']",
                "a[href*='/download-cv/']",
                "a[href*='download'][href*='cv']",
                ".download-cv",
                ".btn-download"
            ]
            
            for selector in download_selectors:
                try:
                    download_links = driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in download_links:
                        if link.is_displayed() and link.get_attribute('href'):
                            # Direct navigation to download URL in new tab
                            download_url = link.get_attribute('href')
                            driver.execute_script(f"window.open('{download_url}', '_blank');")
                            time.sleep(1)  # Brief wait for download to start
                            
                            # Close the download tab and return to profile
                            all_handles = driver.window_handles
                            if len(all_handles) > 1:
                                driver.switch_to.window(all_handles[-1])  # Switch to newest tab
                                driver.close()  # Close download tab
                                driver.switch_to.window(all_handles[-2])  # Return to profile tab
                            
                            return True
                except Exception as e:
                    self.logger.debug(f"Download selector {selector} failed: {e}")
                    continue
            
            # Strategy 2: JavaScript-based download button detection
            js_download_script = """
            const downloadButtons = document.querySelectorAll('a, button');
            for (let btn of downloadButtons) {
                const text = btn.textContent.toLowerCase();
                const href = btn.href || '';
                if ((text.includes('download') && text.includes('cv')) || 
                    href.includes('download')) {
                    return btn;
                }
            }
            return null;
            """
            
            download_button = driver.execute_script(js_download_script)
            if download_button:
                driver.execute_script("arguments[0].click();", download_button)
                time.sleep(1)
                return True
            
            self.logger.warning("No download button found")
            return False
            
        except Exception as e:
            self.logger.error(f"Download button click failed: {e}")
            return False
    
    def _close_tab_and_return(self, driver: webdriver.Chrome, main_window: str):
        """
        Optimized tab closing and window switching with minimal delays.
        
        Args:
            driver: Selenium WebDriver instance
            main_window: Handle of the main window to return to
        """
        try:
            # Get current window handles
            all_handles = driver.window_handles
            current_handle = driver.current_window_handle
            
            # Only close if we're not already on the main window
            if current_handle != main_window and current_handle in all_handles:
                self.logger.debug(f"Closing tab: {current_handle}")
                driver.close()
                
                # Minimal wait for close operation - reduced from 0.5s to 0.1s
                time.sleep(0.1)
            
            # Switch back to main window if it still exists
            try:
                updated_handles = driver.window_handles
                if main_window in updated_handles:
                    driver.switch_to.window(main_window)
                    self.logger.debug("✅ Returned to search results page")
                else:
                    # Main window might have been closed, try to find a valid window
                    if updated_handles:
                        driver.switch_to.window(updated_handles[0])
                        self.logger.warning("Main window not found, switched to available window")
                    else:
                        self.logger.error("No browser windows available")
                        return
                
                # Quick session validation - reduced from 1s to 0.2s
                try:
                    driver.current_url  # Simple test to verify session is still valid
                    # Minimal wait for page stability - reduced from 1s to 0.2s
                    time.sleep(0.2)
                except Exception as e:
                    self.logger.warning(f"Session may be unstable after tab switch: {e}")
                    
            except Exception as switch_error:
                self.logger.error(f"Error switching to main window: {switch_error}")
                raise
            
        except Exception as e:
            self.logger.error(f"Error returning to main window: {e}")
            # Don't raise here - we'll try to continue with the session
            pass
    
    def _ensure_download_directory(self):
        """Create download directory if it doesn't exist."""
        if not self._directory_created:
            self.download_path.mkdir(parents=True, exist_ok=True)
            self._directory_created = True
    
    def _wait_for_download_completion(self, timeout: int = 5) -> bool:
        """
        Smart wait for download completion with early detection and reduced timeout.
        
        Args:
            timeout: Maximum time to wait in seconds (reduced from 15s to 5s)
            
        Returns:
            True if download appears complete, False if timeout
        """
        try:
            import os
            import time
            
            initial_files = set()
            if self.download_path.exists():
                initial_files = set(os.listdir(self.download_path))
            
            start_time = time.time()
            last_file_count = len(initial_files)
            stable_count = 0
            
            while time.time() - start_time < timeout:
                time.sleep(0.2)  # Faster checking - every 200ms instead of 500ms
                
                if self.download_path.exists():
                    current_files = set(os.listdir(self.download_path))
                    new_files = current_files - initial_files
                    
                    # Check if we have new non-temporary files
                    completed_files = [f for f in new_files 
                                     if not f.endswith(('.tmp', '.partial', '.crdownload', '.part', '.downloading'))]
                    
                    if completed_files:
                        self.logger.info(f"✅ Download completed early: {completed_files[0]}")
                        return True
                    
                    # Smart early exit: if file count is stable for 1 second, likely no download
                    current_count = len(current_files)
                    if current_count == last_file_count:
                        stable_count += 1
                        if stable_count >= 5:  # 5 * 0.2s = 1 second stable
                            self.logger.info("📁 No new files detected, assuming download not initiated or completed")
                            return False
                    else:
                        stable_count = 0
                        last_file_count = current_count
                    
                    # Check if temporary files exist (download in progress)
                    temp_files = [f for f in new_files 
                                if f.endswith(('.tmp', '.partial', '.crdownload', '.part', '.downloading'))]
                    
                    if temp_files:
                        # Wait a bit more for temp files to convert to final files
                        time.sleep(0.5)  # Reduced from 2s to 0.5s
                        continue
            
            # Timeout reached
            self.logger.info(f"⏱️ Download wait timeout ({timeout}s) - continuing (likely no file download)")
            return False
            
        except Exception as e:
            self.logger.debug(f"Error waiting for download: {e}")
            return False
    
    def _calculate_data_completeness(self, candidate_info: 'CandidateInfo') -> float:
        """
        Calculate a data completeness score for the candidate info.
        
        Args:
            candidate_info: CandidateInfo object to assess
            
        Returns:
            Float between 0.0 and 1.0 representing completeness
        """
        try:
            fields_to_check = [
                'name', 'title', 'location', 'salary_expectation', 
                'skills', 'contact_info'
            ]
            
            filled_fields = 0
            total_fields = len(fields_to_check)
            
            for field in fields_to_check:
                value = getattr(candidate_info, field, None)
                if value:
                    if isinstance(value, str) and value.strip() and value != "Unknown":
                        filled_fields += 1
                    elif isinstance(value, list) and len(value) > 0:
                        filled_fields += 1
                    elif isinstance(value, dict) and len(value) > 0:
                        filled_fields += 1
            
            return round(filled_fields / total_fields, 2)
            
        except Exception:
            return 0.0
    
    def get_download_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the download session.
        
        Returns:
            Dictionary containing download statistics
        """
        return {
            "total_downloaded": len(self.downloaded_cvs),
            "total_failed": len(self.failed_downloads),
            "target_quantity": self.target_quantity,
            "success_rate": len(self.downloaded_cvs) / max(len(self.downloaded_cvs) + len(self.failed_downloads), 1) * 100,
            "downloaded_cvs": [cv.to_dict() for cv in self.downloaded_cvs],
            "failed_candidates": [result.name for result in self.failed_downloads]
        } 