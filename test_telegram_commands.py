#!/usr/bin/env python3
"""Test script for Telegram bot commands."""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()
os.environ['APP_URL'] = 'http://localhost:5000'

from src.models.database import db
from src.models.user import User
from src.services.telegram_bot import TelegramBotService, ADMIN_ID
from src.services.dictionary_service import dictionary_service


def test_admin_check():
    """Test admin permission checking."""
    print("\n" + "="*70)
    print("TEST: Admin Permission Check")
    print("="*70)
    
    bot = TelegramBotService()
    
    test_cases = [
        ('5624590693', True),   # Should be admin
        ('123456789', False),   # Should not be admin
        (5624590693, True),     # Int should also work
        ('999999999', False),   # Random ID
    ]
    
    for telegram_id, expected in test_cases:
        result = bot._is_admin(str(telegram_id))
        status = "✓" if result == expected else "✗"
        print(f"  {status} _is_admin({telegram_id}) = {result} (expected {expected})")


def test_user_operations():
    """Test user creation and retrieval."""
    print("\n" + "="*70)
    print("TEST: User Operations")
    print("="*70)
    
    bot = TelegramBotService()
    
    # Test getting admin user
    admin_user = db.get_user_by_telegram_id('5624590693')
    if admin_user:
        print(f"  ✓ Admin user found: {admin_user['id'][:8]}...")
        print(f"    is_active: {admin_user.get('is_active')}")
        print(f"    is_admin: {admin_user.get('is_admin')}")
    else:
        print("  ✗ Admin user NOT found!")
    
    # Test regular user (should create new)
    test_user_id = '999999999999'
    user = db.get_user_by_telegram_id(test_user_id)
    if user:
        print(f"  ✓ Test user exists: {user['id'][:8]}...")
    else:
        print(f"  ℹ Test user {test_user_id} not found (will be created on first use)")


def test_dictionary_service():
    """Test word details retrieval with scraping."""
    print("\n" + "="*70)
    print("TEST: Dictionary Service (with Scraping)")
    print("="*70)
    
    # Test getting word details
    word = '你好'
    print(f"\n  Getting details for: {word}")
    
    try:
        details = dictionary_service.get_word_details(word)
        
        checks = [
            ('character', details.get('character')),
            ('pinyin', details.get('pinyin')),
            ('translation', details.get('translation')),
            ('stroke_gifs', details.get('stroke_gifs')),
            ('pronunciation', details.get('pronunciation')),
            ('real_usage_examples', details.get('real_usage_examples')),
        ]
        
        for field, value in checks:
            has_data = bool(value)
            status = "✓" if has_data else "✗"
            preview = str(value)[:40] + "..." if value and len(str(value)) > 40 else value
            print(f"    {status} {field}: {preview if has_data else 'EMPTY'}")
        
        print(f"\n  ✓ Word details retrieved successfully")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")


def test_csv_export():
    """Test CSV export functionality."""
    print("\n" + "="*70)
    print("TEST: CSV Export")
    print("="*70)
    
    try:
        # Get admin user
        admin_user = db.get_user_by_telegram_id('5624590693')
        if not admin_user:
            print("  ✗ Admin user not found!")
            return
        
        user_id = admin_user['id']
        
        # Generate CSV
        csv_data = dictionary_service.generate_csv(user_id)
        
        # Parse and check
        lines = csv_data.decode('utf-8').strip().split('\n')
        print(f"  ✓ CSV generated: {len(lines)} rows")
        
        if lines:
            first_row = lines[0]
            cols = first_row.split(',')
            print(f"  ✓ Columns in first row: {len(cols)}")
            print(f"    First few: {cols[0]}, {cols[1][:30]}..., {cols[2][:30]}...")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")


def test_bot_commands():
    """Test bot command handlers exist."""
    print("\n" + "="*70)
    print("TEST: Bot Command Handlers")
    print("="*70)
    
    bot = TelegramBotService()
    
    # Check if token is set
    if bot.token:
        print(f"  ✓ Bot token configured")
    else:
        print(f"  ✗ Bot token NOT configured!")
    
    # Check ADMIN_ID
    if ADMIN_ID:
        print(f"  ✓ ADMIN_ID configured: {ADMIN_ID}")
    else:
        print(f"  ✗ ADMIN_ID NOT configured!")
    
    # List of expected commands
    expected_commands = [
        'cmd_start', 'cmd_help', 'cmd_dictionary', 'cmd_dictinfo',
        'cmd_export', 'cmd_list', 'cmd_chosedict', 'cmd_rmdict',
        'cmd_rm', 'cmd_search', 'cmd_clearmydata', 'cmd_changelog',
        'cmd_admin', 'cmd_stats', 'cmd_wipedict',
        'handle_text', 'handle_image'
    ]
    
    print("\n  Command handlers:")
    for cmd in expected_commands:
        exists = hasattr(bot, cmd)
        status = "✓" if exists else "✗"
        print(f"    {status} {cmd}")


def test_database_connection():
    """Test database connectivity."""
    print("\n" + "="*70)
    print("TEST: Database Connection")
    print("="*70)
    
    try:
        # Try to get stats
        stats = db.get_stats()
        print(f"  ✓ Database connected")
        print(f"    Mode: {stats.get('mode', 'unknown')}")
        print(f"    Total users: {stats.get('total_users', 0)}")
        print(f"    Total words: {stats.get('total_words', 0)}")
        
    except Exception as e:
        print(f"  ✗ Database error: {e}")


def main():
    """Run all tests."""
    print("="*70)
    print("TELEGRAM BOT TEST SUITE")
    print("="*70)
    
    try:
        test_database_connection()
        test_admin_check()
        test_user_operations()
        test_bot_commands()
        test_dictionary_service()
        test_csv_export()
        
        print("\n" + "="*70)
        print("ALL TESTS COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
