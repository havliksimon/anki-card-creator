"""Web scraping service using Selenium - exact copy from old app."""
import os
import re
import urllib.parse
import threading
import traceback
import time
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Tone colors mapping (same as old app)
tone_colors = {
    1: '#ff0000',  # Red
    2: '#ffaa00',  # Orange
    3: '#00aa00',  # Green
    4: '#0000ff',  # Blue
    0: 'var(--regular-text)'   # Black (neutral)
}


def get_tone_number(syllable):
    """Get tone number from pinyin syllable."""
    tone_mapping = {
        'ā': 1, 'ō': 1, 'ē': 1, 'ī': 1, 'ū': 1, 'ǖ': 1,
        'á': 2, 'ó': 2, 'é': 2, 'í': 2, 'ú': 2, 'ǘ': 2,
        'ǎ': 3, 'ǒ': 3, 'ě': 3, 'ǐ': 3, 'ǔ': 3, 'ǚ': 3,
        'à': 4, 'ò': 4, 'è': 4, 'ì': 4, 'ù': 4, 'ǜ': 4,
    }
    for char in syllable:
        if char in tone_mapping:
            return tone_mapping[char]
    return 0  # Neutral tone/unknown


def style_scraped_pinyin(pinyin_str, word_str):
    """Style scraped pinyin with colors - exact copy from old app."""
    styled_syllables = []
    syllables = pinyin_str
    word_syllables = [char for char in word_str]
    styled_word_syllables = []
    for i in range(len(syllables)):
        tone = get_tone_number(syllables[i])
        color = tone_colors.get(tone, '')
        styled = f'<span style="color:{color}">{syllables[i]}</span>'
        styled_syllables.append(styled)
        styled = f'<span style="color:{color}">{word_syllables[i]}</span>'
        styled_word_syllables.append(styled)
    return ' '.join(styled_syllables), ''.join(styled_word_syllables)


def extract_plain_hanzi(hanzi_html):
    """Extract plain text from hanzi HTML."""
    soup = BeautifulSoup(hanzi_html, 'html.parser')
    return soup.get_text()


def convert_pinyin_to_styled(pinyin_html):
    """Convert pinyin HTML to styled HTML with colors."""
    soup = BeautifulSoup(pinyin_html, 'html.parser')
    # Process syllable spans to add color styles
    for span in soup.find_all('span', class_=re.compile(r'tone-\d')):
        classes = span.get('class', [])
        tone_class = next((c for c in classes if c.startswith('tone-')), None)
        if tone_class:
            tone = int(tone_class.split('-')[1])
            color = tone_colors.get(tone, '')
            span['style'] = f'color: {color};'
            # Remove all classes
            del span['class']
    
    # Remove all elements with class 'pinyin sentence' or 'pinyin word'
    for elem in soup.find_all(class_=lambda x: x in ['pinyin sentence', 'pinyin word']):
        elem.unwrap()  # Unwraps the element, keeping its contents
    
    # Remove 'non-pinyin' spans and replace them with their text content
    for elem in soup.find_all(class_='non-pinyin'):
        elem.replace_with(elem.get_text())
    
    # Remove 'lang' attributes and unnecessary classes
    for elem in soup.find_all():
        if 'lang' in elem.attrs:
            del elem['lang']
        if 'class' in elem.attrs and not elem['class']:
            del elem['class']
    
    # Generate the plain text string with spans and text
    pinyin_str = ''.join([str(elem) for elem in soup.body.children]) if soup.body else str(soup)
    return pinyin_str.strip()


def convert_hanzi_to_styled(hanzi_html):
    """Convert hanzi HTML to styled HTML with colors."""
    soup = BeautifulSoup(hanzi_html, 'html.parser')
    # Process tone spans
    for span in soup.find_all('span', class_=re.compile(r'tone-\d')):
        classes = span.get('class', [])
        tone_class = next((c for c in classes if c.startswith('tone-')), None)
        if tone_class:
            tone = int(tone_class.split('-')[1])
            color = tone_colors.get(tone, '')
            span['style'] = f'color: {color};'
            del span['class']  # Remove class attribute
    
    # Cleanup attributes
    for elem in soup.find_all():
        if 'lang' in elem.attrs:
            del elem['lang']
        if 'class' in elem.attrs and not elem['class']:
            del elem['class']
    
    # Return processed HTML
    return str(soup).strip()


