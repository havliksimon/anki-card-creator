#!/usr/bin/env python3
"""Complete Supabase setup with service key."""
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

# SQL for creating tables
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    telegram_id TEXT UNIQUE,
    telegram_username TEXT,
    password_hash TEXT,
    is_active BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS words (
    id SERIAL PRIMARY KEY,
    character TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pinyin TEXT,
    translation TEXT,
    meaning TEXT,
    stroke_gifs TEXT,
    pronunciation TEXT,
    exemplary_image TEXT,
    anki_usage_examples TEXT,
    real_usage_examples TEXT,
    styled_term TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(character, user_id)
);

CREATE TABLE IF NOT EXISTS example_sentences (
    id SERIAL PRIMARY KEY,
    chinese_sentence TEXT UNIQUE,
    styled_pinyin TEXT,
    styled_hanzi TEXT,
    translation TEXT,
    source_name TEXT,
    source_link TEXT,
    word_list TEXT
);

CREATE TABLE IF NOT EXISTS pending_approvals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tts_cache (
    hanzi TEXT PRIMARY KEY,
    audio BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stroke_gifs (
    character TEXT NOT NULL,
    stroke_order INTEGER NOT NULL,
    gif_data BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (character, stroke_order)
);

CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id);
CREATE INDEX IF NOT EXISTS idx_words_character ON words(character);
"""

def setup():
    """Main setup function."""
    from supabase import create_client
    
    print("=" * 70)
    print("SUPABASE FULL SETUP")
    print("=" * 70)
    
    if not SUPABASE_SERVICE_KEY:
        print("\n❌ No service key found!")
        return False
    
    print("\nConnecting to Supabase...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✓ Connected!")
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    
    # Try to create tables via REST API
    print("\n=== Checking/Creating Tables ===")
    tables = ['users', 'words', 'example_sentences', 'pending_approvals', 
              'verification_tokens', 'tts_cache', 'stroke_gifs']
    
    existing = []
    missing = []
    
    for table in tables:
        try:
            result = supabase.table(table).select('count', count='exact').limit(1).execute()
            existing.append(table)
            print(f"  ✓ {table}: exists ({result.count} rows)")
        except:
            missing.append(table)
            print(f"  ✗ {table}: missing")
    
    if missing:
        print(f"\n⚠ {len(missing)} tables need to be created")
        print("\nPlease run this SQL in Supabase Dashboard SQL Editor:")
        print("-" * 70)
        print(CREATE_TABLES_SQL)
        print("-" * 70)
        print("\nThen run this script again.")
        return False
    
    # Migrate users
    print("\n=== Migrating Users ===")
    with open("migration_data_optimized/users.json", 'r') as f:
        users = json.load(f)
    
    for user in users:
        try:
            supabase.table('users').upsert(user).execute()
        except Exception as e:
            print(f"  Warning for user {user['id']}: {e}")
    
    print(f"✓ Migrated {len(users)} users")
    
    # Migrate words
    print("\n=== Migrating Words ===")
    with open("migration_data_optimized/words.json", 'r') as f:
        words = json.load(f)
    
    total = len(words)
    for i in range(0, total, 100):
        batch = words[i:i+100]
        try:
            supabase.table('words').upsert(batch).execute()
            print(f"  Progress: {min(i+100, total)}/{total}")
        except Exception as e:
            print(f"  Error in batch {i}: {e}")
        time.sleep(0.1)
    
    print(f"✓ Migrated {total} words")
    
    # Migrate sentences
    print("\n=== Migrating Example Sentences ===")
    with open("migration_data_optimized/example_sentences.json", 'r') as f:
        sentences = json.load(f)
    
    total = len(sentences)
    for i in range(0, total, 50):
        batch = sentences[i:i+50]
        try:
            supabase.table('example_sentences').upsert(batch).execute()
            if i % 1000 == 0:
                print(f"  Progress: {i}/{total}")
        except:
            pass
        time.sleep(0.05)
    
    print(f"✓ Migrated {total} sentences")
    
    # Final verification
    print("\n=== Final Verification ===")
    u = supabase.table('users').select('count', count='exact').execute().count
    w = supabase.table('words').select('count', count='exact').execute().count
    s = supabase.table('example_sentences').select('count', count='exact').execute().count
    
    print(f"✓ Users: {u}")
    print(f"✓ Words: {w}")
    print(f"✓ Sentences: {s}")
    
    print("\n" + "=" * 70)
    print("✅ SUPABASE SETUP COMPLETE!")
    print("=" * 70)
    print("\nAll data is now in Supabase!")
    print("\nTo use Supabase mode:")
    print("1. Edit .env: set USE_LOCAL_DB=false")
    print("2. Run: ./run_production.sh")
    print("\nOr deploy to Koyeb with the env vars from .env")
    
    return True

if __name__ == '__main__':
    import sys
    success = setup()
    sys.exit(0 if success else 1)
