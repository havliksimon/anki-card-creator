#!/usr/bin/env python3
"""Test script to verify Telegram bot functionality and check for messages."""
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
os.environ['APP_URL'] = 'http://localhost:5000'

from telegram import Bot
from telegram.error import TelegramError


ADMIN_ID = os.environ.get('TELEGRAM_ADMIN_ID')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')


async def test_bot_connection():
    """Test that the bot can connect to Telegram API."""
    print("\n" + "="*70)
    print("TEST: Bot Connection")
    print("="*70)
    
    if not BOT_TOKEN:
        print("  ✗ BOT_TOKEN not set!")
        return False
    
    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        print(f"  ✓ Bot connected successfully")
        print(f"    Name: {me.full_name}")
        print(f"    Username: @{me.username}")
        print(f"    Bot ID: {me.id}")
        return True
    except TelegramError as e:
        print(f"  ✗ Failed to connect: {e}")
        return False


async def test_get_updates():
    """Get pending updates (messages sent to the bot)."""
    print("\n" + "="*70)
    print("TEST: Pending Updates (messages sent to bot)")
    print("="*70)
    
    if not BOT_TOKEN:
        print("  ✗ BOT_TOKEN not set!")
        return
    
    try:
        bot = Bot(token=BOT_TOKEN)
        
        updates = await bot.get_updates(timeout=10)
        
        if not updates:
            print("  ℹ No pending updates")
            return
        
        print(f"  ✓ Found {len(updates)} update(s)")
        
        cutoff = datetime.now() - timedelta(hours=24)
        
        for update in updates:
            if update.message:
                msg_time = update.message.date
                if msg_time.tzinfo:
                    msg_time = msg_time.replace(tzinfo=None)
                
                is_recent = msg_time > cutoff
                time_str = msg_time.strftime("%Y-%m-%d %H:%M:%S")
                status = "📬" if is_recent else "  "
                
                print(f"    {status} [{time_str}] {update.message.from_user.full_name}: {update.message.text[:50]}...")
                
    except TelegramError as e:
        print(f"  ✗ Error getting updates: {e}")


async def test_send_to_admin():
    """Test sending a message to the admin."""
    print("\n" + "="*70)
    print("TEST: Send Message to Admin")
    print("="*70)
    
    if not BOT_TOKEN:
        print("  ✗ BOT_TOKEN not set!")
        return
    
    if not ADMIN_ID:
        print("  ✗ ADMIN_ID not set!")
        return
    
    try:
        bot = Bot(token=BOT_TOKEN)
        
        message = (
            "🔧 *Bot Test Message*\n\n"
            "This is a test to verify the bot can send messages.\n\n"
            "If you're receiving this, the bot is working correctly!"
        )
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            parse_mode='Markdown'
        )
        
        print(f"  ✓ Test message sent to admin ({ADMIN_ID})")
        
    except TelegramError as e:
        print(f"  ✗ Failed to send message: {e}")
        if e.message == "Forbidden":
            print("     The user has not started a chat with the bot yet!")
            print("     Tell the user to message @anki_card_creator_bot first")


async def main():
    """Run all tests."""
    print("="*70)
    print("TELEGRAM BOT VERIFICATION TEST")
    print("="*70)
    print(f"Admin ID: {ADMIN_ID or 'Not set'}")
    print(f"Bot Token: {'Set' if BOT_TOKEN else 'Not set'}")
    
    # Test 1: Bot connection
    if not await test_bot_connection():
        print("\n❌ Bot connection failed. Check your BOT_TOKEN.")
        return
    
    # Test 2: Get pending updates
    await test_get_updates()
    
    # Test 3: Send to admin
    await test_send_to_admin()
    
    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70)
    print("\nIf no updates were found, the user needs to send a message")
    print("directly to the bot @anki_card_creator_bot")


if __name__ == '__main__':
    asyncio.run(main())
