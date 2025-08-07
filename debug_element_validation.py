#!/usr/bin/env python3
"""
Debug script to analyze why search result elements are being filtered out
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pathlib import Path

def debug_element_validation():
    """Debug why search result elements are failing validation."""
    
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
        
        # Handle cookie banner
        try:
            cookie_btn = driver.find_element(By.CSS_SELECTOR, "#onetrust-accept-btn-handler")
            if cookie_btn.is_displayed():
                cookie_btn.click()
                time.sleep(2)
        except:
            pass
        
        # Expand advanced options
        try:
            advanced_button = driver.find_element(By.CSS_SELECTOR, "button.toggle-quick-advanced")
            if advanced_button.is_displayed():
                advanced_button.click()
                time.sleep(2)
        except:
            pass
        
        # Fill keywords with working selector
        try:
            keywords_input = driver.find_element(By.CSS_SELECTOR, "input.boolean__input")
            driver.execute_script("arguments[0].value = '';", keywords_input)
            keywords_input.send_keys("Senior Software Engineer Python")
            print("✅ Keywords filled")
        except Exception as e:
            print(f"❌ Could not fill keywords: {e}")
            return
        
        # Submit search
        try:
            submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='View results']")
            driver.execute_script("arguments[0].click();", submit_button)
            print("✅ Search submitted")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Could not submit: {e}")
            return
        
        print(f"\n📍 Current URL: {driver.current_url}")
        
        # Find search result elements
        print("\n🔍 ANALYZING SEARCH RESULT ELEMENTS...")
        
        result_elements = driver.find_elements(By.CSS_SELECTOR, ".search-result")
        print(f"✅ Found {len(result_elements)} .search-result elements")
        
        for i, element in enumerate(result_elements, 1):
            try:
                print(f"\n--- Element {i} ---")
                
                # Get basic info
                element_text = element.text.strip()
                cv_links = element.find_elements(By.CSS_SELECTOR, "a[href*='/cv/']")
                tag_name = element.tag_name.lower()
                
                print(f"Tag: {tag_name}")
                print(f"Text length: {len(element_text)} characters")
                print(f"CV links found: {len(cv_links)}")
                print(f"Text preview: {element_text[:200]}...")
                
                # Check validation criteria
                text_valid = len(element_text) > 50
                cv_links_valid = len(cv_links) > 0
                tag_valid = tag_name != 'tr'
                
                print(f"✅ Text > 50 chars: {text_valid}")
                print(f"✅ Has CV links: {cv_links_valid}")
                print(f"✅ Not table row: {tag_valid}")
                
                overall_valid = text_valid and cv_links_valid and tag_valid
                print(f"🎯 OVERALL VALID: {overall_valid}")
                
                if cv_links:
                    for j, link in enumerate(cv_links[:3]):
                        href = link.get_attribute('href')
                        link_text = link.text.strip()
                        print(f"  CV Link {j+1}: {link_text} -> {href}")
                
                # Check for View CV buttons specifically
                view_cv_buttons = element.find_elements(By.CSS_SELECTOR, "a[href*='/cv/']")
                view_cv_text_buttons = element.find_elements(By.XPATH, ".//a[contains(text(), 'View CV')]")
                print(f"View CV buttons: {len(view_cv_buttons)} href-based, {len(view_cv_text_buttons)} text-based")
                
            except Exception as e:
                print(f"❌ Error analyzing element {i}: {e}")
        
        print(f"\n⏸️  Pausing for 15 seconds...")
        time.sleep(15)
        
    finally:
        driver.quit()
        print("🧹 Browser closed")

if __name__ == "__main__":
    debug_element_validation() 