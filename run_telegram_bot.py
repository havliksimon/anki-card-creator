#!/usr/bin/env python3
"""Standalone Telegram Bot Runner for Anki Card Creator.

This script runs the Telegram bot independently of the web application.
You can run it locally or deploy it separately.

Usage:
    python run_telegram_bot.py

Environment Variables Required:
    TELEGRAM_BOT_TOKEN - Your bot token from @BotFather
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_SERVICE_KEY - Your Supabase service role key
    TELEGRAM_ADMIN_ID (optional) - Telegram ID of the admin user
"""
import os
import sys
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.telegram_bot import telegram_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def check_environment():
    """Check that required environment variables are set."""
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
        logger.error("\nPlease set these variables and try again.")
        logger.error("You can create a .env file or export them directly.")
        return False
    
    return True


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("ANKI CARD CREATOR - TELEGRAM BOT")
    logger.info("=" * 60)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Show config (without secrets)
    logger.info("\nConfiguration:")
    logger.info(f"  Supabase URL: {os.environ.get('SUPABASE_URL', 'Not set')}")
    logger.info(f"  Admin ID: {os.environ.get('TELEGRAM_ADMIN_ID', 'Not set')}")
    logger.info("\nStarting bot...")
    logger.info("Press Ctrl+C to stop\n")
    
    try:
        telegram_bot.run()
    except KeyboardInterrupt:
        logger.info("\n\nBot stopped by user.")
    except Exception as e:
        logger.error(f"\n\nBot crashed: {e}")
        raise


if __name__ == "__main__":
    main()
