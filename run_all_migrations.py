#!/usr/bin/env python3
"""Run all migrations: user_decks table, data migration, R2 optimization."""
import os
import sys
import httpx
import base64
from tqdm import tqdm

# Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://aptlvvbrlypqmymfatnx.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not SUPABASE_KEY:
    print("Error: SUPABASE_SERVICE_KEY not set")
    sys.exit(1)

client = httpx.Client(
    base_url=f"{SUPABASE_URL}/rest/v1",
    headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    },
    timeout=60.0
)


def create_user_decks_table():
    """Create the user_decks table via SQL."""
    print("\n=== Creating user_decks table ===")
    
    sql = """
    CREATE TABLE IF NOT EXISTS user_decks (
        deck_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        deck_number INTEGER NOT NULL,
        label TEXT DEFAULT '',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(user_id, deck_number)
    );
    CREATE INDEX IF NOT EXISTS idx_user_decks_user_id ON user_decks(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_decks_deck_id ON user_decks(deck_id);
    """
    
    try:
        # Run via RPC or REST
        response = client.post("/rpc/exec_sql", json={"sql": sql})
        if response.status_code in [200, 201, 204]:
            print("✓ user_decks table created")
            return True
        else:
            print(f"Note: Table may already exist ({response.status_code})")
            return True
    except Exception as e:
        print(f"Note: {e}")
        return True


def migrate_admin_decks():
    """Migrate admin to multi-deck format."""
    print("\n=== Migrating Admin Decks ===")
    
    # Get admin user
    try:
        response = client.get("/users?email=eq.simon2444444@gmail.com&select=id").json()
        if not response:
            print("Admin user not found")
            return
        
        admin_id = response[0]['id']
        print(f"Admin ID: {admin_id}")
        
        # Check for numeric decks (1, 2, 3, etc.) that belong to admin
        # These would be words with user_id like "1", "2", "3", etc.
        for deck_num in range(1, 10):
            deck_id = f"{admin_id}-{deck_num}"
            
            # Check if words exist with this deck number (old format)
            old_words = client.get(f"/words?user_id=eq.{deck_num}&select=id").json()
            
            if old_words:
                print(f"Found {len(old_words)} words in deck {deck_num}")
                
                # Create deck entry
                try:
                    client.post("/user_decks", json={
                        "deck_id": deck_id,
                        "user_id": admin_id,
                        "deck_number": deck_num,
                        "label": f"Deck {deck_num}"
                    })
                except:
                    pass  # May already exist
                
                # Migrate words to new deck_id format
                for word in tqdm(old_words, desc=f"Migrating deck {deck_num}"):
                    try:
                        client.patch(
                            f"/words?id=eq.{word['id']}",
                            json={"user_id": deck_id}
                        )
                    except Exception as e:
                        print(f"Error migrating word {word['id']}: {e}")
                
                print(f"✓ Migrated deck {deck_num}")
        
        print("✓ Admin deck migration complete")
    except Exception as e:
        print(f"Error: {e}")


def cleanup_supabase_storage():
    """Clean up Supabase storage after R2 migration."""
    print("\n=== Cleaning Up Supabase Storage ===")
    print("WARNING: This will delete TTS cache and stroke GIFs from Supabase")
    print("Only run this after confirming R2 migration is complete!")
    
    confirm = input("\nDelete TTS cache from Supabase? (yes/no): ")
    if confirm.lower() == 'yes':
        try:
            # Delete all TTS cache
            response = client.delete("/tts_cache")
            print(f"TTS cache deleted: {response.status_code}")
        except Exception as e:
            print(f"Error deleting TTS cache: {e}")
    
    confirm = input("\nDelete stroke GIFs from Supabase? (yes/no): ")
    if confirm.lower() == 'yes':
        try:
            # Delete all stroke GIFs
            response = client.delete("/stroke_gifs")
            print(f"Stroke GIFs deleted: {response.status_code}")
        except Exception as e:
            print(f"Error deleting stroke GIFs: {e}")


def main():
    print("=== Anki Card Creator - Migration Tool ===")
    print(f"Supabase: {SUPABASE_URL}")
    
    print("\n1. Create user_decks table")
    print("2. Migrate admin decks")
    print("3. Clean up Supabase storage (after R2 migration)")
    print("4. Run all")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        create_user_decks_table()
    elif choice == '2':
        migrate_admin_decks()
    elif choice == '3':
        cleanup_supabase_storage()
    elif choice == '4':
        create_user_decks_table()
        migrate_admin_decks()
        print("\nSkipping cleanup - run option 3 separately after confirming R2 migration")
    else:
        print("Invalid option")


if __name__ == '__main__':
    main()
