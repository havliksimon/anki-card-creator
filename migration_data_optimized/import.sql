-- Optimized data import for Supabase
-- Run this after creating tables

-- Import users
COPY users (id, email, telegram_id, telegram_username, password_hash, is_active, is_admin, created_at, last_login)
FROM '/path/to/users.csv' DELIMITER ',' CSV HEADER;

-- Import words  
COPY words (character, user_id, pinyin, translation, meaning, stroke_gifs, pronunciation, exemplary_image, anki_usage_examples, real_usage_examples, styled_term, created_at)
FROM '/path/to/words.csv' DELIMITER ',' CSV HEADER;

-- Import example sentences
COPY example_sentences (chinese_sentence, styled_pinyin, styled_hanzi, translation, source_name, source_link, word_list)
FROM '/path/to/example_sentences.csv' DELIMITER ',' CSV HEADER;

-- Verify counts
SELECT 'Users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Words', COUNT(*) FROM words
UNION ALL
SELECT 'Example Sentences', COUNT(*) FROM example_sentences;
