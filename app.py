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
from src.routes.auth import auth_bp
from src.routes.main import main_bp
from src.routes.admin import admin_bp
from flask import request  # Import for rate limiter


def create_app(config_name=None):
    """Application factory."""
    config_name = config_name or os.environ.get('FLASK_ENV', 'production')
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['production']))
    
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
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def rate_limit(error):
        return render_template('errors/429.html'), 429
    
    # Context processors
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'Anki Card Creator',
            'telegram_bot_username': app.config.get('TELEGRAM_BOT_USERNAME', '')
        }
    
    # Create admin user if configured
    with app.app_context():
        create_admin_user(app)
    
    return app


def create_admin_user(app):
    """Create admin user if configured."""
    admin_email = app.config.get('ADMIN_EMAIL')
    admin_password = app.config.get('ADMIN_PASSWORD')
    
    if not admin_email or not admin_password:
        return
    
    existing = User.get_by_email(admin_email)
    
    if not existing:
        try:
            db.create_user(
                user_id=User.generate_id(),
                email=admin_email,
                password_hash=User.hash_password(admin_password),
                is_active=True,
                is_admin=True
            )
            app.logger.info(f'Admin user created: {admin_email}')
        except Exception as e:
            app.logger.error(f'Failed to create admin user: {e}')


# Create the application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
