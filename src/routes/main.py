"""Main application routes."""
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app, session
from flask_login import login_required, current_user

from src.models.database import db
from src.models.user import User
from src.models.deck_manager import deck_manager
from src.services.dictionary_service import dictionary_service
from src.utils.chinese_utils import (
    extract_chinese_words, chinese_to_styled_pinyin,
    get_coverage_percentage, get_hsk_progress
)

main_bp = Blueprint('main', __name__)


def get_current_deck_id():
    """Get current deck ID for the logged-in user."""
    if not current_user.is_authenticated:
        return None
    return deck_manager.get_current_deck_id(current_user.id)


@main_bp.route('/')
def index():
    """Home page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    deck_id = get_current_deck_id()
    
    # Get words for current deck
    words = db.get_words_by_user(current_user.id, deck_id)
    
    # Get deck info
    decks = deck_manager.get_user_decks(current_user.id)
    current_deck_num = deck_manager.parse_deck_id(deck_id)[1]
    current_deck_label = next((d.get('label', f'Deck {current_deck_num}') for d in decks if d.get('deck_id') == deck_id), f'Deck {current_deck_num}')
    
    # Calculate stats
    char_count = len(words)
    coverage = get_coverage_percentage(char_count)
    hsk_progress = get_hsk_progress(char_count)
    
    return render_template('dashboard.html', 
                         words=words[:10],
                         deck_id=deck_id,
                         deck_label=current_deck_label,
                         deck_number=current_deck_num,
                         decks=decks,
                         coverage=coverage,
                         hsk_progress=hsk_progress,
                         total_count=len(words))


@main_bp.route('/switch-deck/<int:deck_number>', methods=['POST'])
@login_required
def switch_deck(deck_number):
    """Switch to a different deck."""
    deck_manager.swap_to_deck(current_user.id, deck_number)
    flash(f'Switched to Deck {deck_number}', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/create-deck', methods=['POST'])
@login_required
def create_deck():
    """Create a new deck."""
    deck_number = request.form.get('deck_number', type=int)
    label = request.form.get('label', '').strip()
    
    if not deck_number or deck_number < 1:
        flash('Invalid deck number', 'error')
        return redirect(url_for('main.dashboard'))
    
    deck_manager.create_deck(current_user.id, deck_number, label)
    deck_manager.set_current_deck(current_user.id, deck_number)
    flash(f'Created and switched to Deck {deck_number}', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/dictionary')
@login_required
def dictionary():
    """View all saved words."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    deck_id = get_current_deck_id()
    words = db.get_words_by_user(current_user.id, deck_id)
    total = len(words)
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_words = words[start:end]
    
    total_pages = (total + per_page - 1) // per_page
    
    # Get deck info
    decks = deck_manager.get_user_decks(current_user.id)
    current_deck_num = deck_manager.parse_deck_id(deck_id)[1]
    current_deck_label = next((d.get('label', f'Deck {current_deck_num}') for d in decks if d.get('deck_id') == deck_id), f'Deck {current_deck_num}')
    
    return render_template('dictionary.html',
                         words=paginated_words,
                         deck_id=deck_id,
                         deck_label=current_deck_label,
                         deck_number=current_deck_num,
                         decks=decks,
                         page=page,
                         total_pages=total_pages,
                         total=total)


@main_bp.route('/word/<character>')
@login_required
def word_detail(character):
    """View word details."""
    deck_id = get_current_deck_id()
    
    # Find word in current deck
    words = db.get_words_by_user(current_user.id, deck_id)
    word = next((w for w in words if w.get('character') == character), None)
    
    if not word:
        flash('Word not found in current deck.', 'error')
        return redirect(url_for('main.dictionary'))
    
    return render_template('word_detail.html', word=word)


@main_bp.route('/add-word', methods=['GET', 'POST'])
@login_required
def add_word():
    """Add new word."""
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        
        if not text:
            flash('Please enter some Chinese text.', 'error')
            return redirect(url_for('main.add_word'))
        
        # Extract Chinese words
        chinese_words = extract_chinese_words(text)
        
        if not chinese_words:
            flash('No Chinese characters found.', 'error')
            return redirect(url_for('main.add_word'))
        
        deck_id = get_current_deck_id()
        added = []
        existing = []
        
        for word_text in chinese_words:
            # Check if word already exists in current deck
            words_in_deck = db.get_words_by_user(current_user.id, deck_id)
            existing_word = next((w for w in words_in_deck if w.get('character') == word_text), None)
            
            if existing_word:
                existing.append(word_text)
                continue
            
            # Get word details
            try:
                word_details = dictionary_service.get_word_details(word_text)
                word_details['user_id'] = deck_id  # Store with deck_id
                db.create_word(word_details)
                added.append(word_text)
            except Exception as e:
                current_app.logger.error(f"Error adding word {word_text}: {e}")
                flash(f'Error adding word: {word_text}', 'error')
        
        if added:
            flash(f'Added {len(added)} word(s): {", ".join(added)}', 'success')
        if existing:
            flash(f'Skipped {len(existing)} existing word(s): {", ".join(existing)}', 'info')
        
        return redirect(url_for('main.dictionary'))
    
    return render_template('add_word.html')


@main_bp.route('/delete-word/<int:word_id>', methods=['POST'])
@login_required
def delete_word(word_id):
    """Delete a word."""
    deck_id = get_current_deck_id()
    db.delete_word(word_id, current_user.id, deck_id)
    flash('Word deleted', 'success')
    return redirect(url_for('main.dictionary'))


@main_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all():
    """Clear all words in current deck."""
    deck_id = get_current_deck_id()
    db.delete_all_words(current_user.id, deck_id)
    flash('All words in current deck have been cleared.', 'success')
    return redirect(url_for('main.dictionary'))


@main_bp.route('/export')
@login_required
def export_csv():
    """Export words from current deck to CSV."""
    deck_id = get_current_deck_id()
    csv_data = dictionary_service.generate_csv(current_user.id, deck_id)
    
    # Parse deck number for filename
    _, deck_num = deck_manager.parse_deck_id(deck_id)
    
    return send_file(
        io.BytesIO(csv_data),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'anki_deck_{deck_num}.csv'
    )


@main_bp.route('/preview-anki/<character>')
@login_required
def preview_anki(character):
    """Preview Anki card for a word."""
    deck_id = get_current_deck_id()
    words = db.get_words_by_user(current_user.id, deck_id)
    word = next((w for w in words if w.get('character') == character), None)
    
    if not word:
        return jsonify({'error': 'Word not found'}), 404
    
    # Generate Anki card HTML preview
    preview_html = dictionary_service.generate_anki_preview(word)
    
    return jsonify({
        'word': word,
        'preview_html': preview_html
    })


@main_bp.route('/api/tts/<text>')
def tts(text):
    """Text-to-speech endpoint."""
    audio_data = dictionary_service.get_tts_audio(text)
    
    if audio_data:
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/mpeg'
        )
    
    # Generate new audio
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='zh-cn')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_data = audio_buffer.getvalue()
        
        # Cache it
        dictionary_service._cache_tts(text, audio_data)
        
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/mpeg'
        )
    except Exception as e:
        current_app.logger.error(f"TTS error: {e}")
        return jsonify({'error': 'Failed to generate audio'}), 500


@main_bp.route('/help')
def help_page():
    """Help page."""
    return render_template('help.html')


@main_bp.route('/profile')
@login_required
def profile():
    """User profile."""
    stats = current_user.get_stats()
    decks = deck_manager.get_user_decks(current_user.id)
    return render_template('profile.html', stats=stats, decks=decks)
