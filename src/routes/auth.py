"""Authentication routes."""
import hashlib
import hmac
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from src.models.user import User
from src.models.database import db
from src.utils.email_service import (
    generate_verification_token, verify_token,
    send_verification_email, send_password_reset_email
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def check_telegram_auth(data: dict) -> bool:
    """Verify Telegram login widget data."""
    bot_token = current_app.config['TELEGRAM_BOT_TOKEN']
    
    # Check if hash is present
    if 'hash' not in data:
        return False
    
    received_hash = data.pop('hash')
    
    # Create data_check_string
    data_check_arr = []
    for key in sorted(data.keys()):
        if data[key] is not None:
            data_check_arr.append(f"{key}={data[key]}")
    data_check_string = '\n'.join(data_check_arr)
    
    # Generate secret key
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return calculated_hash == received_hash


@auth_bp.route('/login')
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/login.html')


@auth_bp.route('/login/email', methods=['POST'])
def login_email():
    """Email login handler."""
    email = request.form.get('email', '').lower().strip()
    password = request.form.get('password', '')
    
    if not email or not password:
        flash('Please provide both email and password.', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.get_by_email(email)
    
    if not user:
        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth.login'))
    
    if not User.check_password(user._data.get('password_hash', ''), password):
        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth.login'))
    
    if not user.is_active:
        flash('Your account is pending approval. Please wait for an administrator to approve your account.', 'warning')
        return redirect(url_for('auth.login'))
    
    user.update(last_login=datetime.utcnow())
    login_user(user)
    flash(f'Welcome back, {user.display_name}!', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/login/telegram', methods=['POST', 'GET'])
def login_telegram():
    """Telegram login handler."""
    # Handle GET requests (error callbacks from Telegram widget)
    if request.method == 'GET':
        error = request.args.get('error', 'Unknown error')
        current_app.logger.error(f"Telegram login error: {error}")
        flash(f'Telegram login failed: {error}. Please check domain configuration.', 'error')
        return redirect(url_for('auth.login', telegram_error=error))
    
    # POST request from Telegram widget
    data = request.form.to_dict()
    
    # Log the login attempt (for debugging)
    current_app.logger.info(f"Telegram login attempt: id={data.get('id')}, username={data.get('username')}")
    
    # Check auth date (must be within 24 hours)
    auth_date = int(data.get('auth_date', 0))
    if datetime.utcnow().timestamp() - auth_date > 86400:
        flash('Login link expired. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Verify Telegram data
    if not check_telegram_auth(data):
        current_app.logger.error("Telegram auth verification failed")
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    
    telegram_id = data.get('id')
    telegram_username = data.get('username', '')
    
    # Check if user exists
    user = User.get_by_telegram(telegram_id)
    
    if not user:
        # Create new user
        user = User.create_telegram_user(telegram_id, telegram_username)
        flash('Account created! Your account is pending approval.', 'info')
        return redirect(url_for('auth.login'))
    
    if not user.is_active:
        flash('Your account is pending approval. Please wait for an administrator to approve your account.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Update last login
    user.update(last_login=datetime.utcnow())
    login_user(user)
    flash(f'Welcome, {user.display_name}!', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if email exists
        if User.get_by_email(email):
            flash('An account with this email already exists.', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        user = User.create_email_user(email, password)
        
        if user:
            # Send verification email
            token = generate_verification_token(user.id, 'email')
            try:
                send_verification_email(email, token)
                flash('Account created! Please check your email to verify your address. Your account is also pending admin approval.', 'success')
            except Exception as e:
                current_app.logger.error(f"Failed to send verification email: {e}")
                flash('Account created! However, we could not send a verification email. Please contact support.', 'warning')
            
            return redirect(url_for('auth.login'))
        else:
            flash('Failed to create account. Please try again.', 'error')
    
    return render_template('auth/register.html')


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify email address."""
    user_id = verify_token(token, 'email')
    
    if not user_id:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))
    
    # Email is verified, but account still needs admin approval
    flash('Your email has been verified! Your account is pending admin approval.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page."""
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        user = User.get_by_email(email)
        
        if user:
            token = generate_verification_token(user.id, 'password')
            try:
                send_password_reset_email(email, token)
                flash('Password reset instructions sent to your email.', 'success')
            except Exception as e:
                current_app.logger.error(f"Failed to send password reset email: {e}")
                flash('Could not send reset email. Please try again later.', 'error')
        else:
            # Don't reveal if email exists
            flash('If an account exists with this email, you will receive reset instructions.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password page."""
    user_id = verify_token(token, 'password', max_age=3600)  # 1 hour
    
    if not user_id:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.login'))
    
    user = User.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
        
        user.update(password_hash=User.hash_password(password))
        flash('Your password has been reset. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
