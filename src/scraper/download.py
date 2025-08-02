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
        Download CVs from search results.
        
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
                    # Download CV for this candidate
                    cv_data = self._download_single_cv(driver, result, main_window)
                    
                    if cv_data:
                        self.downloaded_cvs.append(cv_data)
                        self.download_count += 1
                        self.logger.info(f"✅ Successfully downloaded CV for {result.name} ({self.download_count}/{self.target_quantity})")
                    else:
                        self.failed_downloads.append(result)
                        self.logger.warning(f"❌ Failed to download CV for {result.name}")
                    
                    # Rate limiting between downloads (reduced for speed)
                    if self.download_count < self.target_quantity:  # Only wait if we have more to do
                        time.sleep(1)  # Minimal delay instead of full rate limiting
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing candidate {result.name}: {e}")
                    self.failed_downloads.append(result)
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
        Download CV for a single candidate with optimized speed.
        
        Args:
            driver: Selenium WebDriver instance
            search_result: Search result for the candidate
            main_window: Handle of the main search results window
            
        Returns:
            CVData object if successful, None otherwise
        """
        try:
            # Step 1: Open CV profile (optimized)
            self.logger.info(f"Step 1: Opening CV profile for {search_result.name}")
            
            if not self._click_view_cv_button(search_result, driver):
                self.logger.error(f"Could not open CV profile for {search_result.name}")
                return None
            
            # Step 2: Switch to the new tab (optimized wait)
            self.logger.info("Step 2: Switching to candidate profile tab")
            
            if not self._switch_to_candidate_tab(driver, main_window):
                self.logger.error("Failed to switch to candidate profile tab")
                return None
            
            # Step 3: Fast extraction of candidate information
            self.logger.info("Step 3: Extracting candidate information")
            candidate_info = self._extract_candidate_details(driver)
            
            # Step 4: Download the CV (optimized)
            self.logger.info("Step 4: Downloading CV file")
            download_success = self._click_download_cv_button(driver)
            
            # Step 5: Quick return to main window
            self.logger.info("Step 5: Returning to search results")
            self._close_tab_and_return(driver, main_window)
            
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
                with open(candidate_data_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump({
                        'candidate_info': candidate_info.to_dict(),
                        'search_result': {
                            'cv_id': search_result.cv_id,
                            'name': search_result.name,
                            'location': search_result.location,
                            'salary': search_result.salary,
                            'skills': search_result.skills,
                            'profile_url': search_result.profile_url
                        },
                        'extraction_time': time.time(),
                        'search_keywords': search_result.search_keywords,
                        'download_success': download_success
                    }, f, indent=2, ensure_ascii=False)
                self.logger.info(f"✅ Saved candidate data to: {candidate_data_file}")
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
        Navigate directly to CV profile using URL manipulation (fastest method).
        
        Args:
            search_result: SearchResult object containing profile URL
            driver: Selenium WebDriver instance
            
        Returns:
            True if profile opened successfully, False otherwise
        """
        try:
            if search_result.profile_url:
                # Direct navigation is fastest
                driver.execute_script(f"window.open('{search_result.profile_url}', '_blank');")
                return True
            else:
                self.logger.warning(f"No profile URL available for {search_result.name}")
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
                    
                    # Very short wait for basic page load
                    time.sleep(1)
                    
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
        Extract essential candidate information from the CV-Library profile page with maximum speed.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            CandidateInfo object with extracted details
        """
        try:
            self.logger.info("Fast extracting candidate details...")
            
            # Single page source access for speed
            page_text = driver.page_source
            
            # Extract candidate name (fastest method)
            name = "Unknown"
            try:
                page_title = driver.title
                if " - " in page_title:
                    potential_name = page_title.split(" - ")[0].strip()
                    if len(potential_name) > 3 and len(potential_name) < 50:
                        name = potential_name
                        self.logger.info(f"✅ Extracted name: {name}")
            except Exception:
                name = "Unknown"
            
            # Fast regex-based extraction (essential fields only)
            location = None
            salary_expectation = None
            skills = []
            contact_info = {}
            
            try:
                # Extract location (single regex)
                location_match = re.search(r'Location:\s*([^\n\r<]+)', page_text, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()[:50]  # Limit length
                
                # Extract salary (single regex)
                salary_match = re.search(r'Expected Salary:\s*([^\n\r<]+)', page_text, re.IGNORECASE)
                if salary_match:
                    salary_expectation = salary_match.group(1).strip()[:30]  # Limit length
                
                # Extract essential skills only (minimal processing)
                essential_skills = ["Python", "Java", "JavaScript", "React", "SQL", "AWS", "Docker"]
                skills = [skill for skill in essential_skills if skill.lower() in page_text.lower()]
                
                # Fast email extraction (single regex)
                email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
                if email_matches:
                    # Filter out obvious non-emails and take first valid one
                    valid_emails = [email for email in email_matches[:3] if not any(domain in email.lower() for domain in ['cv-library', 'google', 'facebook', 'linkedin'])]
                    if valid_emails:
                        contact_info['email'] = valid_emails[0]
                
                # Fast phone extraction (single regex)
                phone_match = re.search(r'\b(?:\+44|0)\s?[1-9]\d{8,10}\b', page_text)
                if phone_match:
                    contact_info['phone'] = phone_match.group(0)
                    
            except Exception as e:
                self.logger.debug(f"Error in fast extraction: {e}")
            
            # Create CandidateInfo with extracted data
            candidate_info = CandidateInfo(
                name=name,
                title=None,  # Skip for speed
                location=location,
                salary_expectation=salary_expectation,
                skills=skills,
                contact_info=contact_info
            )
            
            self.logger.info(f"✅ Fast extracted details for: {name}")
            return candidate_info
            
        except Exception as e:
            self.logger.warning(f"Error extracting candidate details: {e}")
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
        Close the current tab and return to the main search results window with optimized speed.
        
        Args:
            driver: Selenium WebDriver instance
            main_window: Handle of the main window to return to
        """
        try:
            # Close current tab
            driver.close()
            
            # Switch back to main window
            driver.switch_to.window(main_window)
            
            # No wait time needed for stability
            
            self.logger.info("✅ Returned to search results page")
            
        except Exception as e:
            self.logger.error(f"Error returning to main window: {e}")
            # Try to switch to main window anyway
            try:
                driver.switch_to.window(main_window)
            except:
                pass
    
    def _ensure_download_directory(self):
        """Create download directory if it doesn't exist."""
        if not self._directory_created:
            self.download_path.mkdir(parents=True, exist_ok=True)
            self._directory_created = True
    
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