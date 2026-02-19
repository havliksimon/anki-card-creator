-- RUN THIS IN SUPABASE DASHBOARD SQL EDITOR
-- Then run: python migrate_to_supabase.py

-- Enable extensions
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

-- Example sentences
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

-- Pending approvals
CREATE TABLE IF NOT EXISTS pending_approvals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Verification tokens
CREATE TABLE IF NOT EXISTS verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TTS cache
CREATE TABLE IF NOT EXISTS tts_cache (
    hanzi TEXT PRIMARY KEY,
    audio BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stroke GIFs
CREATE TABLE IF NOT EXISTS stroke_gifs (
    character TEXT NOT NULL,
    stroke_order INTEGER NOT NULL,
    gif_data BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (character, stroke_order)
);

-- Performance indexes
CREATE INDEX idx_words_user_id ON words(user_id);
CREATE INDEX idx_words_character ON words(character);

-- Verification query
SELECT 'Tables created successfully!' as status;
SELECT 
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count;
