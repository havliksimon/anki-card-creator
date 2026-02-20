"""Debug routes for troubleshooting."""
from flask import Blueprint, jsonify, session, current_app, render_template, request
from flask_login import login_required, current_user
from src.models.deck_manager import deck_manager

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')


@debug_bp.route('/deck-status')
@login_required
def deck_status():
    """Debug endpoint to check current deck status."""
    user_id = current_user.id
    deck_id = deck_manager.get_current_deck_id(user_id)
    deck_num = deck_manager.parse_deck_id(deck_id)[1]
    
    # Get all session keys related to this user
    user_session_keys = {k: v for k, v in session.items() if str(user_id) in k or 'deck' in k}
    
    return jsonify({
        'user_id': user_id,
        'current_deck_id': deck_id,
        'current_deck_num': deck_num,
        'session_keys': user_session_keys,
        'all_session_keys': list(session.keys()),
        'decks': deck_manager.get_user_decks(user_id)
    })


@debug_bp.route('/telegram-config')
def telegram_config():
    """Debug endpoint to check Telegram configuration."""
    return jsonify({
        'bot_username': current_app.config.get('TELEGRAM_BOT_USERNAME'),
        'has_token': bool(current_app.config.get('TELEGRAM_BOT_TOKEN')),
        'admin_id': current_app.config.get('TELEGRAM_ADMIN_ID'),
        'app_url': current_app.config.get('APP_URL'),
        'request_url': request.url,
        'request_host': request.host,
        'request_origin': request.headers.get('Origin', 'Not set')
    })


@debug_bp.route('/telegram-test')
def telegram_test():
    """Test page for Telegram login widget."""
    return render_template('debug/telegram_test.html')


@debug_bp.route('/telegram-diagnostic')
def telegram_diagnostic():
    """Detailed diagnostic page for Telegram login issues."""
    from flask import current_app
    return render_template('debug/telegram_diagnostic.html',
                         bot_username=current_app.config.get('TELEGRAM_BOT_USERNAME'),
                         has_token=bool(current_app.config.get('TELEGRAM_BOT_TOKEN')),
                         app_url=current_app.config.get('APP_URL'),
                         auth_url=url_for('auth.login_telegram', _external=True))
