"""Database connection and operations."""
import os
import sqlite3
import httpx
from typing import Optional, List, Dict, Any
from flask import current_app
import json
from datetime import datetime


class Database:
    """Database wrapper for Supabase or local SQLite."""
    
    def __init__(self):
        self._supabase_url: Optional[str] = None
        self._supabase_key: Optional[str] = None
        self._client: Optional[httpx.Client] = None
        self._local_db_path = 'local.db'
    
    def init_app(self, app):
        """Initialize database connection."""
        if not app.config.get('USE_LOCAL_DB'):
            try:
                self._supabase_url = app.config['SUPABASE_URL']
                self._supabase_key = app.config['SUPABASE_SERVICE_KEY']
                self._client = httpx.Client(
                    base_url=f"{self._supabase_url}/rest/v1",
                    headers={
                        "apikey": self._supabase_key,
                        "Authorization": f"Bearer {self._supabase_key}",
                        "Content-Type": "application/json"
                    }
                )
                # Test connection
                response = self._client.get("/words?limit=1")
                response.raise_for_status()
                app.logger.info("Connected to Supabase successfully")
            except Exception as e:
                app.logger.warning(f"Failed to connect to Supabase: {e}. Using local SQLite.")
                self._client = None
        
        if self._client is None or app.config.get('USE_LOCAL_DB'):
            self._init_local_db()
    
    def _init_local_db(self):
        """Initialize local SQLite database."""
        conn = sqlite3.connect(self._local_db_path)
        c = conn.cursor()
        
        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                telegram_id TEXT UNIQUE,
                telegram_username TEXT,
                password_hash TEXT,
                is_active BOOLEAN DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Words table
        c.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character TEXT NOT NULL,
                user_id TEXT NOT NULL,
                pinyin TEXT,
                translation TEXT,
                meaning TEXT,
                stroke_gifs TEXT,
                pronunciation TEXT,
                exemplary_image TEXT,
                anki_usage_examples TEXT,
                real_usage_examples TEXT,
                styled_term TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(character, user_id)
            )
        ''')
        
        # Example sentences table
        c.execute('''
            CREATE TABLE IF NOT EXISTS example_sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                chinese TEXT NOT NULL,
                pinyin TEXT,
                english TEXT,
                FOREIGN KEY (word_id) REFERENCES words(id)
            )
        ''')
        
        # Pending approvals table
        c.execute('''
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                telegram_id TEXT,
                telegram_username TEXT,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Verification tokens table
        c.execute('''
            CREATE TABLE IF NOT EXISTS verification_tokens (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                type TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ==================== Users ====================
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        if self._client:
            response = self._client.get(f"/users?email=eq.{email}&limit=1")
            data = response.json()
            return data[0] if data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = c.fetchone()
            conn.close()
            if row:
                return self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username', 
                                               'password_hash', 'is_active', 'is_admin', 'created_at', 'last_login'])
            return None
    
    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[Dict]:
        """Get user by Telegram ID."""
        if self._client:
            response = self._client.get(f"/users?telegram_id=eq.{telegram_id}&limit=1")
            data = response.json()
            return data[0] if data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = c.fetchone()
            conn.close()
            if row:
                return self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username',
                                               'password_hash', 'is_active', 'is_admin', 'created_at', 'last_login'])
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        if self._client:
            response = self._client.get(f"/users?id=eq.{user_id}&limit=1")
            data = response.json()
            return data[0] if data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = c.fetchone()
            conn.close()
            if row:
                return self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username',
                                               'password_hash', 'is_active', 'is_admin', 'created_at', 'last_login'])
            return None
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics."""
        if self._client:
            try:
                words = self._client.get(f"/words?user_id=eq.{user_id}&select=id").json()
                return {"word_count": len(words)}
            except:
                return {"word_count": 0}
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
            count = c.fetchone()[0]
            conn.close()
            return {"word_count": count}
    
    def create_user(self, user_id: str, email: str, password_hash: str, 
                    telegram_id: str = None, telegram_username: str = None,
                    is_active: bool = False, is_admin: bool = False) -> bool:
        """Create a new user."""
        if self._client:
            data = {
                "id": user_id,
                "email": email,
                "password_hash": password_hash,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "is_active": is_active,
                "is_admin": is_admin,
                "created_at": datetime.utcnow().isoformat()
            }
            response = self._client.post("/users", json=data)
            return response.status_code == 201
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO users (id, email, password_hash, telegram_id, telegram_username, is_active, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, email, password_hash, telegram_id, telegram_username, is_active, is_admin))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user fields."""
        if self._client:
            response = self._client.patch(f"/users?id=eq.{user_id}", json=updates)
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [user_id]
            c.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            return True
    
    # ==================== Words ====================
    
    def get_words_by_user(self, user_id: str) -> List[Dict]:
        """Get all words for a user."""
        if self._client:
            response = self._client.get(f"/words?user_id=eq.{user_id}&order=created_at.desc")
            return response.json()
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM words WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = c.fetchall()
            conn.close()
            return [self._row_to_dict(row, ['id', 'character', 'user_id', 'pinyin', 'translation', 
                                           'meaning', 'stroke_gifs', 'pronunciation', 'exemplary_image',
                                           'anki_usage_examples', 'real_usage_examples', 'styled_term', 'created_at']) 
                    for row in rows]
    
    def get_word(self, word_id: int) -> Optional[Dict]:
        """Get a word by ID."""
        if self._client:
            response = self._client.get(f"/words?id=eq.{word_id}&limit=1")
            data = response.json()
            return data[0] if data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM words WHERE id = ?", (word_id,))
            row = c.fetchone()
            conn.close()
            if row:
                return self._row_to_dict(row, ['id', 'character', 'user_id', 'pinyin', 'translation',
                                               'meaning', 'stroke_gifs', 'pronunciation', 'exemplary_image',
                                               'anki_usage_examples', 'real_usage_examples', 'styled_term', 'created_at'])
            return None
    
    def create_word(self, word_data: Dict) -> Optional[int]:
        """Create a new word."""
        if self._client:
            response = self._client.post("/words", json=word_data)
            if response.status_code == 201:
                # Get the created word ID
                result = self._client.get(f"/words?character=eq.{word_data['character']}&user_id=eq.{word_data['user_id']}&limit=1")
                data = result.json()
                return data[0]['id'] if data else None
            return None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO words (character, user_id, pinyin, translation, meaning, stroke_gifs, 
                                  pronunciation, exemplary_image, anki_usage_examples, real_usage_examples, styled_term)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (word_data.get('character'), word_data.get('user_id'), word_data.get('pinyin'),
                  word_data.get('translation'), word_data.get('meaning'), word_data.get('stroke_gifs'),
                  word_data.get('pronunciation'), word_data.get('exemplary_image'),
                  word_data.get('anki_usage_examples'), word_data.get('real_usage_examples'),
                  word_data.get('styled_term')))
            word_id = c.lastrowid
            conn.commit()
            conn.close()
            return word_id
    
    def delete_word(self, word_id: int, user_id: str) -> bool:
        """Delete a word."""
        if self._client:
            response = self._client.delete(f"/words?id=eq.{word_id}&user_id=eq.{user_id}")
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("DELETE FROM words WHERE id = ? AND user_id = ?", (word_id, user_id))
            conn.commit()
            deleted = c.rowcount > 0
            conn.close()
            return deleted
    
    # ==================== Example Sentences ====================
    
    def get_example_sentences(self, word_id: int) -> List[Dict]:
        """Get example sentences for a word."""
        if self._client:
            response = self._client.get(f"/example_sentences?word_id=eq.{word_id}")
            return response.json()
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM example_sentences WHERE word_id = ?", (word_id,))
            rows = c.fetchall()
            conn.close()
            return [self._row_to_dict(row, ['id', 'word_id', 'chinese', 'pinyin', 'english']) for row in rows]
    
    def add_example_sentence(self, word_id: int, chinese: str, pinyin: str = None, english: str = None) -> bool:
        """Add an example sentence."""
        if self._client:
            data = {"word_id": word_id, "chinese": chinese, "pinyin": pinyin, "english": english}
            response = self._client.post("/example_sentences", json=data)
            return response.status_code == 201
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO example_sentences (word_id, chinese, pinyin, english)
                VALUES (?, ?, ?, ?)
            ''', (word_id, chinese, pinyin, english))
            conn.commit()
            conn.close()
            return True
    
    # ==================== Pending Approvals ====================
    
    def create_pending_approval(self, approval_id: str, email: str, password_hash: str,
                                telegram_id: str = None, telegram_username: str = None) -> bool:
        """Create a pending approval."""
        if self._client:
            data = {
                "id": approval_id,
                "email": email,
                "password_hash": password_hash,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "created_at": datetime.utcnow().isoformat()
            }
            response = self._client.post("/pending_approvals", json=data)
            return response.status_code == 201
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO pending_approvals (id, email, password_hash, telegram_id, telegram_username)
                VALUES (?, ?, ?, ?, ?)
            ''', (approval_id, email, password_hash, telegram_id, telegram_username))
            conn.commit()
            conn.close()
            return True
    
    def get_pending_approval(self, approval_id: str) -> Optional[Dict]:
        """Get a pending approval."""
        if self._client:
            response = self._client.get(f"/pending_approvals?id=eq.{approval_id}&limit=1")
            data = response.json()
            return data[0] if data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM pending_approvals WHERE id = ?", (approval_id,))
            row = c.fetchone()
            conn.close()
            if row:
                return self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username', 
                                               'password_hash', 'created_at'])
            return None
    
    def delete_pending_approval(self, approval_id: str) -> bool:
        """Delete a pending approval."""
        if self._client:
            response = self._client.delete(f"/pending_approvals?id=eq.{approval_id}")
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("DELETE FROM pending_approvals WHERE id = ?", (approval_id,))
            conn.commit()
            conn.close()
            return True
    
    def get_all_pending_approvals(self) -> List[Dict]:
        """Get all pending approvals."""
        if self._client:
            response = self._client.get("/pending_approvals?order=created_at.desc")
            return response.json()
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM pending_approvals ORDER BY created_at DESC")
            rows = c.fetchall()
            conn.close()
            return [self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username',
                                           'password_hash', 'created_at']) for row in rows]
    
    # ==================== Verification Tokens ====================
    
    def create_verification_token(self, token_id: str, email: str, token: str, 
                                   token_type: str, expires_at: datetime) -> bool:
        """Create a verification token."""
        if self._client:
            data = {
                "id": token_id,
                "email": email,
                "token": token,
                "type": token_type,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            response = self._client.post("/verification_tokens", json=data)
            return response.status_code == 201
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO verification_tokens (id, email, token, type, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (token_id, email, token, token_type, expires_at))
            conn.commit()
            conn.close()
            return True
    
    def get_verification_token(self, token: str, token_type: str) -> Optional[Dict]:
        """Get a verification token."""
        if self._client:
            response = self._client.get(
                f"/verification_tokens?token=eq.{token}&type=eq.{token_type}&limit=1"
            )
            data = response.json()
            return data[0] if data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM verification_tokens WHERE token = ? AND type = ?", (token, token_type))
            row = c.fetchone()
            conn.close()
            if row:
                return self._row_to_dict(row, ['id', 'email', 'token', 'type', 'expires_at', 'created_at'])
            return None
    
    def delete_verification_token(self, token_id: str) -> bool:
        """Delete a verification token."""
        if self._client:
            response = self._client.delete(f"/verification_tokens?id=eq.{token_id}")
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("DELETE FROM verification_tokens WHERE id = ?", (token_id,))
            conn.commit()
            conn.close()
            return True
    
    # ==================== Helper ====================
    
    def _row_to_dict(self, row: tuple, columns: List[str]) -> Dict:
        """Convert SQLite row to dict."""
        return {columns[i]: row[i] for i in range(len(columns))}
    
    def get_stats(self) -> Dict:
        """Get database stats."""
        if self._client:
            try:
                users = self._client.get("/users?select=id").json()
                words = self._client.get("/words?select=id").json()
                return {
                    "users": len(users),
                    "words": len(words),
                    "mode": "supabase"
                }
            except:
                return {"users": 0, "words": 0, "mode": "supabase_error"}
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM words")
            word_count = c.fetchone()[0]
            conn.close()
            return {
                "users": user_count,
                "words": word_count,
                "mode": "sqlite"
            }


# Global database instance
db = Database()
