"""Database connection and operations."""
import os
import sqlite3
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from flask import current_app
import json
from datetime import datetime


class Database:
    """Database wrapper for Supabase or local SQLite."""
    
    def __init__(self):
        self._supabase: Optional[Client] = None
        self._local_db_path = 'local.db'
    
    def init_app(self, app):
        """Initialize database connection."""
        if not app.config.get('USE_LOCAL_DB'):
            try:
                self._supabase = create_client(
                    app.config['SUPABASE_URL'],
                    app.config['SUPABASE_SERVICE_KEY']
                )
                self._init_tables()
            except Exception as e:
                app.logger.warning(f"Failed to connect to Supabase: {e}. Using local SQLite.")
                self._supabase = None
        
        if self._supabase is None or app.config.get('USE_LOCAL_DB'):
            self._init_local_db()
    
    def _init_tables(self):
        """Initialize Supabase tables if needed."""
        # Tables should be created via Supabase dashboard or migrations
        pass
    
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
                chinese_sentence TEXT UNIQUE,
                styled_pinyin TEXT,
                styled_hanzi TEXT,
                translation TEXT,
                source_name TEXT,
                source_link TEXT,
                word_list TEXT
            )
        ''')
        
        # Pending approvals table
        c.execute('''
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Verification tokens table
        c.execute('''
            CREATE TABLE IF NOT EXISTS verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                token_type TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # TTS cache table
        c.execute('''
            CREATE TABLE IF NOT EXISTS tts_cache (
                hanzi TEXT PRIMARY KEY,
                audio BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Stroke GIFs cache table
        c.execute('''
            CREATE TABLE IF NOT EXISTS stroke_gifs (
                character TEXT NOT NULL,
                stroke_order INTEGER NOT NULL,
                gif_data BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character, stroke_order)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    @property
    def is_supabase(self) -> bool:
        """Check if using Supabase."""
        return self._supabase is not None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        if self.is_supabase:
            try:
                result = self._supabase.table('users').select('*').eq('id', user_id).limit(1).execute()
                return result.data[0] if result.data else None
            except:
                return None
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        if self.is_supabase:
            try:
                result = self._supabase.table('users').select('*').eq('email', email).limit(1).execute()
                return result.data[0] if result.data else None
            except:
                return None
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
    
    def get_user_by_telegram(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID."""
        if self.is_supabase:
            try:
                result = self._supabase.table('users').select('*').eq('telegram_id', telegram_id).limit(1).execute()
                return result.data[0] if result.data else None
            except:
                return None
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new user."""
        if self.is_supabase:
            result = self._supabase.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO users (id, email, telegram_id, telegram_username, password_hash, is_active, is_admin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data.get('id'),
                user_data.get('email'),
                user_data.get('telegram_id'),
                user_data.get('telegram_username'),
                user_data.get('password_hash'),
                user_data.get('is_active', False),
                user_data.get('is_admin', False)
            ))
            conn.commit()
            conn.close()
            return self.get_user(user_data.get('id'))
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user."""
        if self.is_supabase:
            result = self._supabase.table('users').update(updates).eq('id', user_id).execute()
            return len(result.data) > 0
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            
            allowed_fields = ['email', 'telegram_id', 'telegram_username', 'password_hash', 
                            'is_active', 'is_admin', 'last_login']
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys() if k in allowed_fields])
            values = [v for k, v in updates.items() if k in allowed_fields]
            values.append(user_id)
            
            if set_clause:
                c.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
                conn.commit()
            conn.close()
            return True
    
    def get_users(self, pending_only: bool = False) -> List[Dict[str, Any]]:
        """Get all users, optionally only pending."""
        if self.is_supabase:
            query = self._supabase.table('users').select('*')
            if pending_only:
                query = query.eq('is_active', False)
            result = query.execute()
            return result.data if result.data else []
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            if pending_only:
                c.execute('SELECT * FROM users WHERE is_active = 0')
            else:
                c.execute('SELECT * FROM users')
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def get_word(self, character: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get word by character and user."""
        if self.is_supabase:
            result = self._supabase.table('words').select('*').eq('character', character).eq('user_id', user_id).single().execute()
            return result.data if result.data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM words WHERE character = ? AND user_id = ?', (character, user_id))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
    
    def get_words_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all words for a user."""
        if self.is_supabase:
            result = self._supabase.table('words').select('*').eq('user_id', user_id).execute()
            return result.data if result.data else []
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM words WHERE user_id = ? ORDER BY created_at', (user_id,))
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def create_word(self, word_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new word entry."""
        if self.is_supabase:
            result = self._supabase.table('words').insert(word_data).execute()
            return result.data[0] if result.data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO words 
                (character, user_id, pinyin, translation, meaning, stroke_gifs, pronunciation, 
                 exemplary_image, anki_usage_examples, real_usage_examples, styled_term)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                word_data.get('character'),
                word_data.get('user_id'),
                word_data.get('pinyin'),
                word_data.get('translation'),
                word_data.get('meaning'),
                word_data.get('stroke_gifs'),
                word_data.get('pronunciation'),
                word_data.get('exemplary_image'),
                word_data.get('anki_usage_examples'),
                word_data.get('real_usage_examples'),
                word_data.get('styled_term')
            ))
            conn.commit()
            conn.close()
            return self.get_word(word_data.get('character'), word_data.get('user_id'))
    
    def delete_word(self, character: str, user_id: str) -> bool:
        """Delete word."""
        if self.is_supabase:
            result = self._supabase.table('words').delete().eq('character', character).eq('user_id', user_id).execute()
            return len(result.data) > 0
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('DELETE FROM words WHERE character = ? AND user_id = ?', (character, user_id))
            conn.commit()
            conn.close()
            return True
    
    def delete_all_words(self, user_id: str) -> bool:
        """Delete all words for a user."""
        if self.is_supabase:
            result = self._supabase.table('words').delete().eq('user_id', user_id).execute()
            return True
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('DELETE FROM words WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            return True
    
    def save_verification_token(self, user_id: str, token: str, token_type: str, expires_at: datetime) -> bool:
        """Save verification token."""
        if self.is_supabase:
            result = self._supabase.table('verification_tokens').insert({
                'user_id': user_id,
                'token': token,
                'token_type': token_type,
                'expires_at': expires_at.isoformat()
            }).execute()
            return len(result.data) > 0
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO verification_tokens (user_id, token, token_type, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, token, token_type, expires_at))
            conn.commit()
            conn.close()
            return True
    
    def get_verification_token(self, token: str, token_type: str) -> Optional[Dict[str, Any]]:
        """Get verification token."""
        if self.is_supabase:
            result = self._supabase.table('verification_tokens').select('*').eq('token', token).eq('token_type', token_type).single().execute()
            return result.data if result.data else None
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''
                SELECT * FROM verification_tokens 
                WHERE token = ? AND token_type = ? AND used = 0 AND expires_at > ?
            ''', (token, token_type, datetime.utcnow()))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
    
    def mark_token_used(self, token: str) -> bool:
        """Mark token as used."""
        if self.is_supabase:
            result = self._supabase.table('verification_tokens').update({'used': True}).eq('token', token).execute()
            return len(result.data) > 0
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('UPDATE verification_tokens SET used = 1 WHERE token = ?', (token,))
            conn.commit()
            conn.close()
            return True
    
    def add_pending_approval(self, user_id: str) -> bool:
        """Add user to pending approvals."""
        if self.is_supabase:
            result = self._supabase.table('pending_approvals').insert({'user_id': user_id}).execute()
            return len(result.data) > 0
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO pending_approvals (user_id) VALUES (?)', (user_id,))
            conn.commit()
            conn.close()
            return True
    
    def remove_pending_approval(self, user_id: str) -> bool:
        """Remove user from pending approvals."""
        if self.is_supabase:
            result = self._supabase.table('pending_approvals').delete().eq('user_id', user_id).execute()
            return True
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('DELETE FROM pending_approvals WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            return True
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals with user info."""
        if self.is_supabase:
            result = self._supabase.table('pending_approvals').select('*, users(*)').execute()
            return result.data if result.data else []
        else:
            conn = sqlite3.connect(self._local_db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('''
                SELECT pa.*, u.email, u.telegram_username 
                FROM pending_approvals pa
                JOIN users u ON pa.user_id = u.id
                ORDER BY pa.requested_at
            ''')
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        if self.is_supabase:
            # Get user stats
            users_result = self._supabase.table('users').select('*', count='exact').execute()
            words_result = self._supabase.table('words').select('*', count='exact').execute()
            
            return {
                'total_users': users_result.count,
                'total_words': words_result.count
            }
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            total_users = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM words')
            total_words = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            active_users = c.fetchone()[0]
            conn.close()
            return {
                'total_users': total_users,
                'total_words': total_words,
                'active_users': active_users
            }
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get stats for a specific user."""
        if self.is_supabase:
            result = self._supabase.table('words').select('*', count='exact').eq('user_id', user_id).execute()
            return {'total_words': result.count}
        else:
            conn = sqlite3.connect(self._local_db_path)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM words WHERE user_id = ?', (user_id,))
            total_words = c.fetchone()[0]
            conn.close()
            return {'total_words': total_words}


# Global database instance
db = Database()
