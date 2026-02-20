"""Main Flask application."""
import os
from datetime import timedelta
from flask import Flask, render_template
from flask_login import LoginManager
from flask_limiter import Limiter

from src.config import config
from src.models.database import db
from src.models.user import User
from src.utils.email_service import init_mail
from flask import request  # Import for rate limiter


def create_app(config_name=None):
    """Application factory."""
    config_name = config_name or os.environ.get('FLASK_ENV', 'production')
    
    # Check if web interface should be enabled
    enable_web = os.environ.get('ENABLE_WEB_INTERFACE', 'true').lower() == 'true'
    
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['production']))
    
    # Store web enabled flag in config
    app.config['ENABLE_WEB_INTERFACE'] = enable_web
    
    # Set session lifetime
    app.permanent_session_lifetime = timedelta(days=7)
    
    # Initialize extensions
    db.init_app(app)
    init_mail(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=lambda: getattr(getattr(request, 'user', None), 'id', request.remote_addr),
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Register blueprints based on mode
    if enable_web:
        # Full web mode - load all routes
        from src.routes.auth import auth_bp
        from src.routes.main import main_bp
        from src.routes.admin import admin_bp
        from src.routes.api import api_bp
        from src.routes.debug import debug_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(debug_bp)
        
        # Error handlers for web
        @app.errorhandler(404)
        def not_found(error):
            return render_template('errors/404.html'), 404
        
        @app.errorhandler(500)
        def internal_error(error):
            return render_template('errors/500.html'), 500
        
        @app.errorhandler(429)
        def rate_limit(error):
            return render_template('errors/429.html'), 429
    else:
        # Telegram-only mode - minimal routes
        @app.route('/')
        def telegram_only_index():
            return """
            <html>
            <head><title>Anki Card Creator - Telegram Bot</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1>🤖 Anki Card Creator</h1>
                <p>This instance is running in <strong>Telegram-only mode</strong> for optimized performance.</p>
                <p>The web interface is disabled to save memory.</p>
                <h2>Use the Telegram Bot:</h2>
                <p><a href="https://t.me/anki_card_creator_bot" style="font-size: 18px; padding: 10px 20px; background: #0088cc; color: white; text-decoration: none; border-radius: 5px;">@anki_card_creator_bot</a></p>
                <hr>
                <p style="color: #666; font-size: 14px;">To enable web interface, set ENABLE_WEB_INTERFACE=true</p>
            </body>
            </html>
            """
        
        @app.route('/health')
        def health_check():
            return {'status': 'ok', 'mode': 'telegram_only'}
    
    # Context processors
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'Anki Card Creator',
            'telegram_bot_username': app.config.get('TELEGRAM_BOT_USERNAME', ''),
            'web_enabled': enable_web
        }
    
    # Create admin user if configured
    with app.app_context():
        create_admin_user(app)
    
    return app


def create_admin_user(app):
    """Create admin user if configured."""
    admin_email = app.config.get('ADMIN_EMAIL')
    admin_password = app.config.get('ADMIN_PASSWORD')
    admin_telegram_id = app.config.get('TELEGRAM_ADMIN_ID')
    
    if not admin_email or not admin_password:
        return
    
    existing = User.get_by_email(admin_email)
    
    if not existing:
        try:
            db.create_user(
                user_id=User.generate_id(),
                email=admin_email,
                password_hash=User.hash_password(admin_password),
                telegram_id=str(admin_telegram_id) if admin_telegram_id else None,
                telegram_username=None,
                is_active=True,
                is_admin=True
            )
            app.logger.info(f'Admin user created: {admin_email} (Telegram: {admin_telegram_id})')
        except Exception as e:
            app.logger.error(f'Failed to create admin user: {e}')


# Create the application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
