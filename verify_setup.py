#!/usr/bin/env python3
"""Verify the Anki Card Creator setup."""
import os
import sys
import sqlite3

os.environ['USE_LOCAL_DB'] = 'true'

def check_files():
    """Check that all required files exist."""
    print("=== Checking Files ===")
    
    required_files = [
        'app.py',
        'requirements.txt',
        '.env',
        'src/config.py',
        'src/models/database.py',
        'src/models/user.py',
        'src/routes/auth.py',
        'src/routes/main.py',
        'src/routes/admin.py',
        'templates/base.html',
        'templates/index.html',
        'templates/auth/login.html',
        'templates/dashboard.html',
    ]
    
    missing = []
    for f in required_files:
        if not os.path.exists(f):
            missing.append(f)
        else:
            print(f"✓ {f}")
    
    if missing:
        print(f"\n✗ Missing files: {missing}")
        return False
    
    print("\n✓ All required files present")
    return True


def check_database():
    """Check database is set up correctly."""
    print("\n=== Checking Database ===")
    
    if not os.path.exists('local.db'):
        print("✗ local.db not found")
        return False
    
    conn = sqlite3.connect('local.db')
    c = conn.cursor()
    
    # Check tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in c.fetchall()]
    
    required_tables = ['users', 'words', 'example_sentences', 'pending_approvals', 
                       'verification_tokens', 'tts_cache', 'stroke_gifs']
    
    for table in required_tables:
        if table in tables:
            print(f"✓ Table: {table}")
        else:
            print(f"✗ Missing table: {table}")
    
    # Check data counts
    print("\nData counts:")
    for table in ['users', 'words', 'example_sentences']:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            print(f"  {table}: {count}")
        except:
            print(f"  {table}: ERROR")
    
    conn.close()
    print("\n✓ Database check complete")
    return True


def check_app():
    """Check app can start."""
    print("\n=== Checking App ===")
    
    try:
        from app import create_app
        app = create_app('development')
        print("✓ App creates successfully")
        
        with app.test_client() as client:
            # Test routes
            routes = ['/', '/auth/login', '/auth/register', '/help']
            for route in routes:
                resp = client.get(route)
                status = "✓" if resp.status_code == 200 else "✗"
                print(f"{status} {route}: {resp.status_code}")
        
        print("\n✓ App routes working")
        return True
    except Exception as e:
        print(f"\n✗ App error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_migration_data():
    """Check migration data exists."""
    print("\n=== Checking Migration Data ===")
    
    if not os.path.exists('migration_data'):
        print("✗ migration_data directory not found")
        return False
    
    files = os.listdir('migration_data')
    for f in files:
        size = os.path.getsize(f"migration_data/{f}")
        print(f"✓ {f}: {size:,} bytes")
    
    print("\n✓ Migration data available")
    return True


def main():
    """Run all checks."""
    print("=" * 60)
    print("Anki Card Creator - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Files", check_files),
        ("Database", check_database),
        ("App", check_app),
        ("Migration Data", check_migration_data),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    
    print("=" * 60)
    if all_passed:
        print("✓ All checks passed! Ready to deploy.")
    else:
        print("✗ Some checks failed. Please review.")
    print("=" * 60)
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
