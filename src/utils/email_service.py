"""Email service for sending verification emails."""
from flask import render_template, current_app
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import secrets
import string

mail = Mail()


def init_mail(app):
    """Initialize mail service."""
    mail.init_app(app)


def generate_token(length: int = 32) -> str:
    """Generate random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_verification_token(user_id: str, token_type: str = 'email') -> str:
    """Generate verification token."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'user_id': user_id, 'type': token_type}, salt=token_type)


def verify_token(token: str, token_type: str = 'email', max_age: int = 86400):
    """Verify token and return user_id."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt=token_type, max_age=max_age)
        return data.get('user_id')
    except:
        return None


def send_verification_email(email: str, token: str):
    """Send email verification email."""
    msg = Message(
        'Verify Your Email - Anki Card Creator',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    
    verify_url = f"{current_app.config['APP_URL']}/auth/verify-email/{token}"
    
    msg.html = render_template('email/verify_email.html', verify_url=verify_url)
    msg.body = f"""
    Welcome to Anki Card Creator!
    
    Please verify your email by clicking the link below:
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you did not create an account, please ignore this email.
    """
    
    mail.send(msg)


def send_password_reset_email(email: str, token: str):
    """Send password reset email."""
    msg = Message(
        'Reset Your Password - Anki Card Creator',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    
    reset_url = f"{current_app.config['APP_URL']}/auth/reset-password/{token}"
    
    msg.html = render_template('email/reset_password.html', reset_url=reset_url)
    msg.body = f"""
    Password Reset Request
    
    You requested to reset your password. Click the link below:
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you did not request this, please ignore this email.
    """
    
    mail.send(msg)


def send_approval_notification(email: str, approved: bool = True):
    """Send account approval notification."""
    msg = Message(
        'Account Approved - Anki Card Creator',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    
    if approved:
        msg.html = render_template('email/account_approved.html')
        msg.body = """
        Good news! Your account has been approved.
        
        You can now log in and start using Anki Card Creator.
        
        Happy learning!
        """
    else:
        msg.html = render_template('email/account_rejected.html')
        msg.body = """
        We regret to inform you that your account request has been declined.
        
        If you believe this is an error, please contact the administrator.
        """
    
    mail.send(msg)
