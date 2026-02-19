#!/usr/bin/env python3
"""Test the scraping functionality."""
import os
import sys

# Add the copy app path for Firefox binaries
os.environ['USE_LOCAL_DB'] = 'true'

from src.services.scraper_service import ChineseScraper


def test_scraper():
    """Test the Chinese scraper."""
    print("=" * 60)
    print("Testing Chinese Scraper")
    print("=" * 60)
    
    scraper = None
    try:
        print("\nInitializing scraper...")
        scraper = ChineseScraper()
        print("✓ Scraper initialized")
        
        # Test 1: MDBG scraping
        print("\n--- Testing MDBG Scraping ---")
        print("Scraping: 你好")
        result = scraper.scrape_mdbg("你好")
        if result:
            print(f"✓ Pinyin: {result.get('pinyin')}")
            print(f"✓ Translation: {result.get('translation')[:100]}...")
        else:
            print("⚠ No result from MDBG")
        
        # Test 2: Chinese Boost scraping
        print("\n--- Testing Chinese Boost Scraping ---")
        print("Scraping example sentences for: 学习")
        sentences = scraper.scrape_chinese_boost("学习")
        if sentences:
            print(f"✓ Found {len(sentences)} sentences")
            for i, sent in enumerate(sentences[:3], 1):
                print(f"  {i}. {sent['chinese']}")
                print(f"     {sent['english']}")
        else:
            print("⚠ No sentences found")
        
        # Test 3: Stroke order scraping
        print("\n--- Testing Stroke Order Scraping ---")
        print("Scraping stroke order for: 你")
        gifs = scraper.scrape_stroke_order("你")
        if gifs:
            print(f"✓ Found {len(gifs)} stroke GIFs")
            for i, url in enumerate(gifs[:3], 1):
                print(f"  {i}. {url[:80]}...")
        else:
            print("⚠ No stroke GIFs found")
        
        print("\n" + "=" * 60)
        print("Scraper tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if scraper:
            print("\nClosing scraper...")
            scraper.close()
            print("✓ Scraper closed")
    
    return True


if __name__ == '__main__':
    success = test_scraper()
    sys.exit(0 if success else 1)
