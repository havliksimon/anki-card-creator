"""Cloudflare R2 Storage Service for optimized file storage."""
import os
import boto3
from botocore.config import Config
from typing import Optional, BinaryIO
import hashlib


class R2Storage:
    """Cloudflare R2 Storage wrapper for TTS audio and stroke GIFs."""
    
    def __init__(self):
        self.account_id = os.environ.get('R2_ACCOUNT_ID')
        self.access_key = os.environ.get('R2_ACCESS_KEY_ID')
        self.secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.environ.get('R2_BUCKET_NAME', 'anki-card-creator')
        
        # Public URL for serving files
        self.public_url = os.environ.get('R2_PUBLIC_URL', 
            'https://92170974e105eccaaeab64ed49d553e2.r2.cloudflarestorage.com/anki-card-creator')
        
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize S3-compatible client for R2."""
        if not all([self.account_id, self.access_key, self.secret_key]):
            print("R2 credentials not configured")
            return
        
        try:
            self._client = boto3.client(
                's3',
                endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version='s3v4'),
                region_name='auto'
            )
            print("R2 storage initialized")
        except Exception as e:
            print(f"Failed to initialize R2: {e}")
            self._client = None
    
    def is_available(self) -> bool:
        """Check if R2 is configured and available."""
        return self._client is not None
    
    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generate a storage key."""
        # Hash the identifier to create a safe key
        safe_id = hashlib.md5(identifier.encode()).hexdigest()[:16]
        return f"{prefix}/{safe_id}"
    
    def store_tts(self, hanzi: str, audio_data: bytes) -> Optional[str]:
        """Store TTS audio file and return public URL."""
        if not self.is_available():
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=audio_data,
                ContentType='audio/mpeg',
                Metadata={'hanzi': hanzi}
            )
            
            # Return the public URL
            return f"{self.public_url}/{key}"
        except Exception as e:
            print(f"Error storing TTS to R2: {e}")
            return None
    
    def get_tts(self, hanzi: str) -> Optional[bytes]:
        """Retrieve TTS audio file from R2."""
        if not self.is_available():
            return None
        
        try:
            key = self._get_key('tts', hanzi)
            response = self._client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self._client.exceptions.NoSuchKey:
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
            # Check if object exists
            self._client.head_object(Bucket=self.bucket_name, Key=key)
            return f"{self.public_url}/{key}"
        except:
            return None
    
    def store_stroke_gif(self, character: str, order: int, gif_data: bytes) -> Optional[str]:
        """Store stroke order GIF and return public URL."""
        if not self.is_available():
            return None
        
        try:
            key = f"strokes/{character}_{order}.gif"
            
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=gif_data,
                ContentType='image/gif',
                Metadata={'character': character, 'order': str(order)}
            )
            
            return f"{self.public_url}/{key}"
        except Exception as e:
            print(f"Error storing stroke GIF to R2: {e}")
            return None
    
    def get_stroke_gif(self, character: str, order: int) -> Optional[bytes]:
        """Retrieve stroke GIF from R2."""
        if not self.is_available():
            return None
        
        try:
            key = f"strokes/{character}_{order}.gif"
            response = self._client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self._client.exceptions.NoSuchKey:
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
            self._client.head_object(Bucket=self.bucket_name, Key=key)
            return f"{self.public_url}/{key}"
        except:
            return None
    
    def delete_tts(self, hanzi: str) -> bool:
        """Delete TTS file from R2."""
        if not self.is_available():
            return False
        
        try:
            key = self._get_key('tts', hanzi)
            self._client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception as e:
            print(f"Error deleting TTS from R2: {e}")
            return False
    
    def list_all_tts(self) -> list:
        """List all TTS files in R2."""
        if not self.is_available():
            return []
        
        try:
            response = self._client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='tts/'
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except Exception as e:
            print(f"Error listing TTS from R2: {e}")
            return []


# Global instance
r2_storage = R2Storage()
