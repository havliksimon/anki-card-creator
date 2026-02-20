"""Deck management for multi-deck support."""
from typing import List, Dict, Optional, Tuple
from flask import session, current_app


class DeckManager:
    """Manages user decks with USERID-DECKNUMBER format."""
    
    def __init__(self):
        self._client = None
    
    def _get_db(self):
        """Lazy load database client."""
        if self._client is None:
            from src.models.database import db
            self._client = db._client
        return self._client
    
    def get_deck_id(self, user_id: str, deck_number: int = 1) -> str:
        """Generate deck ID from user_id and deck number."""
        if deck_number == 1:
            # Deck 1 uses the base user_id (legacy format)
            return user_id
        return f"{user_id}-{deck_number}"
    
    def parse_deck_id(self, deck_id: str) -> Tuple[str, int]:
        """Parse deck ID into user_id and deck number."""
        if '-' in deck_id:
            parts = deck_id.rsplit('-', 1)
            try:
                # Check if last part is a number (deck number)
                deck_num = int(parts[1])
                return parts[0], deck_num
            except ValueError:
                pass
        return deck_id, 1
    
    def get_current_deck_id(self, user_id: str) -> str:
        """Get current deck ID from session or default to deck 1."""
        session_key = f'deck_id_{user_id}'
        deck_id = session.get(session_key)
        if deck_id:
            return deck_id
        return self.get_deck_id(user_id, 1)
    
    def set_current_deck(self, user_id: str, deck_number: int):
        """Set current deck for user in session."""
        session_key = f'deck_id_{user_id}'
        deck_id = self.get_deck_id(user_id, deck_number)
        session[session_key] = deck_id
        current_app.logger.info(f"Set deck for user {user_id}: {deck_id} (deck {deck_number})")
    
    def get_user_decks(self, user_id: str) -> List[Dict]:
        """Get all decks for a user - works with BOTH legacy numeric IDs and new format."""
        from src.models.database import db
        decks = []
        
        # Method 1: Check user_decks table (if it exists)
        try:
            response = self._get_db().get(
                f"/user_decks?user_id=eq.{user_id}&order=deck_number.asc"
            )
            data = response.json()
            if isinstance(data, list):
                for d in data:
                    if isinstance(d, dict) and 'deck_id' in d:
                        decks.append(d)
        except Exception as e:
            current_app.logger.debug(f"user_decks table query failed (expected if table doesn't exist): {e}")
        
        # Method 2: Check words table for all user IDs belonging to this user
        # This handles BOTH:
        # - Legacy format: user_id (for deck 1)
        # - Legacy format: "2", "3", "4", "5", "11" etc. (numeric user IDs for other decks)
        # - New format: user_id-1, user_id-3, etc.
        try:
            all_words = db.get_words_by_user(user_id)
            
            # Find all unique user_ids in words that belong to this user
            deck_numbers_found = set()
            
            for word in all_words:
                word_user_id = word.get('user_id', '')
                
                # Check if it's the base user_id (Deck 1)
                if word_user_id == user_id:
                    deck_numbers_found.add(1)
                # Check if it's the new format (user_id-NUMBER)
                elif str(word_user_id).startswith(f"{user_id}-"):
                    try:
                        deck_num = int(str(word_user_id).split('-')[-1])
                        deck_numbers_found.add(deck_num)
                    except ValueError:
                        pass
            
            # Also check for numeric user_ids (legacy format where user_id was "2", "3", etc.)
            # These belong to the admin user based on our data analysis
            all_words_all_users = db._client.get("/words?select=*").json()
            if isinstance(all_words_all_users, list):
                for word in all_words_all_users:
                    word_uid = str(word.get('user_id', ''))
                    # If it's a pure numeric ID (not a UUID), it might be a legacy deck
                    if word_uid.isdigit():
                        deck_num = int(word_uid)
                        deck_numbers_found.add(deck_num)
            
            # Create deck entries for all found deck numbers
            existing_numbers = {d['deck_number'] for d in decks}
            for deck_num in deck_numbers_found:
                if deck_num not in existing_numbers:
                    if deck_num == 1:
                        deck_id = user_id  # Legacy format for deck 1
                    else:
                        deck_id = str(deck_num)  # Legacy format: just the number
                    
                    decks.append({
                        'deck_id': deck_id,
                        'user_id': user_id,
                        'deck_number': deck_num,
                        'label': f'Deck {deck_num}'
                    })
            
            decks.sort(key=lambda x: x['deck_number'])
        except Exception as e:
            current_app.logger.error(f"Error scanning words for decks: {e}")
        
        if decks:
            return decks
        
        # Fallback to default deck
        return [{
            'deck_id': user_id,
            'user_id': user_id,
            'deck_number': 1,
            'label': 'Main Deck'
        }]
    
    def create_deck(self, user_id: str, deck_number: int, label: str = None) -> bool:
        """Create a new deck for user."""
        # For now, just ensure we can track it
        # We don't need to create anything in the database since:
        # - Deck 1 uses the base user_id
        # - Other decks use numeric IDs (legacy) or user_id-N format (new)
        return True
    
    def swap_to_deck(self, user_id: str, deck_number: int) -> str:
        """Swap to a deck, creating it if needed."""
        self.create_deck(user_id, deck_number, f"Deck {deck_number}")
        self.set_current_deck(user_id, deck_number)
        return self.get_deck_id(user_id, deck_number)


# Global instance
deck_manager = DeckManager()
