"""Main application routes."""
import io
import time
from urllib.parse import unquote
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app, session
from flask_login import login_required, current_user

from src.models.database import db
from src.models.user import User
from src.models.deck_manager import deck_manager
from src.services.dictionary_service import dictionary_service
from src.services.scraping_service import scraping_service
from src.utils.chinese_utils import (
    extract_chinese_words, chinese_to_styled_pinyin,
    get_coverage_percentage, get_hsk_progress
)

main_bp = Blueprint('main', __name__)

# Global dict to track progress for long-running operations
# Structure: {user_id: {'operation': 'add_word', 'stage': 'generating_audio', 'progress': 50, 'message': 'Generating audio...'}}
operation_status = {}


def get_current_deck_id():
    """Get current deck ID for the logged-in user."""
    if not current_user.is_authenticated:
        return None
    return deck_manager.get_current_deck_id(current_user.id)


def set_operation_status(user_id: str, operation: str, stage: str, progress: int, message: str):
    """Set operation status for a user."""
    operation_status[user_id] = {
        'operation': operation,
        'stage': stage,
        'progress': progress,
        'message': message,
        'timestamp': time.time()
    }


def clear_operation_status(user_id: str):
    """Clear operation status for a user."""
    if user_id in operation_status:
        del operation_status[user_id]


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
    return redirect(request.referrer or url_for('main.dashboard'))


@main_bp.route('/create-deck', methods=['POST'])
@login_required
def create_deck():
    """Create a new deck."""
    deck_number = request.form.get('deck_number', type=int)
    label = request.form.get('label', '').strip()
    
    if not deck_number or deck_number < 1:
        flash('Invalid deck number', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    deck_manager.create_deck(current_user.id, deck_number, label)
    deck_manager.set_current_deck(current_user.id, deck_number)
    flash(f'Created and switched to Deck {deck_number}', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))


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
    
    # URL decode the character (handle encoded Chinese characters)
    decoded_character = unquote(character)
    
    # Find word in current deck
    words = db.get_words_by_user(current_user.id, deck_id)
    word = next((w for w in words if w.get('character') == decoded_character), None)
    
    if not word:
        # Check if word exists in OTHER decks
        all_decks = deck_manager.get_user_decks(current_user.id)
        for deck in all_decks:
            other_deck_id = deck['deck_id']
            if other_deck_id != deck_id:
                other_words = db.get_words_by_user(current_user.id, other_deck_id)
                other_word = next((w for w in other_words if w.get('character') == decoded_character), None)
                if other_word:
                    deck_num = deck['deck_number']
                    flash(f'Word "{decoded_character}" is in Deck {deck_num}, not Deck {deck_manager.parse_deck_id(deck_id)[1]}. Switching...', 'info')
                    deck_manager.set_current_deck(current_user.id, deck_num)
                    return redirect(url_for('main.word_detail', character=character))
        
        flash(f'Word "{decoded_character}" not found in any of your decks.', 'error')
        return redirect(url_for('main.dictionary'))
    
    return render_template('word_detail.html', word=word)


@main_bp.route('/add-word', methods=['GET', 'POST'])
@login_required
def add_word():
    """Add new word."""
    deck_id = get_current_deck_id()
    
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
        
        # Store words to process and redirect to progress page
        session['pending_words'] = chinese_words
        return redirect(url_for('main.add_word_progress'))
    
    # Get deck info for display
    decks = deck_manager.get_user_decks(current_user.id)
    current_deck_num = deck_manager.parse_deck_id(deck_id)[1]
    current_deck_label = next((d.get('label', f'Deck {current_deck_num}') for d in decks if d.get('deck_id') == deck_id), f'Deck {current_deck_num}')
    
    return render_template('add_word.html',
                         deck_id=deck_id,
                         deck_label=current_deck_label,
                         deck_number=current_deck_num)


@main_bp.route('/add-word-progress')
@login_required
def add_word_progress():
    """Show progress page for adding words."""
    pending_words = session.get('pending_words', [])
    if not pending_words:
        flash('No words to add.', 'info')
        return redirect(url_for('main.add_word'))
    
    return render_template('word_progress.html',
                         words=pending_words,
                         operation='add',
                         title='Adding Words')


