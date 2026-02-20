#!/usr/bin/env python3
"""Startup script that handles both web and telegram-only modes."""
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Start the application based on mode."""
    enable_web = os.environ.get('ENABLE_WEB_INTERFACE', 'true').lower() == 'true'
    
    if enable_web:
        print("="*60)
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
        
        # Start Telegram bot first
        from app import app
        from threading import Thread
        import logging
        
        # Initialize database for bot
        from src.models.database import db
        from src.services.telegram_bot import telegram_bot
        db.init_app(app)
        
        # Start bot in background thread
        def run_bot():
            with app.app_context():
                telegram_bot.run()
        
        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()
        print("Telegram bot started")
        
        # Start minimal web server for health checks in main thread
        port = os.environ.get('PORT', '8000')
        
        # Reduce logging to save memory
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        print(f"Health check server starting on port {port}")
        
        # Run Flask for health checks (this blocks)
        app.run(host='0.0.0.0', port=int(port), threaded=True, debug=False)

if __name__ == '__main__':
    main()
