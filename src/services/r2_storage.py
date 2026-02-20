"""Cloudflare R2 Storage Service for optimized file storage."""
import os
import requests
from typing import Optional, BinaryIO, Tuple
import hashlib
import base64
import hmac
import datetime
from urllib.parse import quote


class R2Storage:
    """Cloudflare R2 Storage wrapper using S3-compatible API."""
    
    def __init__(self):
        self.account_id = os.environ.get('R2_ACCOUNT_ID')
        self.access_key_id = os.environ.get('R2_ACCESS_KEY_ID')
        self.secret_access_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.environ.get('R2_BUCKET_NAME', 'anki-card-creator')
        
        # Public URL for serving files (direct R2 public URL)
        self.public_url = os.environ.get('R2_PUBLIC_URL', '').rstrip('/')
        if not self.public_url and self.account_id:
            self.public_url = f'https://{self.account_id}.r2.cloudflarestorage.com/{self.bucket_name}'
        
        # R2 S3-compatible endpoint
        self.endpoint = f'https://{self.account_id}.r2.cloudflarestorage.com' if self.account_id else None
        
        self._session = None
        self._init_client()
    
    def _init_client(self):
        """Initialize HTTP session for R2 API."""
        if not all([self.account_id, self.access_key_id, self.secret_access_key]):
            print("R2 credentials not fully configured (need account_id, access_key_id, secret_access_key)")
            return
        
        try:
            self._session = requests.Session()
            print("R2 storage initialized with S3-compatible API")
        except Exception as e:
            print(f"Failed to initialize R2: {e}")
            self._session = None
    
    def is_available(self) -> bool:
        """Check if R2 is configured and available."""
        return self._session is not None and self.endpoint is not None
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generate a storage key."""
        safe_id = hashlib.md5(identifier.encode()).hexdigest()[:16]
        return f"{prefix}/{safe_id}.mp3"
    
    def _aws_signature(self, method: str, key: str, content_type: str = '', payload_hash: str = 'UNSIGNED-PAYLOAD') -> dict:
        """Generate AWS Signature Version 4 headers."""
        now = datetime.datetime.utcnow()
        date_stamp = now.strftime('%Y%m%d')
        time_stamp = now.strftime('%Y%m%dT%H%M%SZ')
        region = 'auto'  # R2 uses 'auto' as region
        service = 's3'
        
        # Create canonical request
        canonical_uri = f'/{self.bucket_name}/{key}'
        canonical_querystring = ''
        
        # Headers
        host = f'{self.account_id}.r2.cloudflarestorage.com'
        canonical_headers = f'host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{time_stamp}\n'
        signed_headers = 'host;x-amz-content-sha256;x-amz-date'
        
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = f"{algorithm}\n{time_stamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # Calculate signature
        k_date = hmac.new(f'AWS4{self.secret_access_key}'.encode(), date_stamp.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, 'aws4_request'.encode(), hashlib.sha256).digest()
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
        
        # Authorization header
        auth_header = f"{algorithm} Credential={self.access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            'Authorization': auth_header,
            'x-amz-date': time_stamp,
            'x-amz-content-sha256': payload_hash,
            'Host': host
        }
    
    def _get_object_url(self, key: str) -> str:
        """Get the full URL for an object."""
        return f"{self.endpoint}/{self.bucket_name}/{key}"
    
    def store_tts(self, hanzi: str, audio_data: bytes) -> Optional[str]:
        """Store TTS audio file and return public URL."""
        if not self.is_available():
            print("R2 not available for store_tts")
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            url = self._get_object_url(key)
            
            # Calculate content hash
            content_hash = hashlib.sha256(audio_data).hexdigest()
            
            # Get AWS signature headers
            headers = self._aws_signature('PUT', key, 'audio/mpeg', content_hash)
            headers['Content-Type'] = 'audio/mpeg'
            headers['Content-Length'] = str(len(audio_data))
            
            response = self._session.put(
                url,
                data=audio_data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                public_url = f"{self.public_url}/{key}"
                print(f"Stored TTS to R2: {public_url}")
                return public_url
            else:
                print(f"R2 store TTS error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"Error storing TTS to R2: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_tts(self, hanzi: str) -> Optional[bytes]:
        """Retrieve TTS audio file from R2."""
        if not self.is_available():
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            url = self._get_object_url(key)
            
            headers = self._aws_signature('GET', key)
            
            response = self._session.get(
                url,
                headers=headers,
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
            headers = self._aws_signature('HEAD', key)
            
            response = self._session.head(
                url,
                headers=headers,
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
            
            content_hash = hashlib.sha256(gif_data).hexdigest()
            headers = self._aws_signature('PUT', key, 'image/gif', content_hash)
            headers['Content-Type'] = 'image/gif'
            headers['Content-Length'] = str(len(gif_data))
            
            response = self._session.put(
                url,
                data=gif_data,
                headers=headers,
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
    
    def get_stroke_url(self, character: str, order: int) -> Optional[str]:
        """Get public URL for stroke GIF (if it exists)."""
        if not self.is_available():
            return None
        
        try:
            key = f"strokes/{character}_{order}.gif"
            url = self._get_object_url(key)
            
            headers = self._aws_signature('HEAD', key)
            
            response = self._session.head(
                url,
                headers=headers,
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
            
            headers = self._aws_signature('DELETE', key)
            
            response = self._session.delete(
                url,
                headers=headers,
                timeout=30
            )
            
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Error deleting TTS from R2: {e}")
            return False


# Global instance
r2_storage = R2Storage()
