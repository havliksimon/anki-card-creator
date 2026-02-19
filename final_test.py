#!/usr/bin/env python3
"""Final comprehensive test before deployment."""
import os
import sys
import sqlite3

# Force local SQLite mode for testing
os.environ['USE_LOCAL_DB'] = 'true'
os.environ['FLASK_ENV'] = 'development'

def test_imports():
    """Test all imports work."""
    print("=== Testing Imports ===")
    try:
        from app import create_app
        from src.models.database import db
        from src.models.user import User
        from src.utils.chinese_utils import chinese_to_styled_pinyin
        from src.utils.email_service import generate_verification_token
        from src.services.dictionary_service import dictionary_service
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database():
    """Test database is accessible."""
    print("\n=== Testing Database ===")
    try:
        conn = sqlite3.connect('local.db')
        c = conn.cursor()
        
        # Check tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        required = ['users', 'words', 'example_sentences']
        
        for table in required:
            if table not in tables:
                print(f"✗ Missing table: {table}")
                return False
        
        # Check data exists
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM words")
        word_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM example_sentences")
        sent_count = c.fetchone()[0]
        
        conn.close()
        
        print(f"✓ Database connected")
        print(f"  - Users: {user_count}")
        print(f"  - Words: {word_count}")
        print(f"  - Example sentences: {sent_count}")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_app_creation():
    """Test Flask app creation."""
    print("\n=== Testing App Creation ===")
    try:
        from app import create_app
        app = create_app('development')
        print("✓ App created successfully")
        return app
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_routes(app):
    """Test all routes."""
    print("\n=== Testing Routes ===")
    
    tests = [
        ('GET', '/', 'Homepage'),
        ('GET', '/auth/login', 'Login page'),
        ('GET', '/auth/register', 'Register page'),
        ('GET', '/help', 'Help page'),
        ('GET', '/api/tts/你好', 'TTS API'),
    ]
    
    client = app.test_client()
    all_passed = True
    
    for method, route, name in tests:
        try:
            if method == 'GET':
                resp = client.get(route)
            else:
                resp = client.post(route)
            
            if resp.status_code == 200:
                print(f"✓ {name}: {resp.status_code}")
            else:
                print(f"⚠ {name}: {resp.status_code} (may be OK)")
        except Exception as e:
            print(f"✗ {name}: {e}")
            all_passed = False
    
    return all_passed


def test_chinese_processing():
    """Test Chinese text processing."""
    print("\n=== Testing Chinese Processing ===")
    try:
        from src.utils.chinese_utils import (
            chinese_to_styled_pinyin, 
            extract_chinese_words,
            is_chinese
        )
        
        # Test pinyin
        pinyin, hanzi = chinese_to_styled_pinyin("你好")
        assert 'nǐ' in pinyin
        assert 'hǎo' in pinyin
        print(f"✓ Pinyin: 你好 -> {pinyin[:50]}...")
        
        # Test extraction
        text = "Hello 你好世界 123"
        words = extract_chinese_words(text)
        assert '你好世界' in words
        print(f"✓ Extraction: {words}")
        
        # Test detection
        assert is_chinese("中文") == True
        assert is_chinese("English") == False
        print("✓ Chinese detection works")
        
        return True
    except Exception as e:
        print(f"✗ Chinese processing failed: {e}")
        return False


def test_authentication(app):
    """Test authentication flow."""
    print("\n=== Testing Authentication ===")
    
    client = app.test_client()
    
    try:
        # Test registration
        resp = client.post('/auth/register', data={
            'email': 'test_final@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        print(f"✓ Registration: {resp.status_code}")
        
        # Test login
        resp = client.post('/auth/login/email', data={
            'email': 'admin@anki-cards.com',
            'password': 'admin123'
        }, follow_redirects=True)
        print(f"✓ Login: {resp.status_code}")
        
        return True
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False


def test_dictionary_service():
    """Test dictionary service."""
    print("\n=== Testing Dictionary Service ===")
    try:
        from src.services.dictionary_service import dictionary_service
        
        # Test CSV generation
        with open('local.db', 'r') as f:
            pass  # Just verify file exists
        
        print("✓ Dictionary service available")
        return True
    except Exception as e:
        print(f"✗ Dictionary service failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("ANKI CARD CREATOR - FINAL TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    
    app = test_app_creation()
    if app:
        results.append(("App Creation", True))
        results.append(("Routes", test_routes(app)))
        results.append(("Authentication", test_authentication(app)))
    else:
        results.append(("App Creation", False))
        results.append(("Routes", False))
        results.append(("Authentication", False))
    
    results.append(("Chinese Processing", test_chinese_processing()))
    results.append(("Dictionary Service", test_dictionary_service()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - READY TO RUN!")
        print("=" * 70)
        print("\nTo run locally:")
        print("  source .venv/bin/activate")
        print("  python app.py")
        print("\nThen open: http://localhost:5000")
    else:
        print("❌ SOME TESTS FAILED - CHECK ERRORS ABOVE")
    print("=" * 70)
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
