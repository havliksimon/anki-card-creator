"""User model and authentication."""
import uuid
import bcrypt
from typing import Optional
from flask_login import UserMixin
from src.models.database import db


class User(UserMixin):
    """User model compatible with Flask-Login."""
    
    def __init__(self, user_data: dict):
        self._data = user_data
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.telegram_id = user_data.get('telegram_id')
        self.telegram_username = user_data.get('telegram_username')
        self.is_active_user = user_data.get('is_active', False)
        self.is_admin_user = user_data.get('is_admin', False)
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
    
    @property
    def is_active(self) -> bool:
        """Required by Flask-Login."""
        return self.is_active_user
    
    @property
    def is_authenticated(self) -> bool:
        """Required by Flask-Login."""
        return True
    
    @property
    def is_anonymous(self) -> bool:
        """Required by Flask-Login."""
        return False
    
    @property
    def display_name(self) -> str:
        """Get display name for user."""
        if self.telegram_username:
            return f"@{self.telegram_username}"
        return self.email or "Unknown"
    
    @staticmethod
    def generate_id() -> str:
        """Generate unique user ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def check_password(password_hash: str, password: str) -> bool:
        """Check password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        """Get user by ID."""
        # Need to add get_user method to database
        user_data = db.get_user_by_id(user_id)
        return cls(user_data) if user_data else None
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """Get user by email."""
        user_data = db.get_user_by_email(email)
        return cls(user_data) if user_data else None
    
    @classmethod
    def get_by_telegram(cls, telegram_id: str) -> Optional['User']:
        """Get user by Telegram ID."""
        user_data = db.get_user_by_telegram_id(telegram_id)
        return cls(user_data) if user_data else None
    
    @classmethod
    def create_email_user(cls, email: str, password: str, is_admin: bool = False) -> Optional['User']:
        """Create new email user."""
        user_id = cls.generate_id()
        result = db.create_user(
            user_id=user_id,
            email=email,
            password_hash=cls.hash_password(password),
            is_active=is_admin,  # Auto-activate if admin
            is_admin=is_admin
        )
        if result and not is_admin:
            # Add to pending approvals for regular users
            db.create_pending_approval(user_id, email, cls.hash_password(password))
        return cls.get_by_id(user_id) if result else None
    
    @classmethod
    def create_telegram_user(cls, telegram_id: str, telegram_username: str = None) -> Optional['User']:
        """Create new Telegram user."""
        user_id = cls.generate_id()
        result = db.create_user(
            user_id=user_id,
            email=None,
            password_hash=None,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            is_active=False,
            is_admin=False
        )
        if result:
            db.create_pending_approval(user_id, email=None, password_hash=None, 
                                        telegram_id=telegram_id, telegram_username=telegram_username)
        return cls.get_by_id(user_id) if result else None
    
    def link_telegram(self, telegram_id: str, telegram_username: str = None) -> bool:
        """Link Telegram account to existing user."""
        self.telegram_id = telegram_id
        self.telegram_username = telegram_username
        return db.update_user(self.id, {
            'telegram_id': telegram_id,
            'telegram_username': telegram_username
        })
    
    def unlink_telegram(self) -> bool:
        """Unlink Telegram account."""
        self.telegram_id = None
        self.telegram_username = None
        return db.update_user(self.id, {
            'telegram_id': None,
            'telegram_username': None
        })
    
    def update(self, **kwargs) -> bool:
        """Update user fields."""
        return db.update_user(self.id, kwargs)
    
    def activate(self) -> bool:
        """Activate user account."""
        self.is_active_user = True
        db.update_user(self.id, {'is_active': True})
        return True
    
    def deactivate(self) -> bool:
        """Deactivate user account."""
        self.is_active_user = False
        return db.update_user(self.id, {'is_active': False})
    
    def get_stats(self) -> dict:
        """Get user statistics."""
        return db.get_user_stats(self.id)
    
    def get_words(self) -> list:
        """Get all user's words."""
        return db.get_words_by_user(self.id)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'telegram_id': self.telegram_id,
            'telegram_username': self.telegram_username,
            'is_active': self.is_active_user,
            'is_admin': self.is_admin_user,
            'display_name': self.display_name
        }
