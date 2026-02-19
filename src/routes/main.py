"""Main application routes."""
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from flask_login import login_required, current_user

from src.models.database import db
from src.models.user import User
from src.services.dictionary_service import dictionary_service
from src.utils.chinese_utils import (
    extract_chinese_words, chinese_to_styled_pinyin,
    get_coverage_percentage, get_hsk_progress
)

main_bp = Blueprint('main', __name__)


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
    words = current_user.get_words()
    stats = current_user.get_stats()
    
    # Calculate progress
    char_count = stats.get('total_words', 0)
    coverage = get_coverage_percentage(char_count)
    hsk_progress = get_hsk_progress(char_count)
    
    return render_template('dashboard.html', 
                         words=words[:10],  # Show recent 10
                         stats=stats,
                         coverage=coverage,
                         hsk_progress=hsk_progress,
                         total_count=len(words))


@main_bp.route('/dictionary')
@login_required
def dictionary():
    """View all saved words."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    words = current_user.get_words()
    total = len(words)
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_words = words[start:end]
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('dictionary.html',
                         words=paginated_words,
                         page=page,
                         total_pages=total_pages,
                         total=total)


@main_bp.route('/word/<character>')
@login_required
def word_detail(character):
    """View word details."""
    word = db.get_word(character, current_user.id)
    
    if not word:
        flash('Word not found.', 'error')
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
        
        added = []
        existing = []
        
        for word_text in chinese_words:
            # Check if word already exists
            existing_word = db.get_word(word_text, current_user.id)
            
            if existing_word:
                existing.append(word_text)
                continue
            
            # Get word details
            try:
                word_details = dictionary_service.get_word_details(word_text)
                word_details['user_id'] = current_user.id
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


@main_bp.route('/delete-word/<character>', methods=['POST'])
@login_required
def delete_word(character):
    """Delete a word."""
    db.delete_word(character, current_user.id)
    flash(f'Deleted: {character}', 'success')
    return redirect(url_for('main.dictionary'))


@main_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all():
    """Clear all words."""
    db.delete_all_words(current_user.id)
    flash('All words have been cleared.', 'success')
    return redirect(url_for('main.dictionary'))


@main_bp.route('/export')
@login_required
def export_csv():
    """Export words to CSV."""
    csv_data = dictionary_service.generate_csv(current_user.id)
    
    return send_file(
        io.BytesIO(csv_data),
        mimetype='text/csv',
        as_attachment=True,
        download_name='anki_export.csv'
    )


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
    return render_template('profile.html', stats=stats)
