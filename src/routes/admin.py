"""Admin routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
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
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         pending=pending,
                         users=users)


@admin_bp.route('/pending')
@login_required
@admin_required
def pending():
    """View pending approvals."""
    pending = db.get_pending_approvals()
    return render_template('admin/pending.html', pending=pending)


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
