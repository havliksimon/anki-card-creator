"""API routes for TTS, stroke GIFs, and other services."""
import os
import io
import base64
from flask import Blueprint, request, send_file, jsonify, current_app
from gtts import gTTS
from src.models.database import db

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Local in-memory cache for frequently used items (reduces Supabase calls)
_local_cache = {}
LOCAL_CACHE_MAX_SIZE = 200


def get_from_local_cache(key):
    """Get item from in-memory cache."""
    return _local_cache.get(key)


def set_local_cache(key, value):
    """Set item in in-memory cache with LRU eviction."""
    if len(_local_cache) >= LOCAL_CACHE_MAX_SIZE:
        # Remove oldest item
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
    
    # Check in-memory cache first (fastest)
    audio_data = get_from_local_cache(cache_key)
    if audio_data:
        return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
    
    # Try to get from Supabase
    try:
        result = db._client.get(f"/tts_cache?hanzi=eq.{hanzi}&limit=1").json()
        if result and len(result) > 0:
            # Supabase returns base64 encoded bytea
            audio_data = base64.b64decode(result[0]['audio'])
            set_local_cache(cache_key, audio_data)
            return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
    except Exception as e:
        current_app.logger.error(f"Error fetching TTS from Supabase: {e}")
    
    # Generate using gTTS if not found
    try:
        current_app.logger.info(f"Generating TTS for: {hanzi}")
        tts = gTTS(text=hanzi, lang='zh-cn')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_data = audio_buffer.getvalue()
        
        # Store in local cache
        set_local_cache(cache_key, audio_data)
        
        # Store in Supabase for future use (fire and forget)
        try:
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
            db._client.post("/tts_cache", json={
                "hanzi": hanzi,
                "audio": encoded_audio
            })
        except Exception as e:
            current_app.logger.warning(f"Could not store TTS in Supabase: {e}")
        
        return send_file(io.BytesIO(audio_data), mimetype="audio/mpeg")
    except Exception as e:
        current_app.logger.error(f"Error generating TTS: {e}")
        return jsonify({'error': str(e)}), 500


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
    
    # Try to get from Supabase
    try:
        result = db._client.get(f"/stroke_gifs?character=eq.{hanzi}&stroke_order=eq.{order}&limit=1").json()
        if result and len(result) > 0:
            gif_data = base64.b64decode(result[0]['gif_data'])
            set_local_cache(cache_key, gif_data)
            return send_file(io.BytesIO(gif_data), mimetype="image/gif")
    except Exception as e:
        current_app.logger.error(f"Error fetching stroke GIF from Supabase: {e}")
    
    return jsonify({'error': 'Stroke GIF not found'}), 404


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'supabase_connected': db._client is not None
    })
