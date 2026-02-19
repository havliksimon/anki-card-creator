"""Web scraping service using Firefox/Geckodriver."""
import os
import time
import re
from typing import List, Dict, Optional
from urllib.parse import quote

# Selenium is optional - only needed for scraping features
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class ChineseScraper:
    """Scraper for Chinese dictionary data."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Detect environment and set paths accordingly
        # Check both firefox AND geckodriver exist together
        
        # Docker/Koyeb paths (priority when geckodriver present)
        if os.path.exists("/usr/bin/firefox") and os.path.exists("/usr/local/bin/geckodriver"):
            self.firefox_binary = "/usr/bin/firefox"
            self.geckodriver_path = "/usr/local/bin/geckodriver"
        # Local development with bundled binaries
        elif os.path.exists("./old_anki_card_creator/server/firefox") and \
             os.path.exists("./old_anki_card_creator/server/geckodriver"):
            self.firefox_binary = os.path.abspath("./old_anki_card_creator/server/firefox")
            self.geckodriver_path = os.path.abspath("./old_anki_card_creator/server/geckodriver")
        # System firefox with local geckodriver
        elif os.path.exists("/usr/bin/firefox") and \
             os.path.exists("./old_anki_card_creator/server/geckodriver"):
            self.firefox_binary = "/usr/bin/firefox"
            self.geckodriver_path = os.path.abspath("./old_anki_card_creator/server/geckodriver")
        # Fallback for docker with firefox-esr
        elif os.path.exists("/usr/bin/firefox-esr") and os.path.exists("/usr/local/bin/geckodriver"):
            self.firefox_binary = "/usr/bin/firefox-esr"
            self.geckodriver_path = "/usr/local/bin/geckodriver"
        else:
            self.firefox_binary = None
            self.geckodriver_path = None
            
        # Extension path
        if os.path.exists("/app/extension.xpi"):
            self.extension_path = "/app/extension.xpi"
        elif os.path.exists("./old_anki_card_creator/server/i_dont_care_about_cookies-3.4.8.xpi"):
            self.extension_path = os.path.abspath("./old_anki_card_creator/server/i_dont_care_about_cookies-3.4.8.xpi")
        else:
            self.extension_path = None
        
        if not SELENIUM_AVAILABLE:
            print("Warning: Selenium not available. Scraping features disabled.")
            return
            
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Firefox WebDriver."""
        if not SELENIUM_AVAILABLE:
            return
            
        options = Options()
        options.binary_location = self.firefox_binary
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        service = Service(self.geckodriver_path)
        self.driver = webdriver.Firefox(service=service, options=options)
        self.driver.set_window_size(1920, 1080)
        self.wait = WebDriverWait(self.driver, 15)
        
        # Install extension
        try:
            self.driver.install_addon(self.extension_path, temporary=True)
        except Exception as e:
            print(f"Warning: Could not install extension: {e}")
    
    def scrape_mdbg(self, character: str) -> Dict:
        """Scrape word data from MDBG."""
        if not SELENIUM_AVAILABLE:
            return {}
            
        try:
            url = f"https://www.mdbg.net/chinese/dictionary?page=worddict&wdrst=0&wdqb={quote(character)}"
            self.driver.get(url)
            
            # Wait for results
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.row")))
            
            entries = self.driver.find_elements(By.CSS_SELECTOR, "tr.row")
            if not entries:
                return {}
            
            results = []
            for entry in entries[:5]:  # Get top 5 results
                try:
                    term = entry.find_element(By.CSS_SELECTOR, "td.head .hanzi").text.strip()
                    pinyin = entry.find_element(By.CSS_SELECTOR, "td.head .pinyin").text.strip()
                    definition = entry.find_element(By.CSS_SELECTOR, "td.details .defs").text.strip()
                    
                    results.append({
                        'term': term,
                        'pinyin': pinyin,
                        'definition': definition
                    })
                except Exception as e:
                    continue
            
            if results:
                return {
                    'pinyin': results[0]['pinyin'],
                    'translation': results[0]['definition'],
                    'variants': results
                }
            
            return {}
            
        except Exception as e:
            print(f"MDBG scraping error: {e}")
            return {}
    
    def scrape_chinese_boost(self, character: str) -> List[Dict]:
        """Scrape example sentences from Chinese Boost."""
        if not SELENIUM_AVAILABLE:
            return []
            
        try:
            url = f"https://www.chineseboost.com/chinese-example-sentences?query={quote(character)}"
            self.driver.get(url)
            
            # Wait for cards
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card")))
            
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.card")
            sentences = []
            
            for card in cards[:6]:  # Get first 6 sentences
                try:
                    liju = card.find_element(By.CSS_SELECTOR, 'div.liju')
                    
                    hanzi = liju.find_element(By.CSS_SELECTOR, 'p.hanzi').text.strip()
                    pinyin = liju.find_element(By.CSS_SELECTOR, 'p.pinyin').text.strip()
                    translation = liju.find_element(By.CSS_SELECTOR, 'p.yingwen').text.strip()
                    
                    sentences.append({
                        'chinese': hanzi,
                        'pinyin': pinyin,
                        'english': translation
                    })
                except Exception as e:
                    continue
            
            return sentences
            
        except Exception as e:
            print(f"Chinese Boost scraping error: {e}")
            return []
    
    def scrape_stroke_order(self, character: str) -> List[str]:
        """Scrape stroke order GIFs from Written Chinese."""
        if not SELENIUM_AVAILABLE:
            return []
            
        try:
            self.driver.get("https://dictionary.writtenchinese.com")
            
            # Search for character
            search_box = self.wait.until(EC.presence_of_element_located((By.ID, "searchKey")))
            search_box.clear()
            search_box.send_keys(character)
            search_box.send_keys(Keys.ENTER)
            
            # Click "Learn more"
            learn_more = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[@class='cstm learnmore learn-more-link']/span[text()='Learn more']")
            ))
            learn_more.click()
            
            # Get stroke GIFs
            self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.symbol-layer img")))
            gifs = self.driver.find_elements(By.CSS_SELECTOR, "div.symbol-layer img")
            
            gif_urls = []
            for gif in gifs:
                src = gif.get_attribute("src")
                if src and "giffile.action" in src:
                    gif_urls.append(src)
            
            return gif_urls[:6]  # Return max 6 strokes
            
        except Exception as e:
            print(f"Stroke order scraping error: {e}")
            return []
    
    def close(self):
        """Close the WebDriver."""
        if SELENIUM_AVAILABLE and self.driver:
            self.driver.quit()
            self.driver = None
    
    def __del__(self):
        """Cleanup on destruction."""
        self.close()


# Global instance
_scraper = None

def get_scraper() -> ChineseScraper:
    """Get or create scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = ChineseScraper()
    return _scraper

def close_scraper():
    """Close the global scraper instance."""
    global _scraper
    if _scraper:
        _scraper.close()
        _scraper = None
