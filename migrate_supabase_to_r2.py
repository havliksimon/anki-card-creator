#!/usr/bin/env python3
"""Migrate TTS and stroke GIFs from Supabase to Cloudflare R2."""
import os
import sys
import base64
import httpx
from tqdm import tqdm

# Load environment
supabase_url = os.environ.get('SUPABASE_URL', '')
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

# Import R2 storage
from src.services.r2_storage import R2Storage

r2 = R2Storage()

if not r2.is_available():
    print("Error: R2 storage not configured properly")
    print("Make sure R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY are set")
    sys.exit(1)

# Create Supabase client
supabase_client = httpx.Client(
    base_url=f"{supabase_url}/rest/v1",
    headers={
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    },
    timeout=60.0
)


def migrate_tts_cache():
    """Migrate TTS cache from Supabase to R2."""
    print("\n=== Migrating TTS Cache ===")
    
    # Get all TTS entries
    try:
        response = supabase_client.get("/tts_cache?select=hanzi,audio")
        items = response.json()
        print(f"Found {len(items)} TTS entries in Supabase")
    except Exception as e:
        print(f"Error fetching TTS from Supabase: {e}")
        return 0, 0
    
    migrated = 0
    failed = 0
    
    for item in tqdm(items, desc="Migrating TTS"):
        try:
            hanzi = item['hanzi']
            audio_data = base64.b64decode(item['audio'])
            
            # Store in R2
            if r2.store_tts(hanzi, audio_data):
                migrated += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\nError migrating TTS {hanzi}: {e}")
            failed += 1
    
    print(f"\nTTS Migration: {migrated} migrated, {failed} failed")
    return migrated, failed


def migrate_stroke_gifs():
    """Migrate stroke GIFs from Supabase to R2."""
    print("\n=== Migrating Stroke GIFs ===")
    
    # Get all stroke GIF entries
    try:
        response = supabase_client.get("/stroke_gifs?select=character,stroke_order,gif_data")
        items = response.json()
        print(f"Found {len(items)} stroke GIF entries in Supabase")
    except Exception as e:
        print(f"Error fetching stroke GIFs from Supabase: {e}")
        return 0, 0
    
    migrated = 0
    failed = 0
    
    for item in tqdm(items, desc="Migrating Stroke GIFs"):
        try:
            character = item['character']
            order = item['stroke_order']
            gif_data = base64.b64decode(item['gif_data'])
            
            # Store in R2
            if r2.store_stroke_gif(character, order, gif_data):
                migrated += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\nError migrating stroke GIF {character}_{order}: {e}")
            failed += 1
    
    print(f"\nStroke GIF Migration: {migrated} migrated, {failed} failed")
    return migrated, failed


def main():
    print("=== Supabase to R2 Migration ===")
    print(f"Supabase: {supabase_url}")
    print(f"R2 Bucket: {r2.bucket_name}")
    print(f"R2 Public URL: {r2.public_url}")
    
    confirm = input("\nProceed with migration? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Migration cancelled")
        return
    
    # Migrate TTS
    tts_migrated, tts_failed = migrate_tts_cache()
    
    # Migrate stroke GIFs
    stroke_migrated, stroke_failed = migrate_stroke_gifs()
    
    print("\n" + "="*50)
    print("Migration Summary:")
    print(f"  TTS: {tts_migrated} migrated, {tts_failed} failed")
    print(f"  Stroke GIFs: {stroke_migrated} migrated, {stroke_failed} failed")
    print("="*50)


if __name__ == '__main__':
    main()
