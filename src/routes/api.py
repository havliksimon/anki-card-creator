"""API routes for TTS, stroke GIFs, and other services."""
import os
import io
import base64
from flask import Blueprint, request, send_file, jsonify, current_app
from gtts import gTTS
from src.models.database import db
from src.services.r2_storage import r2_storage

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Local in-memory cache for frequently used items
_local_cache = {}
LOCAL_CACHE_MAX_SIZE = 200


def get_from_local_cache(key):
    """Get item from in-memory cache."""
    return _local_cache.get(key)


def set_local_cache(key, value):
    """Set item in in-memory cache with LRU eviction."""
    if len(_local_cache) >= LOCAL_CACHE_MAX_SIZE:
        oldest_key = next(iter(_local_cache))
        del _local_cache[oldest_key]
    _local_cache[key] = value


@api_bp.route('/tts', methods=['GET'])
def tts_api():
    """Text-to-speech endpoint. Returns MP3 audio for Chinese text."""
    hanzi = request.args.get('hanzi')
    if not hanzi:
        return jsonify({'error': 'Missing hanzi parameter'}), 400
    
    cache_key = f"tts:{hanzi}"
    
    # Check in-memory cache first
    audio_data = get_from_local_cache(cache_key)
    if audio_data:
        return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
    
    # Priority 1: Try R2 storage (fastest, optimized for free tier)
    if r2_storage.is_available():
        try:
            audio_data = r2_storage.get_tts(hanzi)
            if audio_data:
                set_local_cache(cache_key, audio_data)
                return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
        except Exception as e:
            current_app.logger.warning(f"R2 TTS fetch failed: {e}")
    
    # Priority 2: Try Supabase
    try:
        result = db._client.get(f"/tts_cache?hanzi=eq.{hanzi}&limit=1").json()
        if result and len(result) > 0:
            audio_data = base64.b64decode(result[0]['audio'])
            # Store in R2 for future fast access
            if r2_storage.is_available():
                r2_storage.store_tts(hanzi, audio_data)
            set_local_cache(cache_key, audio_data)
            return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
    except Exception as e:
        current_app.logger.error(f"Supabase TTS fetch failed: {e}")
    
    # Priority 3: Generate using gTTS
    try:
        current_app.logger.info(f"Generating TTS for: {hanzi}")
        tts = gTTS(text=hanzi, lang='zh-cn')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_data = audio_buffer.getvalue()
        
        # Store in local cache
        set_local_cache(cache_key, audio_data)
        
        # Store in R2 (primary)
        if r2_storage.is_available():
            r2_storage.store_tts(hanzi, audio_data)
        
        # Also store in Supabase (backup)
        try:
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            db._client.post("/tts_cache", json={"hanzi": hanzi, "audio": encoded_audio})
        except Exception as e:
            current_app.logger.warning(f"Could not store TTS in Supabase: {e}")
        
        return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
    except Exception as e:
        current_app.logger.error(f"Error generating TTS: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/tts-url/<hanzi>')
def tts_url(hanzi):
    """Get direct URL to TTS audio (for Anki cards)."""
    if not hanzi:
        return jsonify({'error': 'Missing hanzi parameter'}), 400
    
    # Priority 1: Check if exists in R2
    if r2_storage.is_available():
        url = r2_storage.get_tts_url(hanzi)
        if url:
            return jsonify({'url': url, 'source': 'r2'})
    
    # Priority 2: Check Supabase
    try:
        result = db._client.get(f"/tts_cache?hanzi=eq.{hanzi}&limit=1").json()
        if result and len(result) > 0:
            # Return API endpoint URL
            tts_api_url = os.environ.get('TTS_API_URL', '/api/tts')
            return jsonify({'url': f"{tts_api_url}?hanzi={hanzi}", 'source': 'supabase'})
    except Exception as e:
        current_app.logger.error(f"Error checking Supabase: {e}")
    
    # Will need to be generated
    tts_api_url = os.environ.get('TTS_API_URL', '/api/tts')
    return jsonify({'url': f"{tts_api_url}?hanzi={hanzi}", 'source': 'generate'})


@api_bp.route('/stroke', methods=['GET'])
def stroke_api():
    """Stroke order GIF endpoint."""
    hanzi = request.args.get('hanzi')
    order = request.args.get('order', default=1, type=int)
    
    if not hanzi:
        return jsonify({'error': 'Missing hanzi parameter'}), 400
    
    cache_key = f"stroke:{hanzi}:{order}"
    
    # Check in-memory cache first
    gif_data = get_from_local_cache(cache_key)
    if gif_data:
        return send_file(io.BytesIO(gif_data), mimetype="image/gif")
    
    # Priority 1: Try R2 storage
    if r2_storage.is_available():
        try:
            gif_data = r2_storage.get_stroke_gif(hanzi, order)
            if gif_data:
                set_local_cache(cache_key, gif_data)
                return send_file(io.BytesIO(gif_data), mimetype="image/gif")
        except Exception as e:
            current_app.logger.warning(f"R2 stroke fetch failed: {e}")
    
    # Priority 2: Try Supabase
    try:
        result = db._client.get(f"/stroke_gifs?character=eq.{hanzi}&stroke_order=eq.{order}&limit=1").json()
        if result and len(result) > 0:
            gif_data = base64.b64decode(result[0]['gif_data'])
            # Store in R2 for future fast access
            if r2_storage.is_available():
                r2_storage.store_stroke_gif(hanzi, order, gif_data)
            set_local_cache(cache_key, gif_data)
            return send_file(io.BytesIO(gif_data), mimetype="image/gif")
    except Exception as e:
        current_app.logger.error(f"Supabase stroke fetch failed: {e}")
    
    return jsonify({'error': 'Stroke GIF not found'}), 404


@api_bp.route('/stroke-url/<character>/<int:order>')
def stroke_url(character, order):
    """Get direct URL to stroke GIF."""
    if not character:
        return jsonify({'error': 'Missing character parameter'}), 400
    
    # Priority 1: Check if exists in R2
    if r2_storage.is_available():
        url = r2_storage.get_stroke_url(character, order)
        if url:
            return jsonify({'url': url, 'source': 'r2'})
    
    # Priority 2: Check Supabase
    try:
        result = db._client.get(f"/stroke_gifs?character=eq.{character}&stroke_order=eq.{order}&limit=1").json()
        if result and len(result) > 0:
            return jsonify({'url': f"/api/stroke?hanzi={character}&order={order}", 'source': 'supabase'})
    except Exception as e:
        current_app.logger.error(f"Error checking Supabase: {e}")
    
    return jsonify({'url': None, 'error': 'Not found'}), 404


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'r2_available': r2_storage.is_available(),
        'supabase_connected': db._client is not None,
        'tts_cache_size': len([k for k in _local_cache.keys() if k.startswith('tts:')]),
        'stroke_cache_size': len([k for k in _local_cache.keys() if k.startswith('stroke:')])
    })


@api_bp.route('/migrate-to-r2', methods=['POST'])
def migrate_to_r2():
    """Admin endpoint to trigger migration of Supabase cache to R2."""
    from flask_login import current_user
    
    if not current_user.is_authenticated or not current_user.is_admin_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not r2_storage.is_available():
        return jsonify({'error': 'R2 not configured'}), 500
    
    # Get all TTS from Supabase
    try:
        result = db._client.get("/tts_cache?select=hanzi,audio&limit=1000").json()
        migrated = 0
        failed = 0
        
        for item in result:
            try:
                hanzi = item['hanzi']
                audio_data = base64.b64decode(item['audio'])
                
                # Store in R2
                if r2_storage.store_tts(hanzi, audio_data):
                    migrated += 1
                else:
                    failed += 1
            except Exception as e:
                current_app.logger.error(f"Error migrating {hanzi}: {e}")
                failed += 1
        
        return jsonify({
            'status': 'complete',
            'migrated': migrated,
            'failed': failed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
