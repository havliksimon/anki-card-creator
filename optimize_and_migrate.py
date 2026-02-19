#!/usr/bin/env python3
"""Optimized migration with data deduplication and cleanup."""
import os
import json
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

# Paths
OLD_APP_DIR = "/home/simon/py/nmy/anki_card_creator (Copy)/app"
OLD_API_DIR = "/home/simon/py/nmy/anki_card_creator (Copy)/server_api_app"
EXPORT_DIR = "migration_data_optimized"


def analyze_and_optimize_words():
    """Analyze and optimize words data."""
    print("=== Analyzing Words Database ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "chinese_words.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get stats
    c.execute("SELECT COUNT(*) as total FROM words")
    total = c.fetchone()['total']
    
    c.execute("SELECT COUNT(DISTINCT character) as unique_chars FROM words")
    unique_chars = c.fetchone()['unique_chars']
    
    c.execute("SELECT COUNT(DISTINCT user_id) as users FROM words")
    users = c.fetchone()['users']
    
    print(f"  Total entries: {total}")
    print(f"  Unique characters: {unique_chars}")
    print(f"  Users: {users}")
    print(f"  Shared characters: {total - unique_chars}")
    
    # Check for any potential issues
    c.execute("""
        SELECT character, user_id, COUNT(*) as cnt
        FROM words
        GROUP BY character, user_id
        HAVING cnt > 1
    """)
    duplicates = c.fetchall()
    
    if duplicates:
        print(f"\n  ⚠ Found {len(duplicates)} duplicate entries - will deduplicate")
    else:
        print(f"  ✓ No duplicates found (enforced by PRIMARY KEY)")
    
    # Get all unique users
    c.execute("SELECT DISTINCT user_id FROM words ORDER BY user_id")
    user_ids = [row[0] for row in c.fetchall()]
    
    print(f"\n  User breakdown:")
    for user_id in user_ids:
        c.execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (user_id,))
        count = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT character) FROM words WHERE user_id = ?", (user_id,))
        unique = c.fetchone()[0]
        print(f"    User {user_id}: {count} words ({unique} unique)")
    
    conn.close()
    return total, unique_chars, user_ids


