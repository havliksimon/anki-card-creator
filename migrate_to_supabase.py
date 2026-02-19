#!/usr/bin/env python3
"""
Migrate all data to Supabase.
Run this AFTER creating tables in Supabase Dashboard.
"""
import os
import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

def migrate():
    """Main migration function."""
    from supabase import create_client
    
    print("=" * 70)
    print("MIGRATING DATA TO SUPABASE")
    print("=" * 70)
    
    # Check service key
    if not SUPABASE_SERVICE_KEY or 'placeholder' in SUPABASE_SERVICE_KEY.lower():
        print("\n❌ ERROR: SUPABASE_SERVICE_KEY not set!")
        print("\nPlease add it to your .env file:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. Project Settings → API")
        print("3. Copy 'service_role secret'")
        print("4. Add to .env: SUPABASE_SERVICE_KEY=your-key-here")
        return False
    
    # Connect
    print("\nConnecting to Supabase...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✓ Connected!")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    # Check tables exist
    print("\nChecking tables...")
    try:
        result = supabase.table('users').select('count', count='exact').limit(1).execute()
        print("✓ Tables exist")
    except Exception as e:
        print(f"✗ Tables not found: {e}")
        print("\nPlease create tables first:")
        print("1. Go to https://supabase.com/dashboard")
        print("2. SQL Editor → New Query")
        print("3. Run the SQL from SUPABASE_SETUP.sql")
        return False
    
    # Migrate users
    print("\n=== Migrating Users ===")
    with open("migration_data_optimized/users.json", 'r') as f:
        users = json.load(f)
    
    for user in users:
        try:
            supabase.table('users').upsert(user).execute()
        except Exception as e:
            print(f"  Warning: {e}")
    print(f"✓ Migrated {len(users)} users")
    
    # Migrate words
    print("\n=== Migrating Words (this may take a minute) ===")
    with open("migration_data_optimized/words.json", 'r') as f:
        words = json.load(f)
    
    total = len(words)
    for i in range(0, total, 100):
        batch = words[i:i+100]
        try:
            supabase.table('words').upsert(batch).execute()
            print(f"  Progress: {min(i+100, total)}/{total}")
        except Exception as e:
            print(f"  Error: {e}")
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
    
    # Verify
    print("\n=== Verification ===")
    u = supabase.table('users').select('count', count='exact').execute().count
    w = supabase.table('words').select('count', count='exact').execute().count
    s = supabase.table('example_sentences').select('count', count='exact').execute().count
    
    print(f"✓ Users: {u}")
    print(f"✓ Words: {w}")
    print(f"✓ Sentences: {s}")
    
    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
    print("\nYou can now:")
    print("1. Set USE_LOCAL_DB=false in .env")
    print("2. Run: ./run_production.sh")
    print("3. Or deploy to Koyeb!")
    
    return True

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
