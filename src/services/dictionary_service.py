"""Dictionary service for word details - uses scraping exactly like old app."""
import os
import re
import json
import requests
import threading
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO
from urllib.parse import quote
from gtts import gTTS

from src.models.database import db
from src.utils.chinese_utils import chinese_to_styled_pinyin
from src.services.r2_storage import r2_storage
from src.services.scraping_service import scraping_service


class DictionaryService:
    """Service for Chinese dictionary operations - uses scraping like old app."""
    
    def __init__(self):
        self.app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
        self.tts_api_url = f"{self.app_url}/api/tts"
    
    def get_word_details(self, character: str, progress_callback=None) -> Dict[str, Any]:
        """Get full word details using web scraping (exactly like old app).
        
        Args:
            character: Chinese character to look up
            progress_callback: Optional callback function(stage, message) for progress updates
        """
        # Use the scraping service exactly like the old app
        scraped_data = scraping_service.scrape_word_details(character, progress_callback)
        
        # Unpack the returned tuple (same order as old app)
        pinyin, translation, stroke_gifs, pronunciation, example_link, \
        exemplary_image, meaning, reading, component1, component2, \
        styled_term, usage_examples, real_usage_examples = scraped_data
        
        # If styled_term is empty, generate it
        if not styled_term:
            _, styled_term = chinese_to_styled_pinyin(character)
        
        # If pinyin is empty, generate it
        if not pinyin:
            pinyin, _ = chinese_to_styled_pinyin(character)
        
        return {
            'character': character,
            'pinyin': pinyin,
            'styled_term': styled_term,
            'translation': translation or self._get_translation(character),
            'meaning': meaning,
            'stroke_gifs': stroke_gifs,
            'pronunciation': pronunciation or self._get_pronunciation_url(character),
            'exemplary_image': exemplary_image,
            'anki_usage_examples': real_usage_examples,  # Use real examples as anki examples
            'real_usage_examples': real_usage_examples,
            'usage_examples': usage_examples,
            'reading': reading,
            'component1': component1,
            'component2': component2,
            'example_link': example_link
        }
    
    def _get_pronunciation_url(self, text: str) -> str:
        """Get pronunciation audio URL."""
        return f"{self.tts_api_url}?hanzi={quote(text)}"
    
    def _get_translation(self, character: str) -> str:
        """Get English translation for character."""
        return "Translation not available"
    
    def generate_csv(self, user_id: str, deck_id: str = None) -> bytes:
        """Generate CSV export for user's words - matches old app format EXACTLY."""
        import csv
        import io
        
        words = db.get_words_by_user(user_id, deck_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # NO HEADER - matches old app exactly
        # (Old app commented out the header line)
        
        # Process each word exactly like the old app
        for word in words:
            character = word.get('character', '')
            styled_term = word.get('styled_term', '')
            pinyin = word.get('pinyin', '')
            translation = word.get('translation', '')
            meaning = word.get('meaning', '')
            
            # Ensure pronunciation uses correct API URL
            pronunciation = word.get('pronunciation', '')
            if not pronunciation or '212.227.211.88' in pronunciation:
                pronunciation = self._get_pronunciation_url(character)
            
            example_link = word.get('example_link', '')
            exemplary_image = word.get('exemplary_image', '')
            
            # Use real_usage_examples as example_usage (same as old app)
            example_usage = word.get('real_usage_examples', '') or word.get('anki_usage_examples', '')
            
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
            
            # Get APP_URL for stroke order GIF URLs
            app_url = os.environ.get('APP_URL', 'https://cardcreator.havliksimon.eu')
            
            # Full URLs for stroke order GIFs
            full_stroke_urls = []
            for url in stroke_order_fields:
                if url and 'dictionary.writtenchinese.com' in url:
                    # Convert relative URL to full URL
                    full_url = url.replace('https://dictionary.writtenchinese.com', app_url)
                    full_stroke_urls.append(full_url)
                else:
                    full_stroke_urls.append(url)
            
            # CSV row format with APP_URL field before StrokeOrder fields
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
            ] + full_stroke_urls
            
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
        if not pronunciation or '212.227.211.88' in pronunciation:
            pronunciation = self._get_pronunciation_url(character)
        
        # Use real_usage_examples for display
        anki_examples = word.get('real_usage_examples', '') or word.get('anki_usage_examples', '')
        
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
