#!/usr/bin/env python3
"""
Standalone Telegram Bot Runner for Anki Card Creator.

This script runs ONLY the Telegram bot without the web application.
It's useful for testing the bot separately or running the bot on a different server.

Usage:
    python run_bot.py

Required Environment Variables:
    TELEGRAM_BOT_TOKEN - Your bot token from @BotFather
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_SERVICE_KEY - Your Supabase service role key
"""
import os
import sys
import logging
import asyncio

# Setup logging first
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load dotenv
from dotenv import load_dotenv
load_dotenv()

def check_environment():
    """Check required environment variables."""
    required = [
        'TELEGRAM_BOT_TOKEN',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_KEY'
    ]
    
    missing = []
    for var in required:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        logger.error("=" * 60)
        logger.error("MISSING REQUIRED ENVIRONMENT VARIABLES:")
        for var in missing:
            logger.error(f"  - {var}")
        logger.error("=" * 60)
        logger.error("\nPlease set these variables:")
        logger.error("export TELEGRAM_BOT_TOKEN='your-token'")
        logger.error("export SUPABASE_URL='your-url'")
        logger.error("export SUPABASE_SERVICE_KEY='your-key'")
        return False
    
    return True

def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("ANKI CARD CREATOR - TELEGRAM BOT")
    logger.info("=" * 60)
    
    if not check_environment():
        sys.exit(1)
    
    # Initialize Flask app for database access
    from app import app as flask_app
    from src.models.database import db
    db.init_app(flask_app)
    
    # Import here after env check
    try:
        from src.services.telegram_bot import telegram_bot
    except ImportError as e:
        logger.error(f"Failed to import bot: {e}")
        sys.exit(1)
    
    # Show config (without secrets)
    logger.info("\nConfiguration:")
    logger.info(f"  Supabase URL: {os.environ.get('SUPABASE_URL', 'Not set')}")
    logger.info(f"  Admin ID: {os.environ.get('TELEGRAM_ADMIN_ID', 'Not set')}")
    logger.info("")
    
    try:
        telegram_bot.run()
    except KeyboardInterrupt:
        logger.info("\n\nBot stopped by user.")
    except Exception as e:
        logger.error(f"\n\nBot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
