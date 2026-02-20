"""Efficient web scraping service using requests + minimal Playwright."""
import os
import re
import urllib.parse
import threading
import traceback
import json
import time
import asyncio
import concurrent.futures
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

import requests
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Thread pool for running Playwright in async contexts
_playwright_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)


tone_colors = {
    1: '#ff0000',
    2: '#ffaa00',
    3: '#00aa00',
    4: '#0000ff',
    0: 'var(--regular-text)'
}


def get_tone_number(syllable):
    tone_mapping = {
        'ā': 1, 'ō': 1, 'ē': 1, 'ī': 1, 'ū': 1, 'ǖ': 1,
        'á': 2, 'ó': 2, 'é': 2, 'í': 2, 'ú': 2, 'ǘ': 2,
        'ǎ': 3, 'ǒ': 3, 'ě': 3, 'ǐ': 3, 'ǔ': 3, 'ǚ': 3,
        'à': 4, 'ò': 4, 'è': 4, 'ì': 4, 'ù': 4, 'ǜ': 4,
    }
    for char in syllable:
        if char in tone_mapping:
            return tone_mapping[char]
    return 0


def chinese_to_styled_texts(chinese_str):
    """Convert Chinese string to styled pinyin and hanzi with tone colors."""
    pinyin_list = []
    char_list = []
    
    for char in chinese_str:
        try:
            import pypinyin
            py = pypinyin.pinyin(char, style=pypinyin.Style.TONE)[0][0]
        except:
            py = char
        
        tone = get_tone_number(py)
        color = tone_colors.get(tone, 'var(--regular-text)')
        
        styled_py = f'<span style="color:{color}">{py}</span>'
        styled_char = f'<span style="color:{color}">{char}</span>'
        
        pinyin_list.append(styled_py)
        char_list.append(styled_char)
    
    return ' '.join(pinyin_list), ''.join(char_list)


def chinese_to_styled_texts_corrected(chinese_str):
    """
    Converts a Chinese string into styled Pinyin and styled Hanzi characters
    with tone-based coloring. Handles punctuation and whitespace correctly.
    """
    try:
        import pypinyin
        from pypinyin import Style
        
        pinyin_list_of_lists = pypinyin.pinyin(
            chinese_str, 
            style=Style.TONE, 
            heteronym=False, 
            errors='neutralize'
        )
    except:
        # Fallback if pypinyin not available
        return chinese_str, chinese_str

    pinyin_spans = []
    char_spans = []

    for char_in_word, pinyin_syllables_for_char in zip(chinese_str, pinyin_list_of_lists):
        if not pinyin_syllables_for_char:
            pinyin_spans.append(char_in_word)
            char_spans.append(char_in_word)
            continue

        syllable = pinyin_syllables_for_char[0]

        if char_in_word == syllable:
            pinyin_spans.append(char_in_word)
            char_spans.append(char_in_word)
        else:
            tone = get_tone_number(syllable)
            color = tone_colors.get(tone, tone_colors[0])

            if color != tone_colors[0]:
                pinyin_spans.append(f'<span style="color:{color}">{syllable}</span>')
                char_spans.append(f'<span style="color:{color}">{char_in_word}</span>')
            else:
                pinyin_spans.append(syllable)
                char_spans.append(char_in_word)

    return ' '.join(pinyin_spans), ''.join(char_spans)


def style_scraped_pinyin(pinyin_list, word_str):
    styled_syllables = []
    syllables = pinyin_list if isinstance(pinyin_list, list) else [pinyin_list]
    word_syllables = [char for char in word_str]
    styled_word_syllables = []
    
    for i in range(len(syllables)):
        tone = get_tone_number(syllables[i])
        color = tone_colors.get(tone, '')
        styled = f'<span style="color:{color}">{syllables[i]}</span>'
        styled_syllables.append(styled)
        if i < len(word_syllables):
            styled = f'<span style="color:{color}">{word_syllables[i]}</span>'
            styled_word_syllables.append(styled)
    
    return ' '.join(styled_syllables), ''.join(styled_word_syllables)


def extract_plain_hanzi(hanzi_html):
    soup = BeautifulSoup(hanzi_html, 'html.parser')
    return soup.get_text()


