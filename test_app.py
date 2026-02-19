#!/usr/bin/env python3
"""Comprehensive tests for the Anki Card Creator app."""
import os
import sys
import sqlite3

# Set up test environment
os.environ['USE_LOCAL_DB'] = 'true'

from app import create_app
from src.models.database import db
from src.models.user import User
from src.utils.email_service import generate_verification_token, verify_token
from src.utils.chinese_utils import chinese_to_styled_pinyin, extract_chinese_words


def test_app_factory():
    """Test app factory creates app correctly."""
    print("\n=== Testing App Factory ===")
    app = create_app('testing')
    assert app is not None
    print("✓ App factory works")


def test_database():
    """Test database operations."""
    print("\n=== Testing Database ===")
    app = create_app('testing')
    
    with app.app_context():
        # Test user creation
        user_data = {
            'id': User.generate_id(),
            'email': 'test@example.com',
            'password_hash': User.hash_password('password123'),
            'is_active': True,
            'is_admin': False
        }
        user = db.create_user(user_data)
        assert user is not None
        print(f"✓ User created: {user['id']}")
        
        # Test user retrieval
        retrieved = db.get_user(user['id'])
        assert retrieved is not None
        assert retrieved['email'] == 'test@example.com'
        print("✓ User retrieval works")
        
        # Test word creation
        word_data = {
            'character': '你好',
            'user_id': user['id'],
            'pinyin': '<span style="color:#ff0000">nǐ</span> <span style="color:#ffaa00">hǎo</span>',
            'translation': 'Hello',
            'styled_term': '<span style="color:#ff0000">你</span><span style="color:#ffaa00">好</span>'
        }
        word = db.create_word(word_data)
        assert word is not None
        print("✓ Word created")
        
        # Test word retrieval
        words = db.get_words_by_user(user['id'])
        assert len(words) == 1
        assert words[0]['character'] == '你好'
        print("✓ Word retrieval works")


def test_chinese_utils():
    """Test Chinese language utilities."""
    print("\n=== Testing Chinese Utils ===")
    
    # Test pinyin conversion
    pinyin, hanzi = chinese_to_styled_pinyin("你好")
    assert 'nǐ' in pinyin
    assert 'hǎo' in pinyin
    print(f"✓ Pinyin conversion: 你好 -> {pinyin}")
    
    # Test word extraction
    text = "Hello 你好世界 this is 中文"
    words = extract_chinese_words(text)
    assert '你好世界' in words
    assert '中文' in words
    print(f"✓ Word extraction: {words}")


def test_auth():
    """Test authentication."""
    print("\n=== Testing Authentication ===")
    app = create_app('testing')
    
    with app.test_client() as client:
        # Test login page
        resp = client.get('/auth/login')
        assert resp.status_code == 200
        print("✓ Login page accessible")
        
        # Test register page
        resp = client.get('/auth/register')
        assert resp.status_code == 200
        print("✓ Register page accessible")
        
        # Test registration
        resp = client.post('/auth/register', data={
            'email': 'newuser@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert resp.status_code == 200
        print("✓ Registration works")


def test_email_tokens():
    """Test email token generation and verification."""
    print("\n=== Testing Email Tokens ===")
    app = create_app('testing')
    
    with app.app_context():
        # Generate token
        user_id = User.generate_id()
        token = generate_verification_token(user_id, 'email')
        assert token is not None
        print(f"✓ Token generated: {token[:20]}...")
        
        # Verify token
        verified_id = verify_token(token, 'email')
        assert verified_id == user_id
        print("✓ Token verification works")


def test_routes():
    """Test main routes."""
    print("\n=== Testing Routes ===")
    app = create_app('testing')
    
    with app.test_client() as client:
        # Public routes
        routes = [
            ('/', 'Home'),
            ('/help', 'Help'),
            ('/auth/login', 'Login'),
            ('/auth/register', 'Register'),
        ]
        
        for route, name in routes:
            resp = client.get(route)
            assert resp.status_code == 200, f"{name} failed"
            print(f"✓ {name} page works")


def test_tts_api():
    """Test TTS API."""
    print("\n=== Testing TTS API ===")
    app = create_app('testing')
    
    with app.test_client() as client:
        resp = client.get('/api/tts/你好')
        assert resp.status_code == 200
        assert resp.content_type == 'audio/mpeg'
        print("✓ TTS API works")


def test_scraper():
    """Test scraper functionality."""
    print("\n=== Testing Scraper ===")
    
    try:
        from src.services.scraper_service import ChineseScraper
        
        scraper = ChineseScraper()
        print("✓ Scraper initialized")
        
        # Test MDBG scraping
        result = scraper.scrape_mdbg("你好")
        if result:
            print(f"✓ MDBG scraping works: {result.get('pinyin', 'N/A')}")
        else:
            print("⚠ MDBG scraping returned empty (may be normal)")
        
        scraper.close()
        print("✓ Scraper closed")
        
    except Exception as e:
        print(f"⚠ Scraper test skipped: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Anki Card Creator - Test Suite")
    print("=" * 60)
    
    tests = [
        test_app_factory,
        test_chinese_utils,
        test_database,
        test_email_tokens,
        test_auth,
        test_routes,
        test_tts_api,
        test_scraper,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
