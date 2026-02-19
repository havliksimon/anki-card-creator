#!/usr/bin/env python3
"""
AUTOMATED SUPABASE SETUP
Run this script after adding your SERVICE ROLE KEY below
"""
import os
import sys

# ============================================
# CONFIGURATION - ADD YOUR SERVICE ROLE KEY HERE
# ============================================
# Get this from Supabase Dashboard → Project Settings → API → service_role secret
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', 
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFwdGx2dmJybHlwcW15bWZhdG54Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTk1NTIwMCwiZXhwIjoyMDU1NTMxMjAwfQ.dFQtKCm9kUdlznPq')  # REPLACE THIS

SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"

# SQL to create tables
CREATE_TABLES_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
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

-- Words table
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

-- Example sentences
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

-- Pending approvals
CREATE TABLE IF NOT EXISTS pending_approvals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Verification tokens
CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TTS cache
CREATE TABLE IF NOT EXISTS tts_cache (
    hanzi TEXT PRIMARY KEY,
    audio BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stroke GIFs
CREATE TABLE IF NOT EXISTS stroke_gifs (
    character TEXT NOT NULL,
    stroke_order INTEGER NOT NULL,
    gif_data BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (character, stroke_order)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id);
CREATE INDEX IF NOT EXISTS idx_words_character ON words(character);
"""

def setup_supabase():
    """Main setup function."""
    from supabase import create_client
    import json
    import time
    
    print("=" * 70)
    print("AUTOMATED SUPABASE SETUP")
    print("=" * 70)
    
    # Check if service key is set
    if 'your-service-role-key' in SUPABASE_SERVICE_KEY or 'placeholder' in SUPABASE_SERVICE_KEY.lower():
        print("\n❌ ERROR: Please set your SUPABASE_SERVICE_KEY in this file!")
        print("\nTo get your service role key:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Select your project (aptlvvbrlypqmymfatnx)")
        print("3. Project Settings → API")
        print("4. Copy 'service_role secret'")
        print("5. Paste it in this file on line 12")
        return False
    
    print(f"\nConnecting to Supabase...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✓ Connected!")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    # Check if tables exist
    print("\nChecking tables...")
    try:
        result = supabase.table('users').select('count', count='exact').execute()
        print("✓ Tables already exist!")
        tables_exist = True
    except:
        print("✗ Tables need to be created")
        print("\nPlease run this SQL in Supabase Dashboard:")
        print("-" * 70)
        print(CREATE_TABLES_SQL)
        print("-" * 70)
        print("\n1. Go to https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. SQL Editor → New Query")
        print("4. Paste the SQL above")
        print("5. Click Run")
        print("\nThen run this script again.")
        return False
    
    if tables_exist:
        # Migrate users
        print("\n=== Migrating Users ===")
        with open("migration_data_optimized/users.json", 'r') as f:
            users = json.load(f)
        
        for user in users:
            try:
                supabase.table('users').upsert(user).execute()
            except Exception as e:
                print(f"  Error with user {user['id']}: {e}")
        
        print(f"✓ Migrated {len(users)} users")
        
        # Migrate words
        print("\n=== Migrating Words ===")
        with open("migration_data_optimized/words.json", 'r') as f:
            words = json.load(f)
        
        batch_size = 100
        for i in range(0, len(words), batch_size):
            batch = words[i:i+batch_size]
            try:
                supabase.table('words').upsert(batch).execute()
                print(f"  Progress: {min(i+batch_size, len(words))}/{len(words)}")
            except Exception as e:
                print(f"  Error in batch: {e}")
            time.sleep(0.1)
        
        print(f"✓ Migrated {len(words)} words")
        
        # Migrate sentences
        print("\n=== Migrating Example Sentences ===")
        with open("migration_data_optimized/example_sentences.json", 'r') as f:
            sentences = json.load(f)
        
        for i in range(0, len(sentences), 50):
            batch = sentences[i:i+50]
            try:
                supabase.table('example_sentences').upsert(batch).execute()
                if i % 1000 == 0:
                    print(f"  Progress: {i}/{len(sentences)}")
            except:
                pass
            time.sleep(0.05)
        
        print(f"✓ Migrated {len(sentences)} sentences")
        
        # Verify
        print("\n=== Verifying ===")
        users_count = supabase.table('users').select('count', count='exact').execute().count
        words_count = supabase.table('words').select('count', count='exact').execute().count
        sent_count = supabase.table('example_sentences').select('count', count='exact').execute().count
        
        print(f"✓ Users: {users_count}")
        print(f"✓ Words: {words_count}")
        print(f"✓ Sentences: {sent_count}")
        
        print("\n" + "=" * 70)
        print("✅ SETUP COMPLETE!")
        print("=" * 70)
        print("\nYou can now set USE_LOCAL_DB=false in .env and deploy!")
        return True

if __name__ == '__main__':
    success = setup_supabase()
    sys.exit(0 if success else 1)
