-- ============================================
-- Anki Card Creator - Supabase Migration Script
-- Run this in Supabase SQL Editor
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
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

-- Words table
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
);

-- Example sentences table
CREATE TABLE IF NOT EXISTS example_sentences (
    id SERIAL PRIMARY KEY,
    chinese_sentence TEXT UNIQUE,
    styled_pinyin TEXT,
    styled_hanzi TEXT,
    translation TEXT,
    source_name TEXT,
    source_link TEXT,
    word_list TEXT
);

-- Pending approvals table
CREATE TABLE IF NOT EXISTS pending_approvals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Verification tokens table
CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TTS cache table
CREATE TABLE IF NOT EXISTS tts_cache (
    hanzi TEXT PRIMARY KEY,
    audio BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stroke GIFs cache table
CREATE TABLE IF NOT EXISTS stroke_gifs (
    character TEXT NOT NULL,
    stroke_order INTEGER NOT NULL,
    gif_data BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (character, stroke_order)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_words_user_id ON words(user_id);
CREATE INDEX IF NOT EXISTS idx_words_character ON words(character);
CREATE INDEX IF NOT EXISTS idx_example_sentences_word_list ON example_sentences USING gin(to_tsvector('simple', word_list));
CREATE INDEX IF NOT EXISTS idx_verification_tokens_token ON verification_tokens(token);
CREATE INDEX IF NOT EXISTS idx_tts_cache_hanzi ON tts_cache(hanzi);

-- ============================================
-- Optional: Row Level Security (RLS) Policies
-- Uncomment if you want to enable RLS
-- ============================================

-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE words ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE verification_tokens ENABLE ROW LEVEL SECURITY;

-- -- Users can only see their own data
-- CREATE POLICY "Users can view own data" ON users
--     FOR SELECT USING (auth.uid()::text = id);

-- -- Users can only see their own words
-- CREATE POLICY "Users can view own words" ON words
--     FOR SELECT USING (auth.uid()::text = user_id);

-- -- Users can only insert their own words
-- CREATE POLICY "Users can insert own words" ON words
--     FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- -- Users can only delete their own words
-- CREATE POLICY "Users can delete own words" ON words
--     FOR DELETE USING (auth.uid()::text = user_id);

-- ============================================
-- Data Import from JSON (after export)
-- ============================================

-- To import the JSON data, use the migrate_data.py script
-- or use the Supabase Dashboard to import CSV files

-- Example for importing from CSV (export JSON to CSV first):
-- COPY users FROM '/path/to/users.csv' DELIMITER ',' CSV HEADER;
-- COPY words FROM '/path/to/words.csv' DELIMITER ',' CSV HEADER;
-- COPY example_sentences FROM '/path/to/example_sentences.csv' DELIMITER ',' CSV HEADER;
