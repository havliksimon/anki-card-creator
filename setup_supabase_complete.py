#!/usr/bin/env python3
"""Complete Supabase setup using direct PostgreSQL connection."""
import psycopg2
import json
import os
from datetime import datetime

# Supabase connection details
DB_HOST = "db.aptlvvbrlypqmymfatnx.supabase.co"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "dFQtKCm9kUdlznPq"
DB_PORT = "5432"

def get_connection():
    """Create database connection."""
    conn_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return psycopg2.connect(conn_string)

def create_tables(conn):
    """Create all tables."""
    print("\n=== Creating Tables ===")
    
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            telegram_id TEXT UNIQUE,
            telegram_username TEXT,
            password_hash TEXT,
            is_active BOOLEAN DEFAULT false,
            is_admin BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_login TIMESTAMP WITH TIME ZONE
        )
    """)
    print("  ✓ users table")
    
    # Words table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id SERIAL PRIMARY KEY,
            character TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            pinyin TEXT,
            translation TEXT,
            meaning TEXT,
            stroke_gifs TEXT,
            pronunciation TEXT,
            exemplary_image TEXT,
            anki_usage_examples TEXT,
            real_usage_examples TEXT,
            styled_term TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(character, user_id)
        )
    """)
    print("  ✓ words table")
    
    # Example sentences
    cur.execute("""
        CREATE TABLE IF NOT EXISTS example_sentences (
            id SERIAL PRIMARY KEY,
            chinese_sentence TEXT UNIQUE,
            styled_pinyin TEXT,
            styled_hanzi TEXT,
            translation TEXT,
            source_name TEXT,
            source_link TEXT,
            word_list TEXT
        )
    """)
    print("  ✓ example_sentences table")
    
    # Pending approvals
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_approvals (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    print("  ✓ pending_approvals table")
    
    # Verification tokens
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verification_tokens (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token TEXT NOT NULL,
            token_type TEXT NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    print("  ✓ verification_tokens table")
    
    # TTS cache
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tts_cache (
            hanzi TEXT PRIMARY KEY,
            audio BYTEA,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    print("  ✓ tts_cache table")
    
    # Stroke GIFs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stroke_gifs (
            character TEXT NOT NULL,
            stroke_order INTEGER NOT NULL,
            gif_data BYTEA,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (character, stroke_order)
        )
    """)
    print("  ✓ stroke_gifs table")
    
    # Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_words_character ON words(character)")
    print("  ✓ indexes created")
    
    conn.commit()
    cur.close()
    print("\n  All tables created successfully!")

def migrate_users(conn):
    """Migrate users."""
    print("\n=== Migrating Users ===")
    
    with open("migration_data_optimized/users.json", 'r') as f:
        users = json.load(f)
    
    cur = conn.cursor()
    
    for user in users:
        cur.execute("""
            INSERT INTO users (id, email, telegram_id, telegram_username, password_hash, is_active, is_admin, created_at, last_login)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                telegram_id = EXCLUDED.telegram_id,
                is_active = EXCLUDED.is_active,
                is_admin = EXCLUDED.is_admin
        """, (
            user['id'], user['email'], user['telegram_id'], user['telegram_username'],
            user['password_hash'], user['is_active'], user['is_admin'],
            user['created_at'], user['last_login']
        ))
    
    conn.commit()
    cur.close()
    print(f"  ✓ Migrated {len(users)} users")

def migrate_words(conn):
    """Migrate words in batches."""
    print("\n=== Migrating Words ===")
    
    with open("migration_data_optimized/words.json", 'r') as f:
        words = json.load(f)
    
    cur = conn.cursor()
    
    batch_size = 100
    total = len(words)
    migrated = 0
    
    for i in range(0, total, batch_size):
        batch = words[i:i+batch_size]
        
        for word in batch:
            cur.execute("""
                INSERT INTO words (character, user_id, pinyin, translation, meaning, stroke_gifs, pronunciation, exemplary_image, anki_usage_examples, real_usage_examples, styled_term, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (character, user_id) DO UPDATE SET
                    pinyin = EXCLUDED.pinyin,
                    translation = EXCLUDED.translation,
                    pronunciation = EXCLUDED.pronunciation
            """, (
                word['character'], word['user_id'], word['pinyin'], word['translation'],
                word['meaning'], word['stroke_gifs'], word['pronunciation'],
                word['exemplary_image'], word['anki_usage_examples'], word['real_usage_examples'],
                word['styled_term'], word['created_at']
            ))
        
        conn.commit()
        migrated += len(batch)
        if migrated % 500 == 0:
            print(f"  Progress: {migrated}/{total}")
    
    cur.close()
    print(f"  ✓ Migrated {migrated} words")

def migrate_sentences(conn):
    """Migrate example sentences."""
    print("\n=== Migrating Example Sentences ===")
    
    with open("migration_data_optimized/example_sentences.json", 'r') as f:
        sentences = json.load(f)
    
    cur = conn.cursor()
    
    batch_size = 50
    total = len(sentences)
    migrated = 0
    
    for i in range(0, total, batch_size):
        batch = sentences[i:i+batch_size]
        
        for sent in batch:
            try:
                cur.execute("""
                    INSERT INTO example_sentences (chinese_sentence, styled_pinyin, styled_hanzi, translation, source_name, source_link, word_list)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chinese_sentence) DO NOTHING
                """, (
                    sent.get('chinese_sentence'), sent.get('styled_pinyin'), sent.get('styled_hanzi'),
                    sent.get('translation'), sent.get('source_name'), sent.get('source_link'), sent.get('word_list')
                ))
            except:
                pass  # Skip duplicates
        
        conn.commit()
        migrated += len(batch)
        if migrated % 1000 == 0:
            print(f"  Progress: {migrated}/{total}")
    
    cur.close()
    print(f"  ✓ Migrated {migrated} sentences")

def verify_migration(conn):
    """Verify data was migrated."""
    print("\n=== Verifying Migration ===")
    
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM words")
    words = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM example_sentences")
    sentences = cur.fetchone()[0]
    
    cur.close()
    
    print(f"  ✓ Users: {users}")
    print(f"  ✓ Words: {words}")
    print(f"  ✓ Example Sentences: {sentences}")
    
    return users > 0 and words > 0

def main():
    """Main setup function."""
    print("=" * 70)
    print("SUPABASE SETUP - Using Direct PostgreSQL Connection")
    print("=" * 70)
    print(f"\nHost: {DB_HOST}")
    print(f"Database: {DB_NAME}")
    print(f"User: {DB_USER}")
    
    try:
        print("\nConnecting to Supabase...")
        conn = get_connection()
        print("✓ Connected!")
        
        # Create tables
        create_tables(conn)
        
        # Migrate data
        migrate_users(conn)
        migrate_words(conn)
        migrate_sentences(conn)
        
        # Verify
        if verify_migration(conn):
            print("\n" + "=" * 70)
            print("✅ SUPABASE SETUP COMPLETE!")
            print("=" * 70)
            print("\nYour data is now in Supabase!")
            print("You can switch to production mode by setting USE_LOCAL_DB=false")
        else:
            print("\n⚠ Migration verification failed")
        
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