def convert_pinyin_to_styled(pinyin_html):
    soup = BeautifulSoup(pinyin_html, 'html.parser')
    for span in soup.find_all('span', class_=re.compile(r'tone-\d')):
        classes = span.get('class', [])
        tone_class = next((c for c in classes if c.startswith('tone-')), None)
        if tone_class:
            tone = int(tone_class.split('-')[1])
            color = tone_colors.get(tone, '')
            span['style'] = f'color: {color};'
            del span['class']
    
    for elem in soup.find_all(class_=lambda x: x in ['pinyin sentence', 'pinyin word']):
        elem.unwrap()
    
    for elem in soup.find_all(class_='non-pinyin'):
        elem.replace_with(elem.get_text())
    
    for elem in soup.find_all():
        if 'lang' in elem.attrs:
            del elem['lang']
        if 'class' in elem.attrs and not elem['class']:
            del elem['class']
    
    pinyin_str = ''.join([str(elem) for elem in soup.body.children]) if soup.body else str(soup)
    return pinyin_str.strip()


def convert_hanzi_to_styled(hanzi_html):
    soup = BeautifulSoup(hanzi_html, 'html.parser')
    for span in soup.find_all('span', class_=re.compile(r'tone-\d')):
        classes = span.get('class', [])
        tone_class = next((c for c in classes if c.startswith('tone-')), None)
        if tone_class:
            tone = int(tone_class.split('-')[1])
            color = tone_colors.get(tone, '')
            span['style'] = f'color: {color};'
            del span['class']
    
    for elem in soup.find_all():
        if 'lang' in elem.attrs:
            del elem['lang']
        if 'class' in elem.attrs and not elem['class']:
            del elem['class']
    
    return str(soup).strip()


def cache_audio(audio_url):
    try:
        requests.get(audio_url, timeout=5)
    except Exception as e:
        print(f"Error caching audio: {e}")


def get_deepseek_chinese_sentences(deepseek_api_key: str, chinese_word: str) -> List[Dict]:
    """
    Get 3 AI-generated example sentences from DeepSeek API.
    Returns list of dicts with 'chinese', 'pinyin', 'english' keys.
    """
    if not deepseek_api_key:
        print("No DeepSeek API key provided")
        return []
    
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {deepseek_api_key}"
    }
    prompt = f"""Please provide three exemplary Chinese sentences using the word "{chinese_word}". Ensure that the vocabulary used in these sentences is at the same or a lower HSK level than "{chinese_word}". For each Chinese sentence, provide its Pinyin on the next line starting with "Pinyin: ", and its English translation on the following line starting with "Translation: ". Return the result as a JSON array where each element is an object with "chinese", "pinyin", and "english" keys."""
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "n": 1
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        json_response = response.json()
        
        if 'choices' in json_response and len(json_response['choices']) > 0 and 'message' in json_response['choices'][0] and 'content' in json_response['choices'][0]['message']:
            content = json_response['choices'][0]['message']['content']

            try:
                json_start = content.find('[')
                json_end = content.rfind(']')

                if json_start != -1 and json_end != -1 and json_start < json_end:
                    content = content[json_start:json_end + 1]
                
                results = json.loads(content)
                if isinstance(results, list) and len(results) == 3 and all(isinstance(item, dict) and 'chinese' in item and 'pinyin' in item and 'english' in item for item in results):
                    return results
                else:
                    print(f"Unexpected format of the response content: {content}")
                    return []

            except json.JSONDecodeError:
                lines = content.strip().split('\n')
                if len(lines) >= 9:
                    parsed_results = []
                    for i in range(0, len(lines) - 2, 3):
                        chinese_match = re.search(r'"chinese": "(.*)"', lines[i])
                        pinyin_match = re.search(r'"pinyin": "(.*)"', lines[i + 1])
                        english_match = re.search(r'"english": "(.*)"', lines[i + 2])
                        if chinese_match and pinyin_match and english_match:
                            parsed_results.append({
                                "chinese": chinese_match.group(1),
                                "pinyin": pinyin_match.group(1),
                                "english": english_match.group(1)
                            })
                    if len(parsed_results) == 3:
                        return parsed_results
                    else:
                        print(f"Could not parse content into expected format: {content}")
                        return []
                else:
                    print(f"Could not split response into three sets of information: {content}")
                    return []
        else:
            print(f"Unexpected structure in the API response: {json_response}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with the DeepSeek API: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred in DeepSeek API: {e}")
        return []


