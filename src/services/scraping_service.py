"""Efficient web scraping service using requests + minimal Playwright."""
import os
import re
import urllib.parse
import threading
import traceback
import time
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

import requests
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


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

    def scrape_chinese_sentences(self, word: str) -> List[Dict]:
        url = f"https://www.chineseboost.com/chinese-example-sentences?query={urllib.parse.quote(word)}"
        
        try:
            resp = self.session.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.find_all('div', class_='card')
            
            data = []
            for card in cards:
                try:
                    liju = card.find('div', class_='liju')
                    if not liju:
                        continue
                    
                    hanzi_element = liju.find('p', class_='hanzi')
                    pinyin_element = liju.find('p', class_='pinyin')
                    translation_element = liju.find('p', class_='yingwen')
                    
                    if not (hanzi_element and pinyin_element and translation_element):
                        continue
                    
                    hanzi_html = hanzi_element.decode_contents() if hanzi_element else ''
                    chinese_sentence = extract_plain_hanzi(hanzi_html)
                    styled_hanzi = convert_hanzi_to_styled(hanzi_html)
                    
                    pinyin_html = pinyin_element.decode_contents() if pinyin_element else ''
                    styled_pinyin = convert_pinyin_to_styled(pinyin_html)
                    
                    translation = translation_element.get_text().strip()
                    
                    source = {'name': '', 'url': ''}
                    try:
                        source_span = liju.find('small', class_='text-muted')
                        if source_span:
                            a = source_span.find('a')
                            if a:
                                source = {
                                    'name': a.get_text().strip(),
                                    'url': a.get('href', '').strip()
                                }
                    except:
                        pass
                    
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
            
            return data
        except Exception as e:
            print(f"Error scraping ChineseBoost: {e}")
            return []

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

    def scrape_writtenchinese(self, character: str) -> Tuple[str, List[str]]:
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
                page.goto('https://dictionary.writtenchinese.com')
                page.wait_for_load_state('domcontentloaded')
                
                page.fill('#searchKey', character)
                page.press('#searchKey', 'Enter')
                page.wait_for_timeout(5000)
                
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
                
                page.goto(f'https://dictionary.writtenchinese.com/{worddetail_href}')
                page.wait_for_timeout(5000)
                
                symbol = page.query_selector('div.symbol-layer')
                if symbol:
                    imgs = symbol.query_selector_all('img')
                    stroke_order_urls = [
                        img.get_attribute('src') for img in imgs
                        if img.get_attribute('src') and 'giffile' in img.get_attribute('src')
                    ]
                
                if len(str(character)) > 1:
                    try:
                        table = page.query_selector('table.with-flex')
                        if table:
                            rows = table.query_selector_all('tr')[1:]
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
                
            finally:
                page.close()
            
            meaning = " ".join(meanings_list) if meanings_list else ""
            return meaning, stroke_order_urls
            
        except Exception as e:
            print(f"WrittenChinese scraping failed: {e}")
            return "", []

    def scrape_word_details(self, character: str, progress_callback=None) -> Tuple:
        def report(stage, message):
            if progress_callback:
                progress_callback(stage, message)
        
        try:
            report("chineseboost", f"🔍 Scraping ChineseBoost for {character}...")
            reading_results = self.scrape_chinese_sentences(character)
            
            component2 = ""
            reading = ""
            app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
            tts_api_url = f"{app_url}/api/tts"
            
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
            
            report("mdbg", f"📖 Scraping MDBG for {character}...")
            results = self.scrape_mdbg(character)
            
            if not results:
                return ("", "", "", "", "", "", "", "", "", "", "", "[]", "")
            
            report("writtenchinese", f"🎨 Scraping WrittenChinese for {character} GIFs...")
            meaning, stroke_urls = self.scrape_writtenchinese(character)
            if stroke_urls:
                # Make URLs absolute
                abs_urls = [f'https://dictionary.writtenchinese.com{url}' for url in stroke_urls]
                results[0]['stroke_order'] = ", ".join(abs_urls)
            
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
            
            component1 = 'Developer Note: "Reading" card type is still work in progress (will be fixed by standard importing of cards in the near future)'
            
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
            
            report("done", f"✅ {character} complete!")
            
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
                str(reading_results),
                real_usage_examples_str
            )
            
        except Exception as e:
            print(f"Error in scrape_word_details: {e}")
            traceback.print_exc()
            return ("", "", "", "", "", "", "", "", "", "", "", "[]", "")


scraping_service = ScrapingService()