@main_bp.route('/api/add-word-process', methods=['POST'])
@login_required
def add_word_process():
    """Process adding words with progress tracking (AJAX endpoint)."""
    import threading
    
    pending_words = session.get('pending_words', [])
    if not pending_words:
        return jsonify({'error': 'No pending words'}), 400
    
    deck_id = get_current_deck_id()
    user_id = current_user.id
    
    def process_words():
        """Process words in background with progress updates."""
        added = []
        existing = []
        failed = []
        
        total = len(pending_words)
        
        for idx, word_text in enumerate(pending_words):
            # Check if word already exists in current deck
            set_operation_status(user_id, 'add_word', 'checking', 
                               int((idx / total) * 10), 
                               f'Checking "{word_text}"...')
            
            words_in_deck = db.get_words_by_user(user_id, deck_id)
            existing_word = next((w for w in words_in_deck if w.get('character') == word_text), None)
            
            if existing_word:
                existing.append(word_text)
                continue
            
            # Get word details with progress stages
            try:
                # Stage 1: Generating pinyin and styling
                set_operation_status(user_id, 'add_word', 'pinyin', 
                                   int((idx / total) * 100) + 10,
                                   f'Generating pinyin for "{word_text}"...')
                time.sleep(0.1)  # Small delay for UI update
                
                # Stage 2: Fetching examples
                set_operation_status(user_id, 'add_word', 'examples',
                                   int((idx / total) * 100) + 30,
                                   f'Fetching example sentences for "{word_text}"...')
                
                # Stage 3: Getting image
                set_operation_status(user_id, 'add_word', 'image',
                                   int((idx / total) * 100) + 50,
                                   f'Getting image for "{word_text}"...')
                
                # Stage 4: Generating audio
                set_operation_status(user_id, 'add_word', 'audio',
                                   int((idx / total) * 100) + 70,
                                   f'Generating audio for "{word_text}"...')
                
                # Actually get word details
                word_details = dictionary_service.get_word_details(word_text)
                word_details['user_id'] = deck_id
                
                # Stage 5: Saving to database
                set_operation_status(user_id, 'add_word', 'saving',
                                   int((idx / total) * 100) + 90,
                                   f'Saving "{word_text}" to database...')
                
                db.create_word(word_details)
                added.append(word_text)
                
            except Exception as e:
                current_app.logger.error(f"Error adding word {word_text}: {e}")
                failed.append(word_text)
        
        # Store results
        set_operation_status(user_id, 'add_word', 'complete', 100, 
                           f'Added {len(added)}, skipped {len(existing)}, failed {len(failed)}')
        
        session['add_results'] = {
            'added': added,
            'existing': existing,
            'failed': failed
        }
        
        # Clear pending words
        session.pop('pending_words', None)
    
    # Start processing in background
    thread = threading.Thread(target=process_words)
    thread.start()
    
    return jsonify({'status': 'started'})


@main_bp.route('/api/operation-status')
@login_required
def operation_status_api():
    """Get current operation status."""
    user_id = current_user.id
    status = operation_status.get(user_id, {})
    
    # Check if status is stale (older than 5 minutes)
    if status and time.time() - status.get('timestamp', 0) > 300:
        clear_operation_status(user_id)
        return jsonify({'stage': 'idle', 'progress': 0, 'message': 'No active operation'})
    
    return jsonify(status)


@main_bp.route('/refresh-word/<character>', methods=['GET', 'POST'])
@login_required
def refresh_word(character):
    """Refresh/regenerate a word's data."""
    # URL decode the character
    decoded_character = unquote(character)
    
    if request.method == 'GET':
        # Show confirmation/progress page
        return render_template('word_progress.html',
                             words=[decoded_character],
                             operation='refresh',
                             title=f'Refreshing "{decoded_character}"')
    
    # POST - start the refresh process via AJAX
    return redirect(url_for('main.refresh_word_progress', character=character))


@main_bp.route('/api/refresh-word-process/<character>', methods=['POST'])
@login_required
def refresh_word_process(character):
    """Process word refresh with progress tracking."""
    import threading
    
    decoded_character = unquote(character)
    deck_id = get_current_deck_id()
    user_id = current_user.id
    
    def process_refresh():
        """Refresh word in background with progress updates."""
        try:
            # Stage 1: Finding existing word
            set_operation_status(user_id, 'refresh_word', 'finding', 5,
                               f'Finding "{decoded_character}" in database...')
            
            words = db.get_words_by_user(user_id, deck_id)
            existing_word = next((w for w in words if w.get('character') == decoded_character), None)
            
            if not existing_word:
                set_operation_status(user_id, 'refresh_word', 'error', 0,
                                   f'Word "{decoded_character}" not found')
                return
            
            word_id = existing_word.get('id')
            
            # Stage 2: Generating pinyin
            set_operation_status(user_id, 'refresh_word', 'pinyin', 15,
                               f'Regenerating pinyin for "{decoded_character}"...')
            time.sleep(0.2)
            
            # Stage 3: Fetching examples from DeepSeek
            set_operation_status(user_id, 'refresh_word', 'examples', 35,
                               f'Fetching new example sentences for "{decoded_character}"...')
            
            # Stage 4: Getting image from Unsplash
            set_operation_status(user_id, 'refresh_word', 'image', 55,
                               f'Getting new image for "{decoded_character}"...')
            
            # Stage 5: Generating audio
            set_operation_status(user_id, 'refresh_word', 'audio', 75,
                               f'Regenerating audio for "{decoded_character}"...')
            
            # Get fresh word details
            word_details = dictionary_service.get_word_details(decoded_character)
            word_details['user_id'] = deck_id
            
            # Stage 6: Saving to database
            set_operation_status(user_id, 'refresh_word', 'saving', 90,
                               f'Saving updated "{decoded_character}"...')
            
            # Delete old word and create new one
            db.delete_word(word_id, user_id, deck_id)
            db.create_word(word_details)
            
            set_operation_status(user_id, 'refresh_word', 'complete', 100,
                               f'Successfully refreshed "{decoded_character}"!')
            
        except Exception as e:
            current_app.logger.error(f"Error refreshing word {decoded_character}: {e}")
            set_operation_status(user_id, 'refresh_word', 'error', 0,
                               f'Error refreshing "{decoded_character}": {str(e)}')
    
    # Start processing in background
    thread = threading.Thread(target=process_refresh)
    thread.start()
    
    return jsonify({'status': 'started'})


@main_bp.route('/delete-word/<int:word_id>', methods=['POST'])
@login_required
def delete_word(word_id):
    """Delete a word."""
    deck_id = get_current_deck_id()
    db.delete_word(word_id, current_user.id, deck_id)
    flash('Word deleted', 'success')
    return redirect(request.referrer or url_for('main.dictionary'))


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