def cache_audio(audio_url):
    """Trigger API call to cache audio."""
    try:
        import requests
        requests.get(audio_url, timeout=5)
    except Exception as e:
        print(f"Error caching audio: {e}")


class ScrapingService:
    """Web scraping service using Selenium - exact copy from old app."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        try:
            # Firefox options for headless mode
            firefox_options = Options()
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--headless")
            firefox_options.headless = True
            
            # Essential preferences for headless mode
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("marionette.enabled", True)
            firefox_options.set_preference("toolkit.telemetry.reportingpolicy.firstRun", False)
            
            # Initialize driver
            self.driver = webdriver.Firefox(options=firefox_options)
            self.driver.set_window_size(1920, 1080)
            self.wait = WebDriverWait(self.driver, 15)
            print("Selenium WebDriver initialized")
        except Exception as e:
            print(f"Failed to initialize WebDriver: {e}")
            self.driver = None
            self.wait = None
    
    def _ensure_driver(self):
        """Ensure driver is initialized."""
        if self.driver is None:
            self._init_driver()
        return self.driver is not None
    
    def scrape_chinese_sentences(self, word: str) -> List[Dict]:
        """Scrape example sentences from ChineseBoost."""
        if not self._ensure_driver():
            return []
        
        encoded_word = urllib.parse.quote(word)
        url = f"https://www.chineseboost.com/chinese-example-sentences?query={encoded_word}"
        self.driver.get(url)
        
        data = []
        
        # Scrape current page
        self._process_page(data)
        
        # Navigate to next pages
        counter = 0
        while self._navigate_to_next_page() and counter < 2:
            counter += 1
            self._process_page(data)
        
        return data
    
    def _process_page(self, data: List[Dict]):
        """Process a page of ChineseBoost results."""
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.card')
            
            for card in cards:
                try:
                    liju = card.find_element(By.CSS_SELECTOR, 'div.liju')
                    
                    # Hanzi processing
                    hanzi_element = liju.find_element(By.CSS_SELECTOR, 'p.hanzi')
                    hanzi_html = hanzi_element.get_attribute('innerHTML').strip()
                    chinese_sentence = extract_plain_hanzi(hanzi_html)
                    styled_hanzi = convert_hanzi_to_styled(hanzi_html)
                    
                    # Pinyin processing
                    pinyin_element = liju.find_element(By.CSS_SELECTOR, 'p.pinyin')
                    pinyin_html = pinyin_element.get_attribute('innerHTML').strip()
                    styled_pinyin = convert_pinyin_to_styled(pinyin_html)
                    
                    # Translation processing
                    translation_element = liju.find_element(By.CSS_SELECTOR, 'p.yingwen')
                    translation = translation_element.text.strip()
                    
                    # Source processing
                    source_span = liju.find_element(By.CSS_SELECTOR, 'small.text-muted')
                    anchors = source_span.find_elements(By.TAG_NAME, 'a')
                    source = {
                        'name': anchors[0].text.strip() if anchors else '',
                        'url': anchors[0].get_attribute('href').strip() if anchors else ''
                    }
                    
                    data.append({
                        'chinese_sentence': chinese_sentence,
                        'styled_pinyin': styled_pinyin,
                        'styled_hanzi': styled_hanzi,
                        'translation': translation,
                        'source_name': source['name'],
                        'source_link': source['url']
                    })
                except Exception as e:
                    print(f"Error processing card: {e}")
        except Exception as e:
            print(f"Error processing page: {e}")
    
    def _navigate_to_next_page(self) -> bool:
        """Navigate to next page of results."""
        try:
            pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.pagination')
            next_buttons = pagination.find_elements(By.CSS_SELECTOR, 'li.page-item a[rel="next"]')
            if next_buttons:
                next_button = next_buttons[0]
                parent_li = next_button.find_element(By.XPATH, '..')
                if 'disabled' not in parent_li.get_attribute('class'):
                    next_button.click()
                    return True
        except Exception as e:
            print(f"Pagination error: {e}")
        return False
    
    def scrape_mdbg(self, character: str) -> List[Dict]:
        """Scrape word details from MDBG dictionary."""
        if not self._ensure_driver():
            return []
        
        app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
        tts_api_url = f"{app_url}/api/tts"
        
        self.driver.get(f"https://www.mdbg.net/chinese/dictionary?page=worddict&wdrst=0&wdqb={character}")
        results = []
        
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tr.row"))
            )
            entries = self.driver.find_elements(By.CSS_SELECTOR, "tr.row")
            print(f"MDBG entries found: {len(entries)}")
            
            for entry in entries:
                try:
                    # Extract basic components
                    term = entry.find_element(By.CSS_SELECTOR, "td.head .hanzi").text.strip()
                    raw_pinyin = [span.text.strip() for span in entry.find_elements(By.CSS_SELECTOR, "td.head .pinyin span")]
                    definition = entry.find_element(By.CSS_SELECTOR, "td.details .defs").text.replace("\n", ", ").strip()
                    
                    # Style pinyin and term
                    pinyin, styled_term = style_scraped_pinyin(raw_pinyin, term)
                    
                    # Audio extraction - use new API
                    audio_url = f"{tts_api_url}?hanzi={quote(term)}"
                    threading.Thread(target=cache_audio, args=(audio_url,)).start()
                    
                    # Stroke order extraction
                    stroke_gifs = []
                    try:
                        stroke_link = entry.find_element(By.CSS_SELECTOR, "img[src*='brush2.png']").find_element(By.XPATH, "..").get_attribute("href")
                        original_window = self.driver.current_window_handle
                        self.driver.switch_to.new_window('tab')
                        self.driver.get(stroke_link)
                        WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='gif.php']")))
                        gifs = [img.get_attribute("src") for img in self.driver.find_elements(By.CSS_SELECTOR, "img[src*='gif.php']")]
                        stroke_gifs = gifs[:6]  # Limit to first 6 strokes
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                    except Exception as e:
                        stroke_gifs = []
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(self.driver.window_handles[1])
                            self.driver.close()
                            self.driver.switch_to.window(original_window)
                    
                    # Traditional character
                    traditional = ""
                    try:
                        traditional = entry.find_element(By.CSS_SELECTOR, "td.tail .hanzi").text.strip()
                    except:
                        pass
                    
                    results.append({
                        'term': term,
                        'styled_term': styled_term,
                        'pinyin': pinyin,
                        'definition': definition,
                        'example_link': "",
                        'audio_url': audio_url,
                        'stroke_order': ", ".join(stroke_gifs) if stroke_gifs else "",
                        'traditional': traditional
                    })
                except Exception as e:
                    print(f"Error processing MDBG entry: {str(e)}")
                    continue
        except Exception as e:
            print(f"MDBG scraping failed: {str(e)}")
        
        return results
    
    def scrape_word_details(self, character: str) -> Tuple:
        """
        Scrape complete word details - exact copy from old app.
        Returns: (pinyin, definition, stroke_gifs, pronunciation, example_link, 
                  exemplary_image, meaning, reading, component1, component2, 
                  styled_term, usage_examples, real_usage_examples)
        """
        if not self._ensure_driver():
            # Return empty data if driver not available
            return ("", "", "", "", "", "", "", "", "", "", "", "[]", "[]")
        
        app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
        tts_api_url = f"{app_url}/api/tts"
        
        try:
            # Get example sentences from ChineseBoost
            reading_results = self.scrape_chinese_sentences(character)
            
            # Build component2 and reading from ChineseBoost results
            component2 = ""
            reading = ""
            if reading_results:
                try:
                    component2_parts = []
                    for i in range(min(6, len(reading_results))):
                        audio_url = f"{tts_api_url}?hanzi={quote(reading_results[i]['chinese_sentence'])}"
                        part = f"""{reading_results[i]['styled_hanzi']}<br>{reading_results[i]['styled_pinyin']}<button id=\"button{i+1}\" onclick=\"document.getElementById('audio{i+1}').play()\" style=\"padding: 5px 10px; background: var(--button-bg); color: var(--button-text); font-size: 16px; cursor: pointer; vertical-align: middle;\">▶</button><audio id=\"audio{i+1}\" src=\"{audio_url}\" preload=\"auto\"></audio><br>{reading_results[i]['translation']}"""
                        component2_parts.append(part)
                    component2 = '<div style="text-align: center;">Developer note: work in progress<br><br>' + "<br><br>".join(component2_parts) + '</div>'
                except Exception as e:
                    print(f"Error building component2: {e}")
                
                try:
                    reading_parts = []
                    for i in range(min(6, len(reading_results))):
                        part = f"{reading_results[i]['styled_hanzi']}<br>{reading_results[i]['styled_pinyin']}<br>"
                        reading_parts.append(part)
                    reading = '<div style="text-align: center;">Developer note: work in progress<br><br>' + "<br><br>".join(reading_parts) + '</div>'
                except Exception as e:
                    print(f"Error building reading: {e}")
            
            # Get main word data from MDBG
            results = self.scrape_mdbg(character)
            
            if not results:
                return ("", "", "", "", "", "", "", "", "", "", "", "[]", "[]")
            
            # Prioritize exact match
            try:
                if results[0]["term"] != character:
                    result_candidates = []
                    for i in range(len(results)):
                        if results[i]['term'] == character:
                            result_candidates.append({
                                "term": results[i]['term'],
                                "definition": results[i]['definition'],
                                "index": i
                            })
                    if result_candidates:
                        candidate_index = 0
                        longest_definition = 0
                        for i in range(len(result_candidates)):
                            if len(result_candidates[i]["definition"]) > longest_definition:
                                longest_definition = len(result_candidates[i]["definition"])
                                candidate_index = int(result_candidates[i]["index"])
                        results.insert(0, results[candidate_index])
                        results.pop(candidate_index + 1)
            except Exception as e:
                print(f"Error reordering results: {e}")
            
            # Build meaning from character breakdown
            meaning = ""
            
            # component1 placeholder (same as old app)
            component1 = 'Developer Note: "Reading" card type is still work in progress (will be fixed by standard importing of cards in the near future)'
            
            # Build real_usage_examples from reading_results
            real_usage_examples = []
            for idx, result in enumerate(reading_results[:6], 1):
                audio_url = f"{tts_api_url}?hanzi={quote(result['chinese_sentence'])}"
                html = f'''<div style="margin-bottom: 20px;">
<div style="font-size: 20px; font-weight: bold;">{result['styled_hanzi']}</div>
<div style="font-size: 18px; display: inline-block;">
<span style="font-size: 20px; font-weight: bold;">{result['styled_pinyin']} </span>
</div>
<button id="button{idx}" onclick="document.getElementById('audio{idx}').play()" 
    style="padding: 5px 10px; background: var(--button-bg); color: var(--button-text); 
    font-size: 16px; cursor: pointer; vertical-align: middle;">▶</button>
<audio id="audio{idx}" src="{audio_url}" preload="auto"></audio>
<div style="font-size: 16px; margin-top: 10px;">{result['translation']}</div>
</div>'''
                real_usage_examples.append(html)
            
            real_usage_examples_str = ''.join(real_usage_examples)
            
            # Get exemplary_image from Unsplash
            exemplary_image = ""
            unsplash_api_key = os.environ.get('UNSPLASH_API_KEY')
            if unsplash_api_key:
                try:
                    import requests
                    url = 'https://api.unsplash.com/search/photos'
                    params = {
                        'query': character,
                        'page': 1,
                        'per_page': 1,
                        'order_by': 'relevant',
                        'client_id': unsplash_api_key
                    }
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data['results']:
                            exemplary_image = data['results'][0]['urls']['regular']
                except Exception as e:
                    print(f"Error getting Unsplash image: {e}")
            
            # Return format matches old app exactly
            return (
                results[0]["pinyin"],           # 0: pinyin
                results[0]['definition'],        # 1: definition (translation)
                results[0]["stroke_order"],      # 2: stroke_order (stroke_gifs)
                results[0]["audio_url"],         # 3: audio_url (pronunciation)
                results[0]['example_link'],      # 4: example_link
                exemplary_image,                 # 5: exemplary_image
                meaning,                         # 6: meaning
                reading,                         # 7: reading
                component1,                      # 8: component1
                component2,                      # 9: component2
                results[0]["styled_term"],       # 10: styled_term
                str(reading_results),            # 11: usage_examples
                real_usage_examples_str          # 12: real_usage_examples
            )
            
        except Exception as e:
            print(f"Error in scrape_word_details: {e}")
            traceback.print_exc()
            return ("", "", "", "", "", "", "", "", "", "", "", "[]", "[]")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


# Global instance
scraping_service = ScrapingService()
