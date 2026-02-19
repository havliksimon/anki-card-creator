#!/usr/bin/env python3
"""Export all data from SQLite databases to JSON for migration."""
import os
import json
import sqlite3
from datetime import datetime

# Paths to old databases
OLD_APP_DIR = "/home/simon/py/nmy/anki_card_creator (Copy)/app"
OLD_API_DIR = "/home/simon/py/nmy/anki_card_creator (Copy)/server_api_app"
EXPORT_DIR = "migration_data"


def export_users_and_words():
    """Export users and words."""
    print("\n=== Exporting Users and Words ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "chinese_words.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get unique users
    c.execute("SELECT DISTINCT user_id FROM words")
    user_ids = [row[0] for row in c.fetchall()]
    
    users = []
    for user_id in user_ids:
        is_admin = user_id == '5624590693'  # Original admin ID
        users.append({
            'id': user_id,
            'email': None,
            'telegram_id': user_id if user_id.isdigit() else None,
            'telegram_username': None,
            'password_hash': None,
            'is_active': True,
            'is_admin': is_admin,
            'created_at': datetime.utcnow().isoformat(),
            'last_login': None
        })
    
    # Save users
    with open(f"{EXPORT_DIR}/users.json", 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(users)} users to users.json")
    
    # Get all words
    c.execute("SELECT * FROM words")
    words = []
    for row in c.fetchall():
        word = dict(row)
        words.append({
            'character': word['character'],
            'user_id': word['user_id'],
            'pinyin': word.get('pinyin'),
            'translation': word.get('translation'),
            'meaning': word.get('meaning'),
            'stroke_gifs': word.get('stroke_gifs'),
            'pronunciation': word.get('pronunciation'),
            'exemplary_image': word.get('exemplary_image'),
            'anki_usage_examples': word.get('anki_usage_examples'),
            'real_usage_examples': word.get('real_usage_examples'),
            'styled_term': word.get('styled_term'),
            'created_at': datetime.utcnow().isoformat()
        })
    
    # Save words
    with open(f"{EXPORT_DIR}/words.json", 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(words)} words to words.json")
    
    conn.close()


def export_example_sentences():
    """Export example sentences."""
    print("\n=== Exporting Example Sentences ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "example_sentences.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM example_sentences")
    sentences = [dict(row) for row in c.fetchall()]
    
    with open(f"{EXPORT_DIR}/example_sentences.json", 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)
    
    print(f"Exported {len(sentences)} example sentences to example_sentences.json")
    conn.close()


def export_tts_cache():
    """Export TTS cache metadata (not the binary data to keep size manageable)."""
    print("\n=== Exporting TTS Cache Metadata ===")
    
    conn = sqlite3.connect(os.path.join(OLD_API_DIR, "cache.db"))
    c = conn.cursor()
    
    c.execute("SELECT hanzi FROM cache")
    tts_entries = [{'hanzi': row[0]} for row in c.fetchall()]
    
    with open(f"{EXPORT_DIR}/tts_cache_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(tts_entries, f, ensure_ascii=False, indent=2)
    
    print(f"Exported {len(tts_entries)} TTS cache entries to tts_cache_metadata.json")
    conn.close()


def export_stroke_gifs_metadata():
    """Export stroke GIFs metadata."""
    print("\n=== Exporting Stroke GIFs Metadata ===")
    
    conn = sqlite3.connect(os.path.join(OLD_API_DIR, "cache.db"))
    c = conn.cursor()
    
    c.execute("SELECT character, stroke_order FROM stroke_gifs")
    gifs = [{'character': row[0], 'stroke_order': row[1]} for row in c.fetchall()]
    
    with open(f"{EXPORT_DIR}/stroke_gifs_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(gifs, f, ensure_ascii=False, indent=2)
    
    print(f"Exported {len(gifs)} stroke GIF entries to stroke_gifs_metadata.json")
    conn.close()


def main():
    """Main export function."""
    print("=" * 60)
    print("Data Export Tool")
    print("=" * 60)
    
    # Create export directory
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # Run exports
    export_users_and_words()
    export_example_sentences()
    export_tts_cache()
    export_stroke_gifs_metadata()
    
    print("\n" + "=" * 60)
    print(f"Export complete! Files saved to ./{EXPORT_DIR}/")
    print("=" * 60)
    
    # List files
    for f in os.listdir(EXPORT_DIR):
        path = os.path.join(EXPORT_DIR, f)
        size = os.path.getsize(path)
        print(f"  {f}: {size:,} bytes")


if __name__ == "__main__":
    main()
