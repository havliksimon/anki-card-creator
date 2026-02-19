#!/usr/bin/env python3
"""Complete Supabase setup and data migration."""
import os
import sys
import json
import time
from datetime import datetime, timezone

# Supabase credentials from .env
SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"
SUPABASE_KEY = "sb_publishable_7Mp1_7oM9Nr-xmj-Ld1kTA_cM26jDlA"

# Try to get service key from environment or use placeholder
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFwdGx2dmJybHlwcW15bWZhdG54Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTk1NTIwMCwiZXhwIjoyMDU1NTMxMjAwfQ.dFQtKCm9kUdlznPq")

def get_supabase():
    """Create Supabase client with service key."""
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def create_tables(supabase):
    """Create all tables using Supabase REST API."""
    print("\n=== Creating Tables ===")
    
    # We'll use raw SQL via the REST API
    # First, let's try to check if tables exist by querying them
    tables = ['users', 'words', 'example_sentences', 'pending_approvals', 
              'verification_tokens', 'tts_cache', 'stroke_gifs']
    
    existing = []
    for table in tables:
        try:
            result = supabase.table(table).select('count', count='exact').limit(1).execute()
            existing.append(table)
            print(f"  ✓ Table exists: {table}")
        except Exception as e:
            print(f"  ✗ Table missing: {table}")
    
    if len(existing) == len(tables):
        print("\n  All tables already exist!")
        return True
    else:
        print("\n  ⚠ Some tables are missing. Please run the SQL in supabase_migration_optimized.sql")
        print("  in your Supabase Dashboard SQL Editor first.")
        return False

def migrate_users(supabase):
    """Migrate users."""
    print("\n=== Migrating Users ===")
    
    with open("migration_data_optimized/users.json", 'r') as f:
        users = json.load(f)
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            # Check if user exists
            existing = supabase.table('users').select('id').eq('id', user['id']).execute()
            
            if existing.data:
                # Update
                supabase.table('users').update(user).eq('id', user['id']).execute()
            else:
                # Insert
                supabase.table('users').insert(user).execute()
            success += 1
        except Exception as e:
            failed += 1
            print(f"  Error with user {user['id']}: {e}")
    
    print(f"  ✓ Migrated {success} users ({failed} failed)")
    return success > 0

def migrate_words(supabase):
    """Migrate words in batches."""
    print("\n=== Migrating Words ===")
    
    with open("migration_data_optimized/words.json", 'r') as f:
        words = json.load(f)
    
    batch_size = 100
    total = len(words)
    migrated = 0
    failed = 0
    
    for i in range(0, total, batch_size):
        batch = words[i:i+batch_size]
        try:
            supabase.table('words').upsert(batch).execute()
            migrated += len(batch)
            print(f"  Progress: {migrated}/{total}")
        except Exception as e:
            print(f"  Error in batch {i}: {e}")
            failed += len(batch)
        
        time.sleep(0.1)  # Rate limiting
    
    print(f"  ✓ Migrated {migrated} words ({failed} failed)")
    return migrated > 0

def migrate_sentences(supabase):
    """Migrate example sentences in batches."""
    print("\n=== Migrating Example Sentences ===")
    
    with open("migration_data_optimized/example_sentences.json", 'r') as f:
        sentences = json.load(f)
    
    batch_size = 50
    total = len(sentences)
    migrated = 0
    
    for i in range(0, total, batch_size):
        batch = sentences[i:i+batch_size]
        try:
            supabase.table('example_sentences').upsert(batch).execute()
            migrated += len(batch)
            if i % 1000 == 0:
                print(f"  Progress: {migrated}/{total}")
        except Exception as e:
            print(f"  Error in batch {i}: {e}")
        
        time.sleep(0.05)
    
    print(f"  ✓ Migrated {migrated} sentences")
    return migrated > 0

def verify_migration(supabase):
    """Verify data was migrated correctly."""
    print("\n=== Verifying Migration ===")
    
    try:
        users = supabase.table('users').select('*', count='exact').execute()
        words = supabase.table('words').select('*', count='exact').execute()
        sentences = supabase.table('example_sentences').select('*', count='exact').execute()
        
        print(f"  ✓ Users: {users.count}")
        print(f"  ✓ Words: {words.count}")
        print(f"  ✓ Example Sentences: {sentences.count}")
        
        return users.count > 0 and words.count > 0
    except Exception as e:
        print(f"  ✗ Verification failed: {e}")
        return False

def main():
    """Main setup function."""
    print("=" * 70)
    print("SUPABASE SETUP & MIGRATION")
    print("=" * 70)
    print(f"\nSupabase URL: {SUPABASE_URL}")
    
    try:
        supabase = get_supabase()
        print("✓ Connected to Supabase")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure SUPABASE_SERVICE_KEY is set correctly.")
        return False
    
    # Create tables
    if not create_tables(supabase):
        print("\n⚠ Please create tables first using the SQL file.")
        return False
    
    # Migrate data
    migrate_users(supabase)
    migrate_words(supabase)
    migrate_sentences(supabase)
    
    # Verify
    if verify_migration(supabase):
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print("⚠ MIGRATION INCOMPLETE - CHECK ERRORS ABOVE")
        print("=" * 70)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
