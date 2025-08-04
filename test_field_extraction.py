#!/usr/bin/env python3
"""
Test script to verify improved field extraction for previously missing fields.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import ConfigLoader
from src.scraper.cv_library_scraper import CVLibraryScraper

def test_field_extraction():
    """Test extraction of previously missing fields."""
    
    print("🧪 Testing improved field extraction...")
    
    # Load configuration
    config_loader = ConfigLoader()
    settings = config_loader.create_settings()
    
    # Override settings for test
    settings.search.keywords = ["Python developer"]
    settings.download.max_quantity = 3  # Small test
    
    print(f"Target CVs: {settings.download.max_quantity}")
    print(f"Testing extraction of: profile_match_percentage, uk_driving_licence, profile_last_updated")
    
    # Initialize scraper
    scraper = CVLibraryScraper(settings)
    
    try:
        print("\n🔍 Starting extraction test...")
        
        # Run session with small number for quick test
        session_results = scraper.run_session(
            keywords=settings.search.keywords,
            max_downloads=3
        )
        
        if session_results.get('success', False):
            print(f"\n✅ Test completed successfully!")
            print(f"Candidates processed: {len(session_results.get('downloaded_candidates', []))}")
            
            # Check extraction quality
            candidates = session_results.get('downloaded_candidates', [])
            if candidates:
                print("\n📊 FIELD EXTRACTION ANALYSIS:")
                
                fields_to_check = [
                    'profile_match_percentage',
                    'uk_driving_licence', 
                    'profile_last_updated',
                    'quickview_ref',
                    'date_registered'
                ]
                
                for field in fields_to_check:
                    extracted_count = 0
                    examples = []
                    
                    for candidate in candidates:
                        value = candidate.get(field)
                        if value and value != 'null':
                            extracted_count += 1
                            if len(examples) < 2:
                                examples.append(f"{candidate.get('name', 'Unknown')}: {value}")
                    
                    success_rate = (extracted_count / len(candidates)) * 100
                    status = '✅' if success_rate >= 80 else '⚠️' if success_rate >= 30 else '❌'
                    
                    print(f"{status} {field.upper()}: {extracted_count}/{len(candidates)} ({success_rate:.1f}%)")
                    for example in examples:
                        print(f"   📝 {example}")
                
            else:
                print("❌ No candidates downloaded for analysis")
        else:
            print(f"❌ Test failed: {session_results.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    test_field_extraction() 