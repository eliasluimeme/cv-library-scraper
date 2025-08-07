#!/usr/bin/env python3
"""
Debug script to test the complete search flow with cookie handling
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path

def debug_complete_search_flow():
    """Complete debug test including cookie handling and proper form filling."""
    
    # Setup Chrome options with the persistent profile
    chrome_options = Options()
    profile_path = Path("sessions/browser_profiles/default_profile")
    chrome_options.add_argument(f"--user-data-dir={profile_path}")
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Start browser
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("🔍 Opening CV-Library search page...")
        driver.get("https://www.cv-library.co.uk/recruiter/candidate-search")
        time.sleep(3)
        
        print(f"📍 Initial URL: {driver.current_url}")
        
        # Check if authenticated
        if "login" in driver.current_url:
            print("❌ Not authenticated - need to login first")
            return
        
        print("✅ Authenticated!")
        
        # Handle cookie banner if present
        print("\n🍪 Checking for cookie banner...")
        try:
            # Common cookie banner selectors
            cookie_selectors = [
                "#onetrust-accept-btn-handler",
                ".ot-sdk-show-settings",
                "[data-testid='accept-all-cookies']",
                ".accept-cookies",
                ".cookie-accept"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if cookie_btn.is_displayed():
                        cookie_btn.click()
                        print(f"✅ Clicked cookie button: {selector}")
                        time.sleep(2)
                        break
                except:
                    continue
        except Exception as e:
            print(f"No cookie banner found or error: {e}")
        
        print("\n🔧 Setting up search form...")
        
        # Expand advanced options
        try:
            advanced_button = driver.find_element(By.CSS_SELECTOR, "button.toggle-quick-advanced")
            if advanced_button.is_displayed():
                advanced_button.click()
                print("✅ Expanded advanced options")
                time.sleep(2)
        except Exception as e:
            print(f"Advanced options not found or already expanded: {e}")
        
        # Find and fill keywords field - try all possible approaches
        print("\n🔤 Finding keywords field...")
        keywords_filled = False
        
        # Try direct approach first
        try:
            keywords_input = driver.find_element(By.CSS_SELECTOR, "input[name='keywords']")
            if keywords_input.is_displayed() and keywords_input.is_enabled():
                keywords_input.clear()
                # Use more specific keywords that CV-Library will accept
                keywords_input.send_keys("Senior Software Engineer Python")
                print("✅ Filled keywords with specific terms: 'Senior Software Engineer Python'")
                keywords_filled = True
        except Exception as e:
            print(f"Direct keywords selector failed: {e}")
        
        # If that didn't work, try other selectors
        if not keywords_filled:
            selectors_to_try = [
                "#keywords",
                ".keywords-input", 
                "input[placeholder*='keyword']",
                "input[placeholder*='Keyword']",
                "input[id*='keyword']",
                "input[class*='keyword']"
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.clear()
                            element.send_keys("Senior Software Engineer Python")
                            print(f"✅ Filled keywords with selector: {selector}")
                            keywords_filled = True
                            break
                    if keywords_filled:
                        break
                except Exception as e:
                    continue
        
        if not keywords_filled:
            print("❌ Could not fill keywords field")
        
        print(f"\n🎯 Looking for 'View results' button...")
        
        # Find the View results button
        try:
            view_results_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='View results']")
            print(f"✅ Found 'View results' button")
            print(f"   Visible: {view_results_button.is_displayed()}")
            print(f"   Enabled: {view_results_button.is_enabled()}")
            
            # Scroll to button to make sure it's in view
            driver.execute_script("arguments[0].scrollIntoView(true);", view_results_button)
            time.sleep(1)
            
            # Try clicking with JavaScript to avoid interception
            print("🎯 Clicking 'View results' button with JavaScript...")
            driver.execute_script("arguments[0].click();", view_results_button)
            print("✅ Clicked 'View results' button!")
            
            # Wait for page to load and check URL
            time.sleep(5)
            final_url = driver.current_url
            print(f"📍 After clicking, URL: {final_url}")
            
            # Analyze the results
            if "results" in final_url or final_url != "https://www.cv-library.co.uk/recruiter/candidate-search":
                print("✅ Successfully navigated to results page!")
                
                # Look for search results
                print("\n🔍 Analyzing page content...")
                
                # Check page title
                page_title = driver.title
                print(f"📑 Page title: {page_title}")
                
                # Look for results indicators
                page_source = driver.page_source.lower()
                
                if "no results" in page_source or "no candidates found" in page_source:
                    print("📊 Result: NO CANDIDATES FOUND")
                    print("   This could mean:")
                    print("   - Search worked but no matching candidates")
                    print("   - Account has no access to CV database")
                    print("   - Search criteria too restrictive")
                elif "results" in page_source and ("candidate" in page_source or "cv" in page_source):
                    print("📊 Result: POTENTIAL CANDIDATES FOUND")
                    
                    # Try to find result elements
                    result_selectors = [
                        "tr[class*='result']",
                        "tr[class*='candidate']", 
                        ".search-result",
                        ".candidate-result",
                        ".result-row",
                        ".candidate-listing",
                        "tbody tr"
                    ]
                    
                    for selector in result_selectors:
                        try:
                            results = driver.find_elements(By.CSS_SELECTOR, selector)
                            if results and len(results) > 1:  # More than just header
                                print(f"   Found {len(results)} potential candidates with: {selector}")
                        except:
                            continue
                else:
                    print("📊 Result: UNCLEAR - Page loaded but content unknown")
                
            else:
                print("❌ Did not navigate away from search page")
                print("   This suggests the form submission failed")
            
            print(f"\n⏸️  Pausing for 20 seconds to inspect the page...")
            time.sleep(20)
            
        except Exception as e:
            print(f"❌ Error with View results button: {e}")
        
    finally:
        driver.quit()
        print("🧹 Browser closed")

if __name__ == "__main__":
    debug_complete_search_flow() 