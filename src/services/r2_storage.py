"""Cloudflare R2 Storage Service for optimized file storage."""
import os
import requests
from typing import Optional, BinaryIO, Tuple
import hashlib


class R2Storage:
    """Cloudflare R2 Storage wrapper using native HTTP API for R2 API Tokens."""
    
    def __init__(self):
        self.account_id = os.environ.get('R2_ACCOUNT_ID')
        self.api_token = os.environ.get('R2_ACCESS_KEY_ID')  # R2 API Token
        self.bucket_name = os.environ.get('R2_BUCKET_NAME', 'anki-card-creator')
        
        # Public URL for serving files
        self.public_url = os.environ.get('R2_PUBLIC_URL', 
            'https://92170974e105eccaaeab64ed49d553e2.r2.cloudflarestorage.com/anki-card-creator')
        
        # R2 S3-compatible endpoint
        self.endpoint = f'https://{self.account_id}.r2.cloudflarestorage.com' if self.account_id else None
        
        self._session = None
        self._init_client()
    
    def _init_client(self):
        """Initialize HTTP session for R2 API."""
        if not all([self.account_id, self.api_token, self.endpoint]):
            print("R2 credentials not configured")
            return
        
        try:
            self._session = requests.Session()
            print("R2 storage initialized")
        except Exception as e:
            print(f"Failed to initialize R2: {e}")
            self._session = None
    
    def is_available(self) -> bool:
        """Check if R2 is configured and available."""
        return self._session is not None and self.endpoint is not None
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generate a storage key."""
        safe_id = hashlib.md5(identifier.encode()).hexdigest()[:16]
        return f"{prefix}/{safe_id}"
    
    def _get_object_url(self, key: str) -> str:
        """Get the full URL for an object."""
        return f"{self.endpoint}/{self.bucket_name}/{key}"
    
    def _headers(self, content_type: str = 'application/octet-stream') -> dict:
        """Get authentication headers."""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': content_type
        }
    
    def store_tts(self, hanzi: str, audio_data: bytes) -> Optional[str]:
        """Store TTS audio file and return public URL."""
        if not self.is_available():
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            url = self._get_object_url(key)
            
            response = self._session.put(
                url,
                data=audio_data,
                headers=self._headers('audio/mpeg'),
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                return f"{self.public_url}/{key}"
            else:
                print(f"R2 store TTS error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error storing TTS to R2: {e}")
            return None
    
    def get_tts(self, hanzi: str) -> Optional[bytes]:
        """Retrieve TTS audio file from R2."""
        if not self.is_available():
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            url = self._get_object_url(key)
            
            response = self._session.get(
                url,
                headers={'Authorization': f'Bearer {self.api_token}'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Error retrieving TTS from R2: {e}")
            return None
    
    def get_tts_url(self, hanzi: str) -> Optional[str]:
        """Get public URL for TTS file (if it exists)."""
        if not self.is_available():
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            url = self._get_object_url(key)
            
            # Check if object exists (HEAD request)
            response = self._session.head(
                url,
                headers={'Authorization': f'Bearer {self.api_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return f"{self.public_url}/{key}"
            return None
        except Exception as e:
            return None
    
    def store_stroke_gif(self, character: str, order: int, gif_data: bytes) -> Optional[str]:
        """Store stroke order GIF and return public URL."""
        if not self.is_available():
            return None
        
        try:
            key = f"strokes/{character}_{order}.gif"
            url = self._get_object_url(key)
            
            response = self._session.put(
                url,
                data=gif_data,
                headers=self._headers('image/gif'),
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                return f"{self.public_url}/{key}"
            else:
                print(f"R2 store stroke error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error storing stroke GIF to R2: {e}")
            return None
    
    def get_stroke_gif(self, character: str, order: int) -> Optional[bytes]:
        """Retrieve stroke GIF from R2."""
        if not self.is_available():
            return None
        
        try:
            key = f"strokes/{character}_{order}.gif"
            url = self._get_object_url(key)
            
            response = self._session.get(
                url,
                headers={'Authorization': f'Bearer {self.api_token}'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Error retrieving stroke GIF from R2: {e}")
            return None
    
    def get_stroke_url(self, character: str, order: int) -> Optional[str]:
        """Get public URL for stroke GIF (if it exists)."""
        if not self.is_available():
            return None
        
        try:
            key = f"strokes/{character}_{order}.gif"
            url = self._get_object_url(key)
            
            response = self._session.head(
                url,
                headers={'Authorization': f'Bearer {self.api_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return f"{self.public_url}/{key}"
            return None
        except Exception as e:
            return None
    
    def delete_tts(self, hanzi: str) -> bool:
        """Delete TTS file from R2."""
        if not self.is_available():
            return False
        
        try:
            key = self._get_key('tts', hanzi)
            url = self._get_object_url(key)
            
            response = self._session.delete(
                url,
                headers={'Authorization': f'Bearer {self.api_token}'},
                timeout=30
            )
            
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Error deleting TTS from R2: {e}")
            return False
    
    def list_all_tts(self) -> list:
        """List all TTS files in R2."""
        if not self.is_available():
            return []
        
        try:
            # R2 doesn't have a simple list API via HTTP, would need S3 ListObjectsV2
            # For now return empty list
            return []
        except Exception as e:
            print(f"Error listing TTS from R2: {e}")
            return []


# Global instance
r2_storage = R2Storage()