class ScrapingService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.playwright = None
        self.browser = None
    
    def _get_playwright(self):
        if not PLAYWRIGHT_AVAILABLE:
            return None
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
        return self.playwright
    
    def close(self):
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
            self.playwright = None

    def scrape_mdbg(self, character: str) -> List[Dict]:
        url = f"https://www.mdbg.net/chinese/dictionary?page=worddict&wdrst=0&wdqb={urllib.parse.quote(character)}"
        
        try:
            resp = self.session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            entries = soup.find_all('tr', class_='row')
            
            results = []
            app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
            tts_api_url = f"{app_url}/api/tts"
            
            for entry in entries:
                try:
                    head = entry.find('td', class_='head')
                    if not head:
                        continue
                    
                    hanzi_div = head.find('div', class_='hanzi')
                    term = hanzi_div.get_text() if hanzi_div else ''
                    
                    pinyin_div = head.find('div', class_='pinyin')
                    pinyin_spans = pinyin_div.find_all('span') if pinyin_div else []
                    raw_pinyin = [s.get_text() for s in pinyin_spans]
                    
                    details = entry.find('td', class_='details')
                    defs_div = details.find('div', class_='defs') if details else None
                    definition = defs_div.get_text().replace('\n', ', ').strip() if defs_div else ''
                    
                    pinyin, styled_term = style_scraped_pinyin(raw_pinyin, term)
                    
                    audio_url = f"{tts_api_url}?hanzi={quote(term)}"
                    threading.Thread(target=cache_audio, args=(audio_url,)).start()
                    
                    traditional = ''
                    tail = entry.find('td', class_='tail')
                    if tail:
                        trad_div = tail.find('div', class_='hanzi')
                        if trad_div:
                            traditional = trad_div.get_text().strip()
                    
                    results.append({
                        'term': term,
                        'styled_term': styled_term,
                        'pinyin': pinyin,
                        'definition': definition,
                        'example_link': '',
                        'audio_url': audio_url,
                        'stroke_order': '',
                        'traditional': traditional
                    })
                except Exception as e:
                    print(f"Error processing MDBG entry: {e}")
                    continue
            
            return results
        except Exception as e:
            print(f"MDBG scraping failed: {e}")
            return []

    def _scrape_writtenchinese_sync(self, character: str) -> Tuple[str, List[str]]:
        """Synchronous implementation of Written Chinese scraping."""
        if not PLAYWRIGHT_AVAILABLE:
            print("Playwright not available, skipping WrittenChinese")
            return "", []
        
        try:
            p = self._get_playwright()
            if not p or not self.browser:
                return "", []
            
            page = self.browser.new_page()
            page.set_default_timeout(30000)
            
            meanings_list = []
            stroke_order_urls = []
            
            try:
                # Go to Written Chinese dictionary
                page.goto('https://dictionary.writtenchinese.com')
                page.wait_for_load_state('domcontentloaded')
                
                # Search for the character
                page.fill('#searchKey', character)
                page.press('#searchKey', 'Enter')
                page.wait_for_timeout(3000)
                
                # Look for "Learn more" link
                links = page.query_selector_all('a.learn-more-link')
                worddetail_href = None
                for link in links:
                    href = link.get_attribute('href')
                    if href and 'worddetail' in href:
                        worddetail_href = href
                        break
                
                if not worddetail_href:
                    page.close()
                    return "", []
                
                # Navigate to word detail page
                page.goto(f'https://dictionary.writtenchinese.com/{worddetail_href}')
                page.wait_for_timeout(3000)
                
                # Extract stroke order GIFs from symbol-layer
                try:
                    gif_elements = page.query_selector_all('div.symbol-layer img')
                    for gif in gif_elements:
                        src = gif.get_attribute('src')
                        if src and 'giffile.action' in src:
                            # Ensure full URL
                            if src.startswith('http'):
                                stroke_order_urls.append(src)
                            else:
                                stroke_order_urls.append(f'https://dictionary.writtenchinese.com{src}')
                except Exception as e:
                    print(f"Error extracting stroke GIFs: {e}")
                
                # For multi-character words, extract individual character meanings
                if len(str(character)) > 1:
                    try:
                        character_table = page.query_selector('table.with-flex')
                        if character_table:
                            rows = character_table.query_selector_all('tr')[1:]  # Skip header
                            for row in rows:
                                try:
                                    char_cell = row.query_selector('td.smbl-cstm-wrp.word span')
                                    pinyin_cell = row.query_selector('td.pinyin a')
                                    meaning_cell = row.query_selector('td.txt-cell')
                                    
                                    if char_cell and pinyin_cell and meaning_cell:
                                        char = char_cell.inner_text()
                                        pinyin_text = pinyin_cell.inner_text()
                                        meaning = meaning_cell.inner_text()
                                        
                                        styled_pinyin, styled_char = chinese_to_styled_texts(char)
                                        entry = f"🔂 {styled_char} ({styled_pinyin}): {meaning}"
                                        if entry not in meanings_list:
                                            meanings_list.append(entry)
                                except:
                                    continue
                    except Exception as e:
                        print(f"Error getting meanings table: {e}")
                else:
                    # For single character, get the definition
                    try:
                        definition_element = page.query_selector('td.txt-cell')
                        if definition_element:
                            meaning = definition_element.inner_text()
                            styled_pinyin, styled_char = chinese_to_styled_texts(character)
                            entry = f"🔂 {styled_char} ({styled_pinyin}): {meaning}"
                            if entry not in meanings_list:
                                meanings_list.append(entry)
                    except:
                        pass
                
            finally:
                page.close()
            
            meaning = " ".join(meanings_list) if meanings_list else ""
            return meaning, stroke_order_urls
            
        except Exception as e:
            print(f"WrittenChinese scraping failed: {e}")
            traceback.print_exc()
            return "", []

    def scrape_writtenchinese(self, character: str) -> Tuple[str, List[str]]:
        """
        Scrape stroke order GIFs from Written Chinese dictionary.
        Handles both sync and async contexts.
        Returns: (meaning, stroke_order_urls)
        """
        # Check if we're in an async context
        try:
            asyncio.get_running_loop()
            # We're in an async context - run in thread pool
            future = _playwright_executor.submit(self._scrape_writtenchinese_sync, character)
            return future.result(timeout=60)
        except RuntimeError:
            # No running loop - run directly
            return self._scrape_writtenchinese_sync(character)

    def scrape_word_details(self, character: str, progress_callback=None) -> Tuple:
        """
        Scrape all word details.
        Returns: (pinyin, definition, stroke_order, audio_url, example_link, 
                  exemplary_image, meaning, reading, component1, component2, 
                  styled_term, usage_examples_json_str, real_usage_examples_html)
        """
        def report(stage, message):
            if progress_callback:
                progress_callback(stage, message)
        
        try:
            app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
            tts_api_url = f"{app_url}/api/tts"
            deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
            
            # Scrape MDBG for basic word info
            report("mdbg", f"📖 Scraping MDBG for {character}...")
            results = self.scrape_mdbg(character)
            
            if not results:
                return ("", "", "", "", "", "", "", "", "", "", "", "[]", "")
            
            # Reorder results to prioritize exact match
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
            
            # Scrape Written Chinese for stroke GIFs and meaning
            report("writtenchinese", f"🎨 Scraping WrittenChinese for {character} GIFs...")
            meaning, stroke_urls = self.scrape_writtenchinese(character)
            if stroke_urls:
                results[0]['stroke_order'] = ", ".join(stroke_urls)
            
            # Get exemplary image from Unsplash
            report("unsplash", f"🖼️ Fetching image from Unsplash for {character}...")
            exemplary_image = ""
            unsplash_api_key = os.environ.get('UNSPLASH_API_KEY')
            if unsplash_api_key:
                try:
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
            
            results[0]['exemplary_image'] = exemplary_image
            
            # Generate AI example sentences using DeepSeek
            report("deepseek", f"🤖 Generating AI examples for {character}...")
            ai_examples = []
            deepseek_results = []
            
            if deepseek_api_key:
                try:
                    deepseek_data = get_deepseek_chinese_sentences(deepseek_api_key, character)
                    if deepseek_data and len(deepseek_data) == 3:
                        for i, item in enumerate(deepseek_data):
                            chinese_sentence = item.get('chinese', '')
                            english = item.get('english', '')
                            
                            # Style the Chinese sentence
                            styled_pinyin, styled_chinese = chinese_to_styled_texts_corrected(chinese_sentence)
                            
                            # Build audio URL
                            audio_url = f"{tts_api_url}?hanzi={quote(chinese_sentence)}"
                            
                            deepseek_results.append({
                                'chinese': styled_chinese,
                                'pinyin': styled_pinyin,
                                'english': english,
                                'audio_url': audio_url
                            })
                            
                            # Build HTML for real_usage_examples
                            html = f'''<div style="margin-bottom: 20px;">
<div style="font-size: 20px; font-weight: bold;">{styled_chinese}</div>
<div style="font-size: 18px; display: inline-block;">
<span style="font-size: 20px; font-weight: bold;">{styled_pinyin} </span>
</div>
<button id="button{i+1}" onclick="document.getElementById('audio{i+1}').play()" 
    style="padding: 5px 10px; background: var(--button-bg); color: var(--button-text); 
    font-size: 16px; cursor: pointer; vertical-align: middle;">▶</button>
<audio id="audio{i+1}" src="{audio_url}" preload="auto"></audio>
<div style="font-size: 16px; margin-top: 10px;">{english}</div>
</div>'''
                            ai_examples.append(html)
                            
                        # Trigger audio caching
                        for item in deepseek_results:
                            threading.Thread(target=cache_audio, args=(item['audio_url'],)).start()
                except Exception as e:
                    print(f"Error generating AI examples: {e}")
                    traceback.print_exc()
            
            # Build real_usage_examples HTML (from DeepSeek AI examples)
            real_usage_examples_str = ''.join(ai_examples)
            
            # Build anki_usage_examples from OTHER MDBG results (results[1:])
            # This contains alternative dictionary entries formatted as HTML
            anki_usage_examples_parts = []
            for idx, result in enumerate(results[1:6], 1):  # Get up to 5 other results
                audio_url = f"{tts_api_url}?hanzi={quote(result['term'])}"
                html = f'''<div style="margin-bottom: 20px;">
<div style="font-size: 20px; font-weight: bold;">{result['styled_term']}</div>
<div style="font-size: 18px; display: inline-block;">
<span style="font-size: 20px; font-weight: bold;">{result['pinyin']} </span>
</div>
<button id="button{idx}" onclick="document.getElementById('audio{idx}').play()" 
    style="padding: 5px 10px; background: var(--button-bg); color: var(--button-text); 
    font-size: 16px; cursor: pointer; vertical-align: middle;">▶</button>
<audio id="audio{idx}" src="{audio_url}" preload="auto"></audio>
<div style="font-size: 16px; margin-top: 10px;">{result['definition']}</div>
</div>'''
                anki_usage_examples_parts.append(html)
                # Trigger audio caching for this term
                threading.Thread(target=cache_audio, args=(audio_url,)).start()
            
            anki_usage_examples_str = ''.join(anki_usage_examples_parts)
            
            # Chinese Boost reading_results is now empty (deprecated)
            reading_results = []
            
            # Build component1 and component2 (legacy fields, kept empty or minimal)
            component1 = 'Developer Note: "Reading" card type is still work in progress (will be fixed by standard importing of cards in the near future)'
            component2 = ""
            reading = ""
            
            report("done", f"✅ {character} complete!")
            
            # Return format matching old app exactly:
            # (pinyin, definition, stroke_order, audio_url, example_link, exemplary_image, 
            #  meaning, reading, component1, component2, styled_term, 
            #  usage_examples_json_str, real_usage_examples_html, anki_usage_examples_html)
            return (
                results[0]["pinyin"],
                results[0]['definition'],
                results[0]["stroke_order"],
                results[0]["audio_url"],
                results[0]['example_link'],
                results[0]['exemplary_image'],
                meaning,
                reading,
                component1,
                component2,
                results[0]["styled_term"],
                str(reading_results),  # Empty list as string (Chinese Boost removed)
                real_usage_examples_str,  # AI-generated examples from DeepSeek
                anki_usage_examples_str  # Other MDBG dictionary entries
            )
            
        except Exception as e:
            print(f"Error in scrape_word_details: {e}")
            traceback.print_exc()
            return ("", "", "", "", "", "", "", "", "", "", "", "[]", "")


scraping_service = ScrapingService()
