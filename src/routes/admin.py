"""Admin routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user

from src.models.database import db
from src.models.user import User
from src.utils.email_service import send_approval_notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require admin access."""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin_user:
            flash('Access denied.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard."""
    stats = db.get_stats()
    pending = db.get_pending_approvals()
    users = db.get_users()
    
    # Ensure pending is a list
    if not isinstance(pending, list):
        pending = []
    
    # Ensure users is a list
    if not isinstance(users, list):
        users = []
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         pending=pending,
                         users=users)


@admin_bp.route('/deck-switcher')
@login_required
@admin_required
def deck_switcher():
    """Deck switcher for admin - view any user's deck."""
    # Get all users sorted by ID (low numbers first, then UUIDs)
    all_users = db.get_users()
    
    # Sort: numeric IDs first (as integers), then others
    def sort_key(user):
        uid = user.get('id', '')
        try:
            # Try to parse as integer for numeric IDs
            return (0, int(uid))
        except (ValueError, TypeError):
            # UUIDs or other formats come after
            return (1, uid)
    
    all_users.sort(key=sort_key)
    
    # Get current viewed user from session or default to self
    viewed_user_id = session.get('viewed_user_id', current_user.id)
    viewed_user = None
    
    if viewed_user_id != current_user.id:
        user_data = db.get_user_by_id(viewed_user_id)
        if user_data:
            viewed_user = User(user_data)
    
    if not viewed_user:
        viewed_user = current_user
        viewed_user_id = current_user.id
    
    # Get words for viewed user
    words = db.get_words_by_user(viewed_user_id)
    
    return render_template('admin/deck_switcher.html',
                         users=all_users,
                         viewed_user=viewed_user,
                         words=words)


@admin_bp.route('/switch-to-user/<user_id>')
@login_required
@admin_required
def switch_to_user(user_id):
    """Switch to viewing a specific user's deck."""
    session['viewed_user_id'] = user_id
    user_data = db.get_user_by_id(user_id)
    if user_data:
        flash(f"Now viewing deck for: {user_data.get('email') or user_data.get('telegram_id') or user_id}", 'info')
    return redirect(url_for('admin.deck_switcher'))


@admin_bp.route('/reset-to-my-deck')
@login_required
@admin_required
def reset_to_my_deck():
    """Reset to viewing admin's own deck."""
    session.pop('viewed_user_id', None)
    flash("Back to your own deck", 'info')
    return redirect(url_for('admin.deck_switcher'))


@admin_bp.route('/swap-to-deck', methods=['POST'])
@login_required
@admin_required
def swap_to_deck():
    """Swap to a deck by number - creates if doesn't exist."""
    deck_number = request.form.get('deck_number', '').strip()
    
    if not deck_number:
        flash('Please enter a deck number', 'error')
        return redirect(url_for('admin.deck_switcher'))
    
    # Validate it's a positive integer
    try:
        deck_num = int(deck_number)
        if deck_num < 0:
            raise ValueError()
    except ValueError:
        flash('Deck number must be a positive integer', 'error')
        return redirect(url_for('admin.deck_switcher'))
    
    deck_id = str(deck_num)
    
    # Check if user exists
    existing_user = db.get_user_by_id(deck_id)
    
    if not existing_user:
        # Create a new placeholder user for this deck
        db.create_user(
            user_id=deck_id,
            email=None,
            password_hash=None,
            telegram_id=deck_id,
            telegram_username=f"deck_{deck_id}",
            is_active=True,
            is_admin=False
        )
        flash(f"Created and switched to new deck: {deck_id}", 'success')
    else:
        flash(f"Switched to deck: {deck_id}", 'info')
    
    session['viewed_user_id'] = deck_id
    return redirect(url_for('admin.deck_switcher'))


@admin_bp.route('/pending')
@login_required
@admin_required
def pending():
    """View pending approvals."""
    pending_list = db.get_pending_approvals()
    # Ensure pending is a list
    if not isinstance(pending_list, list):
        pending_list = []
    return render_template('admin/pending.html', pending=pending_list)


@admin_bp.route('/approve/<user_id>', methods=['POST'])
@login_required
@admin_required
def approve(user_id):
    """Approve a user."""
    user = User.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.pending'))
    
    user.activate()
    
    # Send notification email
    if user.email:
        try:
            send_approval_notification(user.email, approved=True)
        except Exception as e:
            current_app.logger.error(f"Failed to send approval notification: {e}")
    
    flash(f'Approved user: {user.display_name}', 'success')
    return redirect(url_for('admin.pending'))


@admin_bp.route('/reject/<user_id>', methods=['POST'])
@login_required
@admin_required
def reject(user_id):
    """Reject a user."""
    user = User.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.pending'))
    
    # Deactivate and remove from pending
    user.deactivate()
    db.remove_pending_approval(user_id)
    
    # Send notification email
    if user.email:
        try:
            send_approval_notification(user.email, approved=False)
        except Exception as e:
            current_app.logger.error(f"Failed to send rejection notification: {e}")
    
    flash(f'Rejected user: {user.display_name}', 'info')
    return redirect(url_for('admin.pending'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """View all users."""
    users_list = db.get_users()
    
    # Sort: numeric IDs first, then others
    def sort_key(user):
        uid = user.get('id', '')
        try:
            return (0, int(uid))
        except (ValueError, TypeError):
            return (1, uid)
    
    users_list.sort(key=sort_key)
    
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/toggle-admin/<user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle admin status."""
    if user_id == current_user.id:
        flash('Cannot modify your own admin status.', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    new_status = not user.is_admin_user
    user.update(is_admin=new_status)
    
    flash(f'Updated admin status for {user.display_name}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/deactivate/<user_id>', methods=['POST'])
@login_required
@admin_required
def deactivate(user_id):
    """Deactivate a user."""
    if user_id == current_user.id:
        flash('Cannot deactivate yourself.', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    user.deactivate()
    flash(f'Deactivated user: {user.display_name}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/stats')
@login_required
@admin_required
def stats():
    """View detailed statistics."""
    # Get all users with their word counts
    users_data = []
    all_users = db.get_users()
    
    for user_data in all_users:
        user = User(user_data)
        word_count = db.get_user_stats(user.id).get('word_count', 0)
        users_data.append({
            'user': user,
            'word_count': word_count
        })
    
    # Sort by word count
    users_data.sort(key=lambda x: x['word_count'], reverse=True)
    
    return render_template('admin/stats.html', users_data=users_data)
