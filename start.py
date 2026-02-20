#!/usr/bin/env python3
"""Startup script that handles both web and telegram-only modes."""
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_playwright():
    """Verify Playwright browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to launch browser
            browser = p.chromium.launch(headless=True)
            browser.close()
            print("✅ Playwright Chromium browser: OK")
            return True
    except Exception as e:
        print(f"⚠️  Playwright browser check failed: {e}")
        print("   Stroke GIF scraping will not work!")
        print("   Run: python3 -m playwright install chromium")
        return False

def main():
    """Start the application based on mode."""
    print("="*60)
    print("ANKI CARD CREATOR - STARTUP")
    print("="*60)
    
    # Verify Playwright is working
    verify_playwright()
    print("="*60)
    
    enable_web = os.environ.get('ENABLE_WEB_INTERFACE', 'true').lower() == 'true'
    
    if enable_web:
        print("STARTING: Full Web Mode")
        print("="*60)
        print("Web interface: ENABLED")
        print("Telegram bot: ENABLED")
        print("="*60)
        
        # Start Telegram bot as a separate process (not thread - survives gunicorn fork)
        import multiprocessing
        
        def run_bot_process():
            from app import app
            from src.services.telegram_bot import telegram_bot
            with app.app_context():
                telegram_bot.run()
        
        bot_proc = multiprocessing.Process(target=run_bot_process, daemon=True)
        bot_proc.start()
        print("Telegram bot started as separate process")
        
        # Start gunicorn for web server
        port = os.environ.get('PORT', '8000')
        workers = os.environ.get('GUNICORN_WORKERS', '1')
        threads = os.environ.get('GUNICORN_THREADS', '2')
        
        cmd = [
            'gunicorn',
            'app:app',
            '--bind', f'0.0.0.0:{port}',
            '--workers', workers,
            '--threads', threads,
            '--timeout', '120',
            '--access-logfile', '-',
            '--error-logfile', '-'
        ]
        
        print(f"Starting gunicorn on port {port}...")
        subprocess.run(cmd)
        
    else:
        print("="*60)
        print("STARTING: Telegram-Only Mode (Low RAM)")
        print("="*60)
        print("Web interface: DISABLED")
        print("Telegram bot: ENABLED")
        print("Memory optimized for 0.5GB RAM")
        print("="*60)
        
        # Start Telegram bot in main thread (required for signal handlers)
        from app import app
        from threading import Thread
        import logging
        import time
        
        # Initialize database for bot
        from src.models.database import db
        from src.services.telegram_bot import telegram_bot
        db.init_app(app)
        
        # Start Flask in background thread for health checks
        def run_flask():
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            port = os.environ.get('PORT', '8000')
            app.run(host='0.0.0.0', port=int(port), threaded=True, debug=False, use_reloader=False)
        
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        print("Health check server started")
        print("Waiting for server...")
        time.sleep(3)
        
        # Run bot in main thread (required for asyncio signal handlers)
        print("Starting Telegram bot in main thread...")
        with app.app_context():
            telegram_bot.run()

if __name__ == '__main__':
    main()
