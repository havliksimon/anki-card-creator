-- ============================================
-- Anki Card Creator - Optimized Supabase Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable UUID extension (if needed)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. USERS TABLE
-- ============================================
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
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id) WHERE telegram_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

-- ============================================
-- 2. WORDS TABLE (Main vocabulary data)
-- ============================================
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
    UNIQUE(character, user_id)  -- Prevent duplicates per user
);

-- Performance indexes for words
CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id);
CREATE INDEX IF NOT EXISTS idx_words_character ON words(character);
CREATE INDEX IF NOT EXISTS idx_words_user_character ON words(user_id, character);

-- Full-text search index for Chinese characters
CREATE INDEX IF NOT EXISTS idx_words_character_trgm ON words USING gin(character gin_trgm_ops);

-- ============================================
-- 3. EXAMPLE SENTENCES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS example_sentences (
    id SERIAL PRIMARY KEY,
    chinese_sentence TEXT UNIQUE NOT NULL,
    styled_pinyin TEXT,
    styled_hanzi TEXT,
    translation TEXT,
    source_name TEXT,
    source_link TEXT,
    word_list TEXT
);

-- Indexes for example sentences
CREATE INDEX IF NOT EXISTS idx_sentences_word_list ON example_sentences(word_list) WHERE word_list IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sentences_lookup ON example_sentences USING gin(to_tsvector('simple', COALESCE(word_list, '')));

-- ============================================
-- 4. PENDING APPROVALS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS pending_approvals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pending_requested ON pending_approvals(requested_at);

-- ============================================
-- 5. VERIFICATION TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tokens_lookup ON verification_tokens(token, token_type) WHERE used = false;
CREATE INDEX IF NOT EXISTS idx_tokens_expires ON verification_tokens(expires_at) WHERE used = false;

-- ============================================
-- 6. TTS CACHE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS tts_cache (
    hanzi TEXT PRIMARY KEY,
    audio BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tts_created ON tts_cache(created_at);

-- ============================================
-- 7. STROKE GIFS CACHE TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS stroke_gifs (
    character TEXT NOT NULL,
    stroke_order INTEGER NOT NULL,
    gif_data BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (character, stroke_order)
);

CREATE INDEX IF NOT EXISTS idx_strokes_character ON stroke_gifs(character);

-- ============================================
-- ROW LEVEL SECURITY (Optional but recommended)
-- ============================================
-- Uncomment to enable RLS
-- Note: Requires proper auth setup in your application

-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE words ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE verification_tokens ENABLE ROW LEVEL SECURITY;

-- -- Users can only access their own data
-- CREATE POLICY "Users own data" ON users
--     FOR ALL USING (auth.uid()::text = id);

-- CREATE POLICY "Users own words" ON words
--     FOR ALL USING (auth.uid()::text = user_id);

-- ============================================
-- OPTIMIZATION VIEWS
-- ============================================

-- View: User word counts
CREATE OR REPLACE VIEW user_word_counts AS
SELECT 
    user_id,
    COUNT(*) as word_count,
    COUNT(DISTINCT character) as unique_chars
FROM words
GROUP BY user_id;

-- View: Popular characters (shared between users)
CREATE OR REPLACE VIEW popular_characters AS
SELECT 
    character,
    COUNT(DISTINCT user_id) as user_count,
    COUNT(*) as total_entries
FROM words
GROUP BY character
HAVING COUNT(DISTINCT user_id) > 1
ORDER BY user_count DESC;

-- View: Database statistics
CREATE OR REPLACE VIEW db_stats AS
SELECT 
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users,
    (SELECT COUNT(*) FROM words) as total_words,
    (SELECT COUNT(DISTINCT character) FROM words) as unique_characters,
    (SELECT COUNT(*) FROM example_sentences) as example_sentences,
    (SELECT COUNT(*) FROM tts_cache) as tts_cached,
    (SELECT COUNT(*) FROM stroke_gifs) as stroke_gifs_cached;

-- ============================================
-- DATA IMPORT (After running this schema)
-- ============================================

-- Method 1: Using Supabase Dashboard
-- 1. Export your JSON data to CSV
-- 2. Go to Supabase Dashboard → Table Editor
-- 3. Select table → Insert → Import CSV

-- Method 2: Using pg_dump/pg_restore (for large datasets)
-- 1. Import to local PostgreSQL first
-- 2. Use pg_dump to export
-- 3. Use Supabase Import feature

-- Method 3: Using the migration script
-- Run: python migrate_data.py (requires SUPABASE_SERVICE_KEY)

-- ============================================
-- MAINTENANCE QUERIES
-- ============================================

-- Check database stats
-- SELECT * FROM db_stats;

-- Check user word counts
-- SELECT * FROM user_word_counts;

-- Find popular characters
-- SELECT * FROM popular_characters LIMIT 10;

-- Clean old TTS cache (older than 1 year)
-- DELETE FROM tts_cache WHERE created_at < NOW() - INTERVAL '1 year';

-- Find unused example sentences
-- SELECT * FROM example_sentences 
-- WHERE word_list IS NULL OR word_list = '';
