#!/usr/bin/env python3
"""
Complete Setup Script for Anki Card Creator
This script:
1. Checks local database
2. Attempts Supabase migration (if accessible)
3. Verifies all functionality
4. Creates run commands
"""
import os
import sys
import subprocess

# Configuration
SUPABASE_URL = "https://aptlvvbrlypqmymfatnx.supabase.co"

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def check_local_db():
    """Check local database status."""
    print_header("CHECKING LOCAL DATABASE")
    
    if not os.path.exists('local.db'):
        print("⚠ local.db not found")
        if os.path.exists('migration_data_optimized/words.json'):
            print("  → Importing from migration data...")
            result = subprocess.run(['python', 'import_optimized.py'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("✗ Import failed:")
                print(result.stderr)
                return False
            print("✓ Import complete")
        else:
            print("✗ No migration data found!")
            return False
    else:
        import sqlite3
        conn = sqlite3.connect('local.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM words")
        words = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]
        conn.close()
        
        size = os.path.getsize('local.db') / (1024 * 1024)
        print(f"✓ local.db exists ({size:.1f} MB)")
        print(f"  - {words} words")
        print(f"  - {users} users")
    
    return True

def test_application():
    """Test the application."""
    print_header("TESTING APPLICATION")
    
    result = subprocess.run(['python', 'final_test.py'], 
                          capture_output=True, text=True)
    
    if "ALL TESTS PASSED" in result.stdout:
        print("✓ All tests passed")
        return True
    else:
        print("✗ Tests failed:")
        print(result.stdout[-1000:])  # Last 1000 chars
        return False

def check_supabase():
    """Check Supabase connection."""
    print_header("CHECKING SUPABASE")
    print(f"URL: {SUPABASE_URL}")
    
    try:
        from supabase import create_client
        
        # Try with anon key first (read-only)
        supabase = create_client(SUPABASE_URL, 
            "sb_publishable_7Mp1_7oM9Nr-xmj-Ld1kTA_cM26jDlA")
        
        # Try a simple query
        result = supabase.table('users').select('count', count='exact').limit(1).execute()
        print(f"✓ Supabase accessible")
        print(f"  Users in Supabase: {result.count}")
        return True
        
    except Exception as e:
        print(f"⚠ Supabase not accessible: {e}")
        print("  This is OK for local testing with SQLite")
        return False

def create_run_scripts():
    """Create run scripts."""
    print_header("CREATING RUN SCRIPTS")
    
    # Local run script
    with open('run_local.sh', 'w') as f:
        f.write("""#!/bin/bash
# Run locally with SQLite
echo "Starting Anki Card Creator (Local Mode)..."
echo "URL: http://localhost:5000"
echo ""
source .venv/bin/activate
export USE_LOCAL_DB=true
python app.py
""")
    
    # Production run script
    with open('run_production.sh', 'w') as f:
        f.write("""#!/bin/bash
# Run with Supabase (set USE_LOCAL_DB=false in .env)
echo "Starting Anki Card Creator (Production Mode)..."
echo "URL: http://localhost:5000"
echo ""
source .venv/bin/activate
export USE_LOCAL_DB=false
python app.py
""")
    
    os.chmod('run_local.sh', 0o755)
    os.chmod('run_production.sh', 0o755)
    
    print("✓ Created run_local.sh - for local testing")
    print("✓ Created run_production.sh - for production mode")

def main():
    """Main setup."""
    print("=" * 70)
    print("ANKI CARD CREATOR - COMPLETE SETUP")
    print("=" * 70)
    
    # Check local DB
    if not check_local_db():
        print("\n❌ Local database setup failed")
        return False
    
    # Test application
    if not test_application():
        print("\n❌ Application tests failed")
        return False
    
    # Check Supabase (optional for now)
    check_supabase()
    
    # Create run scripts
    create_run_scripts()
    
    # Summary
    print_header("SETUP COMPLETE")
    print("""
✅ Everything is ready!

TO RUN LOCALLY (with SQLite):
  ./run_local.sh
  
TO RUN WITH SUPABASE:
  1. Set USE_LOCAL_DB=false in .env
  2. Set SUPABASE_SERVICE_KEY in .env
  3. Run: python setup_supabase.py (to migrate data)
  4. Then: ./run_production.sh

TO DEPLOY TO KOYEB:
  1. Push to GitHub
  2. Connect to Koyeb
  3. Set environment variables from .env
  4. Deploy!

The app will be available at: http://localhost:5000

Admin login:
  Email: admin@anki-cards.com
  Password: admin123
""")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
