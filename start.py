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
        
        # Start Telegram bot in a separate thread
        from threading import Thread
        from app import app
        
        # Initialize database for bot
        with app.app_context():
            from src.services.telegram_bot import telegram_bot
            
            def run_bot():
                telegram_bot.run()
            
            bot_thread = Thread(target=run_bot, daemon=True)
            bot_thread.start()
            print("Telegram bot started in background")
        
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
        
        # Start minimal web server for health checks
        port = os.environ.get('PORT', '8000')
        
        # Use a simple Flask server in a thread for health checks
        from app import app
        from threading import Thread
        import logging
        
        # Reduce logging to save memory
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        def run_flask():
            app.run(host='0.0.0.0', port=int(port), threaded=True, debug=False)
        
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        print(f"Health check server started on port {port}")
        print("Waiting for server to be ready...")
        time.sleep(2)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            sys.exit(0)

if __name__ == '__main__':
    main()
