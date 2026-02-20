"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    USE_LOCAL_DB = os.environ.get('USE_LOCAL_DB', 'false').lower() == 'true'
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME')
    TELEGRAM_ADMIN_ID = os.environ.get('TELEGRAM_ADMIN_ID')
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # API Keys
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    UNSPLASH_API_KEY = os.environ.get('UNSPLASH_API_KEY')
    GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_VISION_API_KEY')
    # TTS API URL - defaults to local API endpoint, override for production domain
    TTS_API_URL = os.environ.get('TTS_API_URL', '/api/tts')
    
    # Admin
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    # App
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Rate limiting
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = "100 per minute"
    
    # Performance mode
    ENABLE_WEB_INTERFACE = os.environ.get('ENABLE_WEB_INTERFACE', 'true').lower() == 'true'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    USE_LOCAL_DB = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    USE_LOCAL_DB = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
