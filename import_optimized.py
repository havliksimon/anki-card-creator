#!/usr/bin/env python3
"""Import optimized data to local SQLite database."""
import json
import sqlite3
from datetime import datetime

EXPORT_DIR = "migration_data_optimized"
DB_PATH = "local.db"


def import_data():
    """Import all optimized data to local SQLite."""
    print("Importing optimized data to local.db...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Import users
    print("\n=== Importing Users ===")
    with open(f"{EXPORT_DIR}/users.json", 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    for user in users:
        try:
            c.execute('''
                INSERT OR REPLACE INTO users 
                (id, email, telegram_id, telegram_username, password_hash, is_active, is_admin, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user['id'], user['email'], user['telegram_id'], user['telegram_username'],
                user['password_hash'], user['is_active'], user['is_admin'],
                user['created_at'], user['last_login']
            ))
        except Exception as e:
            print(f"  Error importing user {user['id']}: {e}")
    
    conn.commit()
    print(f"Imported {len(users)} users")
    
    # Import words with progress
    print("\n=== Importing Words ===")
    with open(f"{EXPORT_DIR}/words.json", 'r', encoding='utf-8') as f:
        words = json.load(f)
    
    count = 0
    for word in words:
        try:
            c.execute('''
                INSERT OR REPLACE INTO words 
                (character, user_id, pinyin, translation, meaning, stroke_gifs, pronunciation,
                 exemplary_image, anki_usage_examples, real_usage_examples, styled_term, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                word['character'], word['user_id'], word['pinyin'], word['translation'],
                word['meaning'], word['stroke_gifs'], word['pronunciation'],
                word['exemplary_image'], word['anki_usage_examples'], word['real_usage_examples'],
                word['styled_term'], word['created_at']
            ))
            count += 1
            if count % 500 == 0:
                conn.commit()
                print(f"  Imported {count}/{len(words)} words...")
        except Exception as e:
            print(f"  Error importing word {word['character']}: {e}")
    
    conn.commit()
    print(f"Imported {count} words")
    
    # Import example sentences
    print("\n=== Importing Example Sentences ===")
    with open(f"{EXPORT_DIR}/example_sentences.json", 'r', encoding='utf-8') as f:
        sentences = json.load(f)
    
    count = 0
    for sent in sentences:
        try:
            c.execute('''
                INSERT OR REPLACE INTO example_sentences 
                (chinese_sentence, styled_pinyin, styled_hanzi, translation, source_name, source_link, word_list)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sent.get('chinese_sentence'), sent.get('styled_pinyin'), sent.get('styled_hanzi'),
                sent.get('translation'), sent.get('source_name'), sent.get('source_link'), sent.get('word_list')
            ))
            count += 1
            if count % 1000 == 0:
                conn.commit()
                print(f"  Imported {count}/{len(sentences)} sentences...")
        except Exception as e:
            pass  # Skip duplicates silently
    
    conn.commit()
    print(f"Imported {count} example sentences")
    
    conn.close()
    print("\n=== Import Complete ===")


if __name__ == "__main__":
    import_data()
