#!/usr/bin/env python3
"""
Test script to verify enhanced pagination functionality for CV scraping.
This script tests edge cases and uses total results information for smart pagination.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import ConfigLoader
from src.scraper.cv_library_scraper import CVLibraryScraper

def test_pagination_edge_cases():
    """Test enhanced pagination functionality with edge case handling."""
    
    print("🧪 Testing enhanced pagination with edge cases...")
    
    # Load configuration
    config_loader = ConfigLoader()
    settings = config_loader.create_settings()
    
    # Test scenarios
    test_cases = [
        {"target": 5, "description": "Small target (5 CVs) - should stop early"},
        {"target": 22, "description": "Medium target (22 CVs) - normal pagination"},
        {"target": 100, "description": "Large target (100 CVs) - may exceed available"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST CASE {i}: {case['description']}")
        print(f"{'='*60}")
        
        # Override settings for test
        settings.search.keywords = ["Python developer"]
        settings.download.max_quantity = case["target"]
        
        print(f"Target resumes: {case['target']}")
        print(f"Search keywords: {settings.search.keywords}")
        
        # Initialize scraper
        scraper = CVLibraryScraper(settings)
        
        try:
            print(f"\n🔍 Starting test case {i}...")
            
            # Run session with target downloads
            session_results = scraper.run_session(
                keywords=settings.search.keywords,
                max_downloads=case["target"]
            )
            
            # Analyze results
            if session_results['status'] == 'completed':
                search_results = session_results.get('search_results', {})
                download_results = session_results.get('download_results', {})
                
                total_found = search_results.get('total_found', 0)
                successful_downloads = download_results.get('successful_downloads', 0)
                
                print(f"\n📊 TEST CASE {i} RESULTS:")
                print(f"✅ Target: {case['target']} CVs")
                print(f"✅ Found: {total_found} candidates")
                print(f"✅ Downloaded: {successful_downloads} CVs")
                print(f"✅ Duration: {session_results['duration']:.2f}s")
                
                # Edge case analysis
                if total_found >= case["target"]:
                    print(f"✅ SUCCESS: Found enough candidates ({total_found} >= {case['target']})")
                else:
                    print(f"⚠️  PARTIAL: Found fewer candidates than target ({total_found} < {case['target']})")
                
                if successful_downloads >= min(case["target"], total_found):
                    print(f"✅ DOWNLOAD SUCCESS: Downloaded expected number")
                else:
                    print(f"⚠️  DOWNLOAD PARTIAL: Some downloads may have failed")
            else:
                print(f"❌ TEST CASE {i} FAILED: {session_results.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"❌ TEST CASE {i} EXCEPTION: {e}")
        
        finally:
            try:
                scraper.close()
            except:
                pass
    
    print(f"\n{'='*60}")
    print("🎉 Enhanced pagination testing completed!")
    print("Check logs above for detailed pagination behavior and edge case handling.")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_pagination_edge_cases() 