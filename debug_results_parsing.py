#!/usr/bin/env python3
"""
Debug script to analyze search results page structure
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pathlib import Path

def debug_results_parsing():
    """Debug the search results parsing to find correct selectors."""
    
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
        
        # Check if authenticated
        if "login" in driver.current_url:
            print("❌ Not authenticated - need to login first")
            return
        
        print("✅ Authenticated!")
        
        # Handle cookie banner
        try:
            cookie_btn = driver.find_element(By.CSS_SELECTOR, "#onetrust-accept-btn-handler")
            if cookie_btn.is_displayed():
                cookie_btn.click()
                print("✅ Handled cookie banner")
                time.sleep(2)
        except:
            pass
        
        # Fill form and submit
        print("\n🔧 Filling search form...")
        
        # Expand advanced options
        try:
            advanced_button = driver.find_element(By.CSS_SELECTOR, "button.toggle-quick-advanced")
            if advanced_button.is_displayed():
                advanced_button.click()
                print("✅ Expanded advanced options")
                time.sleep(2)
        except:
            pass
        
        # Fill keywords
        keywords_filled = False
        print("🔤 Trying to fill keywords...")
        
        # Try multiple selectors
        keyword_selectors = [
            "input[name='keywords']",
            "#keywords",
            ".keywords-input",
            "input[placeholder*='keyword']",
            "input[placeholder*='Keyword']",
            "input.boolean__input",  # From the working scraper
            "input[type='text'][name='keywords']"
        ]
        
        for selector in keyword_selectors:
            try:
                keywords_input = driver.find_element(By.CSS_SELECTOR, selector)
                if keywords_input.is_displayed() and keywords_input.is_enabled():
                    # Clear first
                    driver.execute_script("arguments[0].value = '';", keywords_input)
                    # Fill with specific keywords
                    keywords_input.send_keys("Senior Software Engineer Python")
                    
                    # Verify it was filled
                    filled_value = keywords_input.get_attribute('value')
                    if filled_value and "Senior Software Engineer Python" in filled_value:
                        print(f"✅ Keywords filled successfully with selector: {selector}")
                        print(f"   Value: {filled_value}")
                        keywords_filled = True
                        break
                    else:
                        print(f"❌ Keywords not filled properly with {selector}, value: {filled_value}")
            except Exception as e:
                print(f"❌ Selector {selector} failed: {e}")
        
        if not keywords_filled:
            print("❌ Could not fill keywords field with any selector!")
            return
        
        # Submit search
        try:
            submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='View results']")
            driver.execute_script("arguments[0].click();", submit_button)
            print("✅ Search submitted")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Could not submit: {e}")
        
        print(f"\n📍 Current URL: {driver.current_url}")
        print(f"📑 Page title: {driver.title}")
        
        # Now analyze the results page structure
        print("\n🔍 ANALYZING RESULTS PAGE STRUCTURE...")
        
        # Check if we're on results page
        if "results" in driver.current_url or "candidate-search" in driver.current_url:
            print("✅ On search results page")
            
            # Save page source for analysis
            with open("debug_results_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("💾 Saved page source to debug_results_page.html")
            
            # Try different selectors to find result elements
            result_selectors_to_try = [
                # Table-based selectors
                "table tbody tr",
                "table tr",
                "#searchresults tbody tr",
                "#searchresults tr",
                ".search-results tbody tr",
                ".search-results tr",
                
                # Div-based selectors
                ".search-result",
                ".candidate-result", 
                ".result-row",
                ".candidate-listing",
                ".candidate-card",
                ".cv-result",
                ".result-item",
                
                # Generic selectors
                "[data-candidate-id]",
                "[data-cv-id]",
                ".result",
                ".candidate",
                
                # Common CV-Library patterns
                "tr[onclick]",
                "tr[data-*]",
                "div[data-candidate*]",
                "div[onclick*='candidate']",
                "div[onclick*='cv']"
            ]
            
            print("\n🎯 Testing result selectors...")
            for selector in result_selectors_to_try:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"✅ Found {len(elements)} elements with: {selector}")
                        
                        # Analyze first few elements
                        for i, element in enumerate(elements[:3]):
                            try:
                                element_html = element.get_attribute('outerHTML')[:200] + "..."
                                print(f"   Element {i+1}: {element_html}")
                            except:
                                print(f"   Element {i+1}: Could not get HTML")
                    else:
                        print(f"❌ No elements found with: {selector}")
                except Exception as e:
                    print(f"❌ Error with selector {selector}: {e}")
            
            # Check for specific result indicators
            print("\n🔍 Looking for specific CV/candidate indicators...")
            
            # Look for links to CV pages
            cv_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/cv/']")
            print(f"📋 Found {len(cv_links)} CV links")
            
            candidate_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='candidate']")
            print(f"👥 Found {len(candidate_links)} candidate links")
            
            # Look for download buttons
            download_buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='download'], button[onclick*='download'], .download")
            print(f"📥 Found {len(download_buttons)} download elements")
            
            # Check page text for result indicators
            page_text = driver.page_source.lower()
            if "no results" in page_text or "no candidates found" in page_text:
                print("⚠️  Page indicates no results found")
            elif "results" in page_text and ("candidate" in page_text or "cv" in page_text):
                print("✅ Page appears to have results based on text content")
            
            # Look for pagination
            pagination_elements = driver.find_elements(By.CSS_SELECTOR, ".pagination, .pager, .page-nav")
            print(f"📄 Found {len(pagination_elements)} pagination elements")
            
        else:
            print("❌ Not on expected results page")
        
        print(f"\n⏸️  Pausing for 30 seconds to inspect...")
        time.sleep(30)
        
    finally:
        driver.quit()
        print("🧹 Browser closed")

if __name__ == "__main__":
    debug_results_parsing() 