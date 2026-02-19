#!/usr/bin/env python3
"""Migrate TTS cache and stroke GIFs from local SQLite to Supabase."""
import os
import sys
import sqlite3
import base64
import httpx
from tqdm import tqdm
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
CACHE_DB_PATH = 'old_anki_card_creator/api_server/cache.db'

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    sys.exit(1)

if not os.path.exists(CACHE_DB_PATH):
    print(f"Error: Cache database not found at {CACHE_DB_PATH}")
    sys.exit(1)

# Create HTTP client
client = httpx.Client(
    base_url=f"{SUPABASE_URL}/rest/v1",
    headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # Upsert behavior
    },
    timeout=60.0
)


def get_cache_stats():
    """Get count of items to migrate."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cache")
    tts_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM stroke_gifs")
    stroke_count = cursor.fetchone()[0]
    
    conn.close()
    return tts_count, stroke_count


def migrate_tts_cache(batch_size=100):
    """Migrate TTS cache to Supabase."""
    print("\n=== Migrating TTS Cache ===")
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT hanzi, audio FROM cache")
    items = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(items)} TTS items to migrate")
    
    migrated = 0
    failed = 0
    
    for hanzi, audio in tqdm(items, desc="TTS Cache"):
        try:
            # Encode audio as base64
            encoded = base64.b64encode(audio).decode('utf-8')
            
            # Upload to Supabase
            response = client.post(
                "/tts_cache",
                json={"hanzi": hanzi, "audio": encoded}
            )
            
            if response.status_code in [200, 201, 204]:
                migrated += 1
            else:
                print(f"\nFailed to upload {hanzi}: {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"\nError uploading {hanzi}: {e}")
            failed += 1
    
    print(f"\nTTS Migration complete: {migrated} migrated, {failed} failed")
    return migrated, failed


def migrate_stroke_gifs(batch_size=100):
    """Migrate stroke GIFs to Supabase."""
    print("\n=== Migrating Stroke GIFs ===")
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT character, stroke_order, gif_data FROM stroke_gifs")
    items = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(items)} stroke GIFs to migrate")
    
    migrated = 0
    failed = 0
    
    for char, order, gif_data in tqdm(items, desc="Stroke GIFs"):
        try:
            # Encode GIF as base64
            encoded = base64.b64encode(gif_data).decode('utf-8')
            
            # Upload to Supabase
            response = client.post(
                "/stroke_gifs",
                json={
                    "character": char,
                    "stroke_order": order,
                    "gif_data": encoded
                }
            )
            
            if response.status_code in [201, 204]:
                migrated += 1
            else:
                print(f"\nFailed to upload {char}-{order}: {response.status_code}")
                failed += 1
                
        except Exception as e:
            print(f"\nError uploading {char}-{order}: {e}")
            failed += 1
    
    print(f"\nStroke GIFs Migration complete: {migrated} migrated, {failed} failed")
    return migrated, failed


def main():
    print("=== Cache Migration to Supabase ===")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Cache DB: {CACHE_DB_PATH}")
    
    tts_count, stroke_count = get_cache_stats()
    print(f"\nItems to migrate:")
    print(f"  - TTS cache: {tts_count} items")
    print(f"  - Stroke GIFs: {stroke_count} items")
    
    confirm = input("\nProceed with migration? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Migration cancelled")
        return
    
    # Migrate TTS cache
    tts_migrated, tts_failed = migrate_tts_cache()
    
    # Migrate stroke GIFs
    stroke_migrated, stroke_failed = migrate_stroke_gifs()
    
    print("\n" + "="*50)
    print("Migration Summary:")
    print(f"  TTS Cache: {tts_migrated} migrated, {tts_failed} failed")
    print(f"  Stroke GIFs: {stroke_migrated} migrated, {stroke_failed} failed")
    print("="*50)


if __name__ == '__main__':
    main()
