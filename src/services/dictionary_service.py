"""Dictionary service for scraping and managing Chinese words."""
import os
import re
import json
import requests
import threading
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO
from urllib.parse import quote
from bs4 import BeautifulSoup
from gtts import gTTS

from src.models.database import db
from src.utils.chinese_utils import chinese_to_styled_pinyin
from src.services.r2_storage import r2_storage


class DictionaryService:
    """Service for Chinese dictionary operations."""
    
    def __init__(self):
        self.deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
        self.unsplash_api_key = os.environ.get('UNSPLASH_API_KEY')
        # Use the app's own TTS API
        self.app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
        self.tts_api_url = f"{self.app_url}/api/tts"
    
    def get_word_details(self, character: str) -> Dict[str, Any]:
        """Get full word details from scraping and APIs."""
        # Get styled pinyin and hanzi
        styled_pinyin, styled_term = chinese_to_styled_pinyin(character)
        
        # Get example sentences from DeepSeek
        examples = self._get_ai_examples(character)
        
        # Get image from Unsplash
        image_url = self._get_unsplash_image(character)
        
        # Generate pronunciation audio - use R2 if available, otherwise local API
        pronunciation = self._get_pronunciation_url(character)
        
        # Get stroke order GIFs
        stroke_gifs = self._get_stroke_gifs(character)
        
        # Format example sentences for Anki
        anki_examples = self._format_anki_examples(examples, character)
        
        # Format real usage examples (same as anki_examples for now)
        real_usage_examples = anki_examples
        
        return {
            'character': character,
            'pinyin': styled_pinyin,
            'styled_term': styled_term,
            'translation': self._get_translation(character),
            'meaning': '',
            'stroke_gifs': ', '.join(stroke_gifs) if stroke_gifs else '',
            'pronunciation': pronunciation,
            'exemplary_image': image_url,
            'anki_usage_examples': anki_examples,
            'real_usage_examples': real_usage_examples,
            'usage_examples': json.dumps(examples) if examples else '[]'
        }
    
    def _get_ai_examples(self, character: str) -> List[Dict[str, str]]:
        """Get AI-generated example sentences from DeepSeek."""
        if not self.deepseek_api_key:
            return []
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        prompt = f"""Please provide three exemplary Chinese sentences using the word "{character}". 
        Ensure that the vocabulary used in these sentences is at the same or a lower HSK level than "{character}". 
        For each Chinese sentence, provide its Pinyin on the next line starting with "Pinyin: ", 
        and its English translation on the following line starting with "Translation: ". 
        Return the result as a JSON array where each element is an object with "chinese", "pinyin", and "english" keys."""
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "n": 1
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            json_response = response.json()
            
            if 'choices' in json_response and len(json_response['choices']) > 0:
                content = json_response['choices'][0]['message']['content']
                
                # Extract JSON from content
                json_start = content.find('[')
                json_end = content.rfind(']')
                
                if json_start != -1 and json_end != -1 and json_start < json_end:
                    content = content[json_start:json_end + 1]
                
                results = json.loads(content)
                
                # Style the pinyin for each example
                for item in results:
                    if 'chinese' in item:
                        styled_pinyin, styled_chinese = chinese_to_styled_pinyin(item['chinese'])
                        item['pinyin'] = styled_pinyin
                        item['chinese'] = styled_chinese
                        # Generate audio URL for this sentence
                        item['audio_url'] = self._get_pronunciation_url(item.get('chinese', '').replace('<span style="color:', '').replace('">', '').replace('</span>', ''))
                
                return results
        except Exception as e:
            print(f"Error getting AI examples: {e}")
        
        return []
    
    def _get_unsplash_image(self, query: str) -> Optional[str]:
        """Get image from Unsplash."""
        if not self.unsplash_api_key:
            return None
        
        try:
            url = 'https://api.unsplash.com/search/photos'
            params = {
                'query': query,
                'page': 1,
                'per_page': 1,
                'order_by': 'relevant',
                'client_id': self.unsplash_api_key
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    return data['results'][0]['urls']['regular']
        except Exception as e:
            print(f"Error getting Unsplash image: {e}")
        
        return None
    
    def _get_pronunciation_url(self, text: str) -> str:
        """Get pronunciation audio URL - uses the app's own TTS API."""
        # Use the app's own TTS API URL format (same as old app but with new domain)
        return f"{self.tts_api_url}?hanzi={quote(text)}"
    
    def _get_stroke_gifs(self, character: str) -> List[str]:
        """Get stroke order GIFs for character."""
        # Return URLs to writtenchinese stroke order GIFs
        gifs = []
        for char in character:
            encoded = quote(char)
            url = f"https://dictionary.writtenchinese.com/giffile.action?&localfile=true&fileName={encoded}.gif"
            gifs.append(url)
        return gifs
    
    def _get_translation(self, character: str) -> str:
        """Get English translation for character."""
        # This would require a dictionary API
        # For now, return placeholder
        return "Translation not available"
    
    def _format_anki_examples(self, examples: List[Dict[str, str]], main_character: str = None) -> str:
        """Format examples for Anki card - matches old app format exactly."""
        if not examples:
            return ""
        
        formatted = []
        for idx, example in enumerate(examples, 1):
            # Get plain text for audio (remove HTML tags)
            chinese_plain = example.get('chinese', '').replace('<span style="color:', '').replace('">', '').replace('</span>', '')
            audio_url = example.get('audio_url') or self._get_pronunciation_url(chinese_plain)
            
            html = f'''<div style="margin-bottom: 20px;">
<div style="font-size: 20px; font-weight: bold;">{example.get('chinese', '')}</div>
<div style="font-size: 18px; display: inline-block;">
<span style="font-size: 20px; font-weight: bold;">{example.get('pinyin', '')} </span>
</div>
<button id="button{idx}" onclick="document.getElementById('audio{idx}').play()" 
    style="padding: 5px 10px; background: var(--button-bg); color: var(--button-text); 
    font-size: 16px; cursor: pointer; vertical-align: middle;">▶</button>
<audio id="audio{idx}" src="{audio_url}" preload="auto"></audio>
<div style="font-size: 16px; margin-top: 10px;">{example.get('english', '')}</div>
</div>'''
            formatted.append(html)
        
        return ''.join(formatted)
    
    def generate_csv(self, user_id: str, deck_id: str = None) -> bytes:
        """Generate CSV export for user's words - matches old app format EXACTLY."""
        import csv
        import io
        
        words = db.get_words_by_user(user_id, deck_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Process each word exactly like the old app
        for word in words:
            character = word.get('character', '')
            styled_term = word.get('styled_term', '')
            pinyin = word.get('pinyin', '')
            translation = word.get('translation', '')
            meaning = word.get('meaning', '')
            
            # Ensure pronunciation uses new API URL
            pronunciation = word.get('pronunciation', '')
            if '212.227.211.88' in pronunciation:
                # Convert old URL to new
                hanzi = character
                pronunciation = self._get_pronunciation_url(hanzi)
            
            example_link = word.get('example_link', '')
            exemplary_image = word.get('exemplary_image', '')
            
            # Use anki_usage_examples if available, otherwise use real_usage_examples
            example_usage = word.get('anki_usage_examples', '') or word.get('real_usage_examples', '')
            
            reading = word.get('reading', '')
            component1 = word.get('component1', '')
            component2 = word.get('component2', '')
            real_usage_examples = word.get('real_usage_examples', '')
            
            # Split stroke GIFs by comma and space (old format)
            stroke_gifs = word.get('stroke_gifs', '')
            stroke_order_list = stroke_gifs.split(", ") if stroke_gifs else []
            stroke_order_fields = stroke_order_list[:6]  # Limit to 6
            
            # Pad to ensure all 6 columns are present
            stroke_order_fields += [''] * (6 - len(stroke_order_fields))
            
            # CSV row format: Hanzi, StyledTerm, Pinyin, Translation, Meaning, Pronunciation, 
            #                 ExampleLink, ExemplaryImage, ExampleUsage, Reading, Component1, Component2, 
            #                 RealUsageExamples, StrokeOrder1-6
            csv_row = [
                character,
                styled_term,
                pinyin,
                translation,
                meaning,
                pronunciation,
                example_link,
                exemplary_image,
                example_usage,
                reading,
                component1,
                component2,
                real_usage_examples
            ] + stroke_order_fields
            
            writer.writerow(csv_row)
        
        return output.getvalue().encode('utf-8')
    
    def generate_anki_preview(self, word: Dict) -> str:
        """Generate HTML preview of Anki card."""
        character = word.get('character', '')
        pinyin = word.get('pinyin', '')
        translation = word.get('translation', '')
        meaning = word.get('meaning', '')
        exemplary_image = word.get('exemplary_image', '')
        pronunciation = word.get('pronunciation', '')
        
        # Fix pronunciation URL if needed
        if '212.227.211.88' in pronunciation:
            pronunciation = self._get_pronunciation_url(character)
        
        # Use anki_usage_examples or real_usage_examples
        anki_examples = word.get('anki_usage_examples', '') or word.get('real_usage_examples', '')
        
        stroke_gifs = word.get('stroke_gifs', '').split(', ') if word.get('stroke_gifs') else []
        
        html = f'''<div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
    <!-- Front of card -->
    <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="font-size: 48px; margin: 0; text-align: center;">{character}</h2>
        <div style="text-align: center; margin-top: 10px;">
            <button onclick="document.getElementById('preview-audio').play()" 
                style="padding: 10px 20px; font-size: 18px; cursor: pointer;">🔊 Play Audio</button>
            <audio id="preview-audio" src="{pronunciation}" preload="auto"></audio>
        </div>
    </div>
    
    <!-- Back of card -->
    <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #ddd;">
        <div style="font-size: 24px; color: #666; margin-bottom: 10px;">{pinyin}</div>
        <div style="font-size: 18px; margin-bottom: 15px;"><strong>{translation}</strong></div>
        
        {f'<div style="margin: 15px 0;"><img src="{exemplary_image}" style="max-width: 100%; border-radius: 8px;"></div>' if exemplary_image else ''}
        
        <div style="margin-top: 20px;">
            <h4>Example Usage:</h4>
            <div style="background: #f9f9f9; padding: 15px; border-radius: 4px;">
                {anki_examples}
            </div>
        </div>
        
        {f'<div style="margin-top: 15px;"><h4>Stroke Order:</h4><div style="display: flex; gap: 10px; flex-wrap: wrap;">' + ''.join([f'<img src="{gif}" style="width: 100px; height: 100px; border: 1px solid #ddd;">' for gif in stroke_gifs if gif]) + '</div></div>' if stroke_gifs else ''}
    </div>
</div>'''
        return html
    
    def get_tts_audio(self, text: str) -> Optional[bytes]:
        """Get TTS audio bytes."""
        return self._get_cached_tts(text)
    
    def _get_cached_tts(self, text: str) -> Optional[bytes]:
        """Get cached TTS audio."""
        # Check R2 first
        if r2_storage.is_available():
            audio = r2_storage.get_tts(text)
            if audio:
                return audio
        
        # Check local cache
        try:
            import sqlite3
            conn = sqlite3.connect('local.db')
            c = conn.cursor()
            c.execute('SELECT audio FROM tts_cache WHERE hanzi = ?', (text,))
            row = c.fetchone()
            conn.close()
            return row[0] if row else None
        except:
            return None
    
    def _cache_tts(self, text: str, audio_data: bytes):
        """Cache TTS audio."""
        # Store in R2 if available
        if r2_storage.is_available():
            r2_storage.store_tts(text, audio_data)
        
        # Also cache locally
        try:
            import sqlite3
            conn = sqlite3.connect('local.db')
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS tts_cache (
                hanzi TEXT PRIMARY KEY,
                audio BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('INSERT OR REPLACE INTO tts_cache (hanzi, audio) VALUES (?, ?)',
                     (text, audio_data))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error caching TTS: {e}")


# Global instance
dictionary_service = DictionaryService()
