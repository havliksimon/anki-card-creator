#!/usr/bin/env python3
"""Migration script to export data from SQLite and import to Supabase."""
import os
import sys
import sqlite3
import json
from datetime import datetime
from supabase import create_client

# Supabase credentials from user
SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFwdGx2dmJybHlwcW15bWZhdG54Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTk1NTIwMCwiZXhwIjoyMDU1NTMxMjAwfQ.dFQtKCm9kUdlznPq"  # This is a placeholder - will get from user

# Paths to old databases
OLD_APP_DIR = "/home/simon/py/nmy/anki_card_creator (Copy)/app"
OLD_API_DIR = "/home/simon/py/nmy/anki_card_creator (Copy)/server_api_app"


def get_supabase():
    """Create Supabase client."""
    # Use the service role key for admin operations
    # Note: User provided publishable key, but we need service role key
    # For now, we'll create a placeholder and user can provide service key
    service_key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not service_key:
        print("ERROR: Please set SUPABASE_SERVICE_KEY environment variable")
        print("You can find it in Supabase Dashboard -> Project Settings -> API -> service_role secret")
        sys.exit(1)
    return create_client(SUPABASE_URL, service_key)


def migrate_users_and_words(supabase):
    """Migrate users and words from chinese_words.db."""
    print("\n=== Migrating Users and Words ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "chinese_words.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all unique users
    c.execute("SELECT DISTINCT user_id FROM words")
    user_ids = [row[0] for row in c.fetchall()]
    print(f"Found {len(user_ids)} unique users")
    
    # Get all words
    c.execute("SELECT * FROM words")
    words = [dict(row) for row in c.fetchall()]
    print(f"Found {len(words)} words")
    
    # Create users in Supabase
    created_users = 0
    for user_id in user_ids:
        # Check if user already exists
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        if result.data:
            print(f"  User {user_id} already exists, skipping...")
            continue
        
        # Create user
        user_data = {
            'id': user_id,
            'email': None,
            'telegram_id': user_id if user_id.isdigit() else None,
            'telegram_username': None,
            'password_hash': None,
            'is_active': True,  # Existing users are already approved
            'is_admin': user_id == '5624590693',  # Original admin ID from old code
            'created_at': datetime.utcnow().isoformat(),
            'last_login': None
        }
        
        try:
            supabase.table('users').insert(user_data).execute()
            created_users += 1
        except Exception as e:
            print(f"  Error creating user {user_id}: {e}")
    
    print(f"Created {created_users} new users")
    
    # Migrate words
    migrated_words = 0
    batch_size = 100
    
    for i in range(0, len(words), batch_size):
        batch = words[i:i+batch_size]
        
        # Transform to match new schema
        word_records = []
        for word in batch:
            record = {
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
            }
            word_records.append(record)
        
        try:
            supabase.table('words').insert(word_records).execute()
            migrated_words += len(word_records)
            print(f"  Migrated {migrated_words}/{len(words)} words...")
        except Exception as e:
            print(f"  Error migrating batch: {e}")
            # Try inserting one by one to identify problematic records
            for record in word_records:
                try:
                    supabase.table('words').insert(record).execute()
                    migrated_words += 1
                except Exception as e2:
                    print(f"    Error with {record['character']}: {e2}")
    
    conn.close()
    print(f"Migrated {migrated_words} words total")


def migrate_example_sentences(supabase):
    """Migrate example sentences."""
    print("\n=== Migrating Example Sentences ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "example_sentences.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM example_sentences")
    sentences = [dict(row) for row in c.fetchall()]
    print(f"Found {len(sentences)} example sentences")
    
    migrated = 0
    batch_size = 100
    
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i+batch_size]
        
        records = []
        for sent in batch:
            record = {
                'chinese_sentence': sent['chinese_sentence'],
                'styled_pinyin': sent.get('styled_pinyin'),
                'styled_hanzi': sent.get('styled_hanzi'),
                'translation': sent.get('translation'),
                'source_name': sent.get('source_name'),
                'source_link': sent.get('source_link'),
                'word_list': sent.get('word_list')
            }
            records.append(record)
        
        try:
            supabase.table('example_sentences').insert(records).execute()
            migrated += len(records)
            print(f"  Migrated {migrated}/{len(sentences)} sentences...")
        except Exception as e:
            print(f"  Error migrating batch: {e}")
    
    conn.close()
    print(f"Migrated {migrated} example sentences total")


def migrate_tts_cache(supabase):
    """Migrate TTS cache (audio files)."""
    print("\n=== Migrating TTS Cache ===")
    
    conn = sqlite3.connect(os.path.join(OLD_API_DIR, "cache.db"))
    c = conn.cursor()
    
    c.execute("SELECT hanzi, audio FROM cache")
    
    migrated = 0
    batch = []
    
    for row in c.fetchall():
        hanzi, audio = row
        batch.append({
            'hanzi': hanzi,
            'audio': audio,
            'created_at': datetime.utcnow().isoformat()
        })
        
        if len(batch) >= 50:
            try:
                supabase.table('tts_cache').insert(batch).execute()
                migrated += len(batch)
                print(f"  Migrated {migrated} TTS entries...")
            except Exception as e:
                print(f"  Error migrating TTS batch: {e}")
            batch = []
    
    # Insert remaining
    if batch:
        try:
            supabase.table('tts_cache').insert(batch).execute()
            migrated += len(batch)
        except Exception as e:
            print(f"  Error migrating final TTS batch: {e}")
    
    conn.close()
    print(f"Migrated {migrated} TTS entries total")


def migrate_stroke_gifs(supabase):
    """Migrate stroke GIFs."""
    print("\n=== Migrating Stroke GIFs ===")
    
    conn = sqlite3.connect(os.path.join(OLD_API_DIR, "cache.db"))
    c = conn.cursor()
    
    c.execute("SELECT character, stroke_order, gif_data FROM stroke_gifs")
    
    migrated = 0
    batch = []
    
    for row in c.fetchall():
        char, order, gif_data = row
        batch.append({
            'character': char,
            'stroke_order': order,
            'gif_data': gif_data,
            'created_at': datetime.utcnow().isoformat()
        })
        
        if len(batch) >= 50:
            try:
                supabase.table('stroke_gifs').insert(batch).execute()
                migrated += len(batch)
                print(f"  Migrated {migrated} stroke GIFs...")
            except Exception as e:
                print(f"  Error migrating stroke GIF batch: {e}")
            batch = []
    
    # Insert remaining
    if batch:
        try:
            supabase.table('stroke_gifs').insert(batch).execute()
            migrated += len(batch)
        except Exception as e:
            print(f"  Error migrating final stroke GIF batch: {e}")
    
    conn.close()
    print(f"Migrated {migrated} stroke GIFs total")


def main():
    """Main migration function."""
    print("=" * 60)
    print("Anki Card Creator Database Migration Tool")
    print("=" * 60)
    
    # Check environment
    if 'SUPABASE_SERVICE_KEY' not in os.environ:
        print("\nPlease set the SUPABASE_SERVICE_KEY environment variable")
        print("You can find it in your Supabase Dashboard:")
        print("  Project Settings -> API -> service_role secret")
        print("\nExample:")
        print("  export SUPABASE_SERVICE_KEY='your-service-role-key'")
        sys.exit(1)
    
    # Connect to Supabase
    print("\nConnecting to Supabase...")
    try:
        supabase = get_supabase()
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
    
    # Run migrations
    try:
        migrate_users_and_words(supabase)
        migrate_example_sentences(supabase)
        migrate_tts_cache(supabase)
        migrate_stroke_gifs(supabase)
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\nMigration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
