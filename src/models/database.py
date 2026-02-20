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
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def get_all_words(self) -> List[Dict]:
        """Get all words from database (for admin operations)."""
        if self._client:
            response = self._client.get("/words?select=*&order=created_at.desc")
            return response.json()
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM words ORDER BY created_at DESC")
            rows = c.fetchall()
            conn.close()
            # Need to get column names
            return []
    
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
    
    def _serialize_for_json(self, obj):
        """Convert datetime and other objects to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user fields."""
        # Convert datetime objects to ISO format strings
        serialized_updates = {k: self._serialize_for_json(v) for k, v in updates.items()}
        
        if self._client:
            response = self._client.patch(f"/users?id=eq.{user_id}", json=serialized_updates)
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in serialized_updates.keys()])
            values = list(serialized_updates.values()) + [user_id]
            c.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            return True
    
    # ==================== Words ====================
    
    def get_words_by_user(self, user_id: str, deck_id: str = None) -> List[Dict]:
        """Get all words for a user/deck.
        
        Args:
            user_id: The user ID
            deck_id: Optional deck ID (e.g., USERID-1, USERID-2). If None, uses user_id
        """
        target_id = self._get_target_id(user_id, deck_id)
        
        if self._client:
            response = self._client.get(f"/words?user_id=eq.{target_id}&order=created_at.desc")
            return response.json()
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM words WHERE user_id = ? ORDER BY created_at DESC", (target_id,))
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
        import logging
        logger = logging.getLogger(__name__)
        
        if self._client:
            logger.info(f"create_word: creating word '{word_data.get('character')}' for user_id={word_data.get('user_id', '')[:20]}...")
            response = self._client.post("/words", json=word_data)
            logger.info(f"create_word: response status={response.status_code}")
            if response.status_code == 201:
                # Get the created word ID
                result = self._client.get(f"/words?character=eq.{word_data['character']}&user_id=eq.{word_data['user_id']}&limit=1")
                data = result.json()
                word_id = data[0]['id'] if data else None
                logger.info(f"create_word: success, word_id={word_id}")
                return word_id
            else:
                logger.error(f"create_word FAILED: status={response.status_code}, response={response.text[:500]}")
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
    
    def update_word(self, word_id: int, updates: Dict) -> bool:
        """Update a word."""
        serialized_updates = {k: self._serialize_for_json(v) for k, v in updates.items()}
        
        if self._client:
            response = self._client.patch(f"/words?id=eq.{word_id}", json=serialized_updates)
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in serialized_updates.keys()])
            values = list(serialized_updates.values()) + [word_id]
            c.execute(f"UPDATE words SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
            return True
    
    def _get_target_id(self, user_id: str, deck_id: str = None) -> str:
        """Helper to determine target user_id for a deck."""
        if not deck_id:
            return user_id
        
        # Handle deck_id format
        if '-' in deck_id:
            # Format: USERID-NUMBER
            parts = deck_id.rsplit('-', 1)
            try:
                deck_num = int(parts[1])
                if deck_num == 1:
                    return user_id
                else:
                    return deck_id  # Keep full format for deck N > 1
            except ValueError:
                return deck_id
        elif deck_id.isdigit():
            # Pure numeric deck ID
            deck_num = int(deck_id)
            if deck_num == 1:
                return user_id
            else:
                # For deck N > 1, use format USERID-N
                return f"{user_id}-{deck_id}"
        else:
            return deck_id
    
    def delete_word(self, word_id: int, user_id: str, deck_id: str = None) -> bool:
        """Delete a word."""
        target_id = self._get_target_id(user_id, deck_id)
        if self._client:
            response = self._client.delete(f"/words?id=eq.{word_id}&user_id=eq.{target_id}")
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("DELETE FROM words WHERE id = ? AND user_id = ?", (word_id, target_id))
            conn.commit()
            deleted = c.rowcount > 0
            conn.close()
            return deleted
    
    def delete_all_words(self, user_id: str, deck_id: str = None) -> bool:
        """Delete all words for a user/deck."""
        target_id = self._get_target_id(user_id, deck_id)
        if self._client:
            response = self._client.delete(f"/words?user_id=eq.{target_id}")
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("DELETE FROM words WHERE user_id = ?", (target_id,))
            conn.commit()
            conn.close()
            return True
    
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
    
    def create_pending_approval(self, user_id: str) -> bool:
        """Create a pending approval for a user.
        
        Args:
            user_id: The user ID to add to pending approvals
        """
        if self._client:
            data = {
                "user_id": user_id,
                "requested_at": datetime.utcnow().isoformat()
            }
            response = self._client.post("/pending_approvals", json=data)
            return response.status_code == 201
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO pending_approvals (user_id, requested_at)
                VALUES (?, datetime('now'))
            ''', (user_id,))
            conn.commit()
            conn.close()
            return True
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get all pending approvals with user details.
        
        Returns list of dicts with: user_id, email, telegram_id, telegram_username, requested_at
        """
        if self._client:
            try:
                # Get pending approvals with user details via join
                # Supabase doesn't support joins via REST API easily, so we fetch both and merge
                pending_resp = self._client.get("/pending_approvals?order=requested_at.desc")
                pending_list = pending_resp.json()
                
                if not isinstance(pending_list, list):
                    return []
                
                # Get all users to merge data
                users_resp = self._client.get("/users")
                users_list = users_resp.json() if users_resp.status_code == 200 else []
                users_dict = {u.get('id'): u for u in users_list if isinstance(u, dict)}
                
                # Merge pending with user data
                result = []
                for p in pending_list:
                    if isinstance(p, dict) and 'user_id' in p:
                        user = users_dict.get(p['user_id'], {})
                        result.append({
                            'user_id': p['user_id'],
                            'email': user.get('email'),
                            'telegram_id': user.get('telegram_id'),
                            'telegram_username': user.get('telegram_username'),
                            'requested_at': p.get('requested_at')
                        })
                return result
            except Exception as e:
                current_app.logger.error(f"Error getting pending approvals: {e}")
                return []
        else:
            # SQLite: join with users table
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                SELECT pa.user_id, u.email, u.telegram_id, u.telegram_username, pa.requested_at
                FROM pending_approvals pa
                JOIN users u ON pa.user_id = u.id
                ORDER BY pa.requested_at DESC
            ''')
            rows = c.fetchall()
            conn.close()
            return [{
                'user_id': row[0],
                'email': row[1],
                'telegram_id': row[2],
                'telegram_username': row[3],
                'requested_at': row[4]
            } for row in rows]
    
    def remove_pending_approval(self, user_id: str) -> bool:
        """Remove a pending approval by user_id."""
        if self._client:
            response = self._client.delete(f"/pending_approvals?user_id=eq.{user_id}")
            return response.status_code == 204
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("DELETE FROM pending_approvals WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return True
    
    def is_pending_approval(self, user_id: str) -> bool:
        """Check if a user has a pending approval."""
        if self._client:
            response = self._client.get(f"/pending_approvals?user_id=eq.{user_id}&limit=1")
            data = response.json()
            return len(data) > 0 if isinstance(data, list) else False
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT 1 FROM pending_approvals WHERE user_id = ?", (user_id,))
            result = c.fetchone()
            conn.close()
            return result is not None
    
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
    
    # ==================== Pending Approvals ====================
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get all pending approvals."""
        if self._client:
            try:
                response = self._client.get("/pending_approvals?order=created_at.desc")
                data = response.json()
                # Ensure we return a list
                if isinstance(data, list):
                    return data
                # If response is dict (error), return empty list
                return []
            except Exception as e:
                current_app.logger.error(f"Error getting pending approvals: {e}")
                return []
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM pending_approvals ORDER BY created_at DESC")
            rows = c.fetchall()
            conn.close()
            return [self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username',
                                           'password_hash', 'created_at']) for row in rows]
    
    def remove_pending_approval(self, approval_id: str) -> bool:
        """Remove a pending approval."""
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
    
    # ==================== Users Admin ====================
    
    def get_users(self) -> List[Dict]:
        """Get all users."""
        if self._client:
            try:
                response = self._client.get("/users?order=created_at.desc")
                data = response.json()
                # Ensure we return a list
                if isinstance(data, list):
                    return data
                return []
            except Exception as e:
                current_app.logger.error(f"Error getting users: {e}")
                return []
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = c.fetchall()
            conn.close()
            return [self._row_to_dict(row, ['id', 'email', 'telegram_id', 'telegram_username',
                                           'password_hash', 'is_active', 'is_admin', 'created_at', 'last_login']) for row in rows]
    
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
                    "total_users": len(users),
                    "total_words": len(words),
                    "active_users": len(users),  # Approximation
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
                "total_users": user_count,
                "total_words": word_count,
                "active_users": user_count,
                "mode": "sqlite"
            }


# Global database instance
db = Database()
