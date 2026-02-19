#!/usr/bin/env python3
"""Verify Supabase connection and data."""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_publishable_7Mp1_7oM9Nr-xmj-Ld1kTA_cM26jDlA')

def verify():
    """Verify Supabase setup."""
    from supabase import create_client
    
    print("=" * 70)
    print("SUPABASE VERIFICATION")
    print("=" * 70)
    
    print(f"\nURL: {SUPABASE_URL}")
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✓ Connected with anon key")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    # Check tables
    tables = ['users', 'words', 'example_sentences', 'pending_approvals', 
              'verification_tokens', 'tts_cache', 'stroke_gifs']
    
    print("\nChecking tables:")
    all_good = True
    for table in tables:
        try:
            result = supabase.table(table).select('count', count='exact').execute()
            count = result.count
            print(f"  ✓ {table}: {count} rows")
        except Exception as e:
            print(f"  ✗ {table}: NOT FOUND")
            all_good = False
    
    if all_good:
        print("\n" + "=" * 70)
        print("✅ ALL CHECKS PASSED!")
        print("=" * 70)
        print("\nSupabase is ready to use!")
        return True
    else:
        print("\n" + "=" * 70)
        print("⚠ SOME TABLES MISSING")
        print("=" * 70)
        print("\nPlease run the SQL in SUPABASE_SETUP.sql first")
        return False

if __name__ == '__main__':
    verify()