def export_optimized_users():
    """Export users with proper UUIDs and metadata."""
    print("\n=== Exporting Optimized Users ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "chinese_words.db"))
    c = conn.cursor()
    
    c.execute("SELECT DISTINCT user_id FROM words")
    user_ids = [row[0] for row in c.fetchall()]
    
    users = []
    now = datetime.now(timezone.utc).isoformat()
    
    for user_id in user_ids:
        # Original admin ID from the old code
        is_admin = user_id == '5624590693'
        
        user = {
            'id': user_id,
            'email': None,
            'telegram_id': user_id if user_id.isdigit() else None,
            'telegram_username': None,
            'password_hash': None,
            'is_active': True,  # Existing users are pre-approved
            'is_admin': is_admin,
            'created_at': now,
            'last_login': None
        }
        users.append(user)
        
        status = "ADMIN" if is_admin else "user"
        print(f"  ✓ User {user_id[:20]}... ({status})")
    
    conn.close()
    
    # Save
    os.makedirs(EXPORT_DIR, exist_ok=True)
    with open(f"{EXPORT_DIR}/users.json", 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    print(f"\n  Exported {len(users)} users")
    return users


def export_optimized_words():
    """Export words with deduplication and cleanup."""
    print("\n=== Exporting Optimized Words ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "chinese_words.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all words - the PRIMARY KEY (character, user_id) ensures no duplicates
    c.execute("SELECT * FROM words ORDER BY user_id, character")
    
    words = []
    seen = set()  # Track (character, user_id) combinations
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for row in c.fetchall():
        word = dict(row)
        key = (word['character'], word['user_id'])
        
        if key in seen:
            skipped += 1
            continue
        
        seen.add(key)
        
        # Clean up the data
        clean_word = {
            'character': word['character'],
            'user_id': word['user_id'],
            'pinyin': word.get('pinyin') or None,
            'translation': word.get('translation') or None,
            'meaning': word.get('meaning') or None,
            'stroke_gifs': word.get('stroke_gifs') or None,
            'pronunciation': word.get('pronunciation') or None,
            'exemplary_image': word.get('exemplary_image') or None,
            'anki_usage_examples': word.get('anki_usage_examples') or None,
            'real_usage_examples': word.get('real_usage_examples') or None,
            'styled_term': word.get('styled_term') or None,
            'created_at': now
        }
        
        words.append(clean_word)
    
    conn.close()
    
    # Save
    with open(f"{EXPORT_DIR}/words.json", 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    
    print(f"  Exported {len(words)} words")
    if skipped:
        print(f"  Skipped {skipped} duplicates")
    
    # Stats
    by_user = defaultdict(int)
    for word in words:
        by_user[word['user_id']] += 1
    
    print(f"\n  By user:")
    for user_id, count in sorted(by_user.items()):
        print(f"    User {user_id[:20]}...: {count} words")
    
    return words


def export_optimized_sentences():
    """Export example sentences with deduplication."""
    print("\n=== Exporting Optimized Example Sentences ===")
    
    conn = sqlite3.connect(os.path.join(OLD_APP_DIR, "example_sentences.db"))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Check for duplicates
    c.execute("""
        SELECT chinese_sentence, COUNT(*) as cnt
        FROM example_sentences
        GROUP BY chinese_sentence
        HAVING cnt > 1
    """)
    duplicates = c.fetchall()
    
    if duplicates:
        print(f"  ⚠ Found {len(duplicates)} duplicate sentences - will deduplicate")
    else:
        print(f"  ✓ No duplicates found")
    
    # Get unique sentences (using DISTINCT)
    c.execute("""
        SELECT DISTINCT 
            chinese_sentence,
            styled_pinyin,
            styled_hanzi,
            translation,
            source_name,
            source_link,
            word_list
        FROM example_sentences
        ORDER BY chinese_sentence
    """)
    
    sentences = []
    seen = set()
    
    for row in c.fetchall():
        sent = dict(row)
        
        if sent['chinese_sentence'] in seen:
            continue
        
        seen.add(sent['chinese_sentence'])
        
        # Clean up
        clean_sent = {
            'chinese_sentence': sent['chinese_sentence'],
            'styled_pinyin': sent.get('styled_pinyin') or None,
            'styled_hanzi': sent.get('styled_hanzi') or None,
            'translation': sent.get('translation') or None,
            'source_name': sent.get('source_name') or None,
            'source_link': sent.get('source_link') or None,
            'word_list': sent.get('word_list') or None
        }
        sentences.append(clean_sent)
    
    conn.close()
    
    # Save
    with open(f"{EXPORT_DIR}/example_sentences.json", 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)
    
    print(f"  Exported {len(sentences)} unique sentences")
    
    # Word list stats
    word_counts = []
    for sent in sentences:
        if sent['word_list']:
            word_counts.append(len(sent['word_list'].split(',')))
    
    if word_counts:
        avg_words = sum(word_counts) / len(word_counts)
        print(f"  Average words per sentence: {avg_words:.1f}")
    
    return sentences


def export_cache_metadata():
    """Export TTS and stroke GIF metadata."""
    print("\n=== Exporting Cache Metadata ===")
    
    conn = sqlite3.connect(os.path.join(OLD_API_DIR, "cache.db"))
    c = conn.cursor()
    
    # TTS cache
    c.execute("SELECT hanzi FROM cache ORDER BY hanzi")
    tts_entries = [{'hanzi': row[0]} for row in c.fetchall()]
    
    with open(f"{EXPORT_DIR}/tts_cache_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(tts_entries, f, ensure_ascii=False, indent=2)
    
    print(f"  Exported {len(tts_entries)} TTS entries")
    
    # Stroke GIFs
    c.execute("SELECT character, stroke_order FROM stroke_gifs ORDER BY character, stroke_order")
    gifs = [{'character': row[0], 'stroke_order': row[1]} for row in c.fetchall()]
    
    with open(f"{EXPORT_DIR}/stroke_gifs_metadata.json", 'w', encoding='utf-8') as f:
        json.dump(gifs, f, ensure_ascii=False, indent=2)
    
    print(f"  Exported {len(gifs)} stroke GIF entries")
    
    conn.close()
    
    return tts_entries, gifs


def create_import_sql():
    """Create SQL for importing to Supabase."""
    print("\n=== Creating Import SQL ===")
    
    sql = """-- Optimized data import for Supabase
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
"""
    
    with open(f"{EXPORT_DIR}/import.sql", 'w', encoding='utf-8') as f:
        f.write(sql)
    
    print(f"  Created import.sql")


def compare_with_original():
    """Compare optimized data with original."""
    print("\n=== Comparison with Original ===")
    
    original_sizes = {}
    optimized_sizes = {}
    
    for filename in ['users.json', 'words.json', 'example_sentences.json', 
                     'tts_cache_metadata.json', 'stroke_gifs_metadata.json']:
        orig_path = f"migration_data/{filename}"
        opt_path = f"{EXPORT_DIR}/{filename}"
        
        if os.path.exists(orig_path):
            original_sizes[filename] = os.path.getsize(orig_path)
        if os.path.exists(opt_path):
            optimized_sizes[filename] = os.path.getsize(opt_path)
    
    print(f"  {'File':<30} {'Original':>12} {'Optimized':>12} {'Diff':>10}")
    print(f"  {'-'*68}")
    
    total_orig = 0
    total_opt = 0
    
    for filename in original_sizes:
        orig = original_sizes.get(filename, 0)
        opt = optimized_sizes.get(filename, 0)
        diff = opt - orig
        total_orig += orig
        total_opt += opt
        
        print(f"  {filename:<30} {orig:>12,} {opt:>12,} {diff:>+10,}")
    
    print(f"  {'-'*68}")
    print(f"  {'TOTAL':<30} {total_orig:>12,} {total_opt:>12,} {total_opt-total_orig:>+10,}")


def main():
    """Main optimization function."""
    print("=" * 70)
    print("Anki Card Creator - Optimized Data Migration")
    print("=" * 70)
    
    # Analyze original data
    total, unique_chars, users = analyze_and_optimize_words()
    
    # Export optimized data
    users_data = export_optimized_users()
    words_data = export_optimized_words()
    sentences_data = export_optimized_sentences()
    tts_data, gifs_data = export_cache_metadata()
    
    # Create SQL import script
    create_import_sql()
    
    # Compare with original
    if os.path.exists("migration_data"):
        compare_with_original()
    
    print("\n" + "=" * 70)
    print("Optimization Complete!")
    print("=" * 70)
    print(f"\nOptimized data exported to: ./{EXPORT_DIR}/")
    print(f"  - {len(users_data)} users")
    print(f"  - {len(words_data)} words")
    print(f"  - {len(sentences_data)} example sentences")
    print(f"  - {len(tts_data)} TTS entries")
    print(f"  - {len(gifs_data)} stroke GIFs")
    print("\nTo import to local SQLite:")
    print(f"  python import_optimized.py")
    print("\nTo migrate to Supabase, use the migrate_data.py script")


if __name__ == "__main__":
    main()
