"""Multi-deck management system for all users."""
import os
import httpx
from typing import List, Dict, Optional
from flask import session, current_app


class DeckManager:
    """Manage multiple decks per user (USERID-1, USERID-2 format)."""
    
    def __init__(self):
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
        self._client = None
        if self.supabase_url and self.supabase_key:
            self._client = httpx.Client(
                base_url=f"{self.supabase_url}/rest/v1",
                headers={
                    "apikey": self.supabase_key,
                    "Authorization": f"Bearer {self.supabase_key}",
                },
                timeout=30.0
            )
    
    def _get_user_decks_table(self):
        """Ensure user_decks table exists."""
        # Note: Table should be created via migration
        pass
    
    def get_user_decks(self, user_id: str) -> List[Dict]:
        """Get all decks for a user - includes decks with words and user_decks entries."""
        decks = {}
        
        if not self._client:
            # Fallback: return default deck
            return [{
                'deck_id': f'{user_id}-1',
                'user_id': user_id,
                'deck_number': 1,
                'label': 'Main Deck'
            }]
        
        try:
            # Method 1: Get decks from user_decks table
            try:
                response = self._client.get(
                    f"/user_decks?user_id=eq.{user_id}&order=deck_number.asc"
                )
                data = response.json()
                if isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict) and 'deck_id' in d:
                            deck_num = d.get('deck_number', 1)
                            decks[deck_num] = d
            except Exception as e:
                current_app.logger.warning(f"Could not fetch user_decks: {e}")
            
            # Method 2: Get decks that have words (check words table)
            try:
                # Get all unique user_ids from words table that start with this user's ID
                # This catches decks like USERID-1, USERID-3, etc.
                response = self._client.get(
                    f"/words?user_id=like.{user_id}-*&select=user_id"
                )
                data = response.json()
                if isinstance(data, list):
                    for word in data:
                        word_user_id = word.get('user_id', '')
                        # Parse deck number from user_id-decknumber format
                        if word_user_id.startswith(f"{user_id}-"):
                            try:
                                deck_num = int(word_user_id.split('-')[-1])
                                if deck_num not in decks:
                                    decks[deck_num] = {
                                        'deck_id': word_user_id,
                                        'user_id': user_id,
                                        'deck_number': deck_num,
                                        'label': f'Deck {deck_num}'
                                    }
                            except (ValueError, IndexError):
                                pass
            except Exception as e:
                current_app.logger.warning(f"Could not fetch words decks: {e}")
            
            # Ensure deck 1 always exists
            if 1 not in decks:
                decks[1] = {
                    'deck_id': f'{user_id}-1',
                    'user_id': user_id,
                    'deck_number': 1,
                    'label': 'Main Deck'
                }
            
            # Return sorted by deck number
            return [decks[num] for num in sorted(decks.keys())]
            
        except Exception as e:
            current_app.logger.error(f"Error getting user decks: {e}")
            # Return default deck on error
            return [{
                'deck_id': f'{user_id}-1',
                'user_id': user_id,
                'deck_number': 1,
                'label': 'Main Deck'
            }]
    
    def get_deck_id(self, user_id: str, deck_number: int) -> str:
        """Get the full deck ID (USERID-DECKNUMBER format)."""
        return f"{user_id}-{deck_number}"
    
    def parse_deck_id(self, deck_id: str) -> tuple:
        """Parse deck ID into user_id and deck_number."""
        parts = deck_id.rsplit('-', 1)
        if len(parts) == 2:
            try:
                return parts[0], int(parts[1])
            except ValueError:
                pass
        return deck_id, 1  # Default to deck 1
    
    def create_deck(self, user_id: str, deck_number: int, label: str = "") -> Optional[Dict]:
        """Create a new deck for user."""
        if not self._client:
            return None
        
        deck_id = self.get_deck_id(user_id, deck_number)
        
        try:
            # Check if deck already exists
            existing = self._client.get(
                f"/user_decks?deck_id=eq.{deck_id}&limit=1"
            ).json()
            
            if existing:
                return existing[0]
            
            # Create new deck
            data = {
                "deck_id": deck_id,
                "user_id": user_id,
                "deck_number": deck_number,
                "label": label or f"Deck {deck_number}",
                "created_at": "now()"
            }
            
            response = self._client.post("/user_decks", json=data)
            if response.status_code == 201:
                return data
            return None
        except Exception as e:
            current_app.logger.error(f"Error creating deck: {e}")
            return None
    
    def get_or_create_default_deck(self, user_id: str) -> str:
        """Get or create default deck (deck 1) for user."""
        deck_id = self.get_deck_id(user_id, 1)
        
        # Check if exists
        decks = self.get_user_decks(user_id)
        if not decks:
            self.create_deck(user_id, 1, "Main Deck")
        
        return deck_id
    
    def get_current_deck_id(self, user_id: str) -> str:
        """Get the currently selected deck ID from session or default."""
        session_key = f'deck_id_{user_id}'
        deck_id = session.get(session_key)
        
        if not deck_id:
            deck_id = self.get_or_create_default_deck(user_id)
            session[session_key] = deck_id
        
        return deck_id
    
    def set_current_deck(self, user_id: str, deck_number: int) -> str:
        """Set the current deck for user."""
        deck_id = self.get_deck_id(user_id, deck_number)
        session_key = f'deck_id_{user_id}'
        session[session_key] = deck_id
        return deck_id
    
    def swap_to_deck(self, user_id: str, deck_number: int, label: str = "") -> str:
        """Swap to a deck, creating it if needed."""
        deck_id = self.get_deck_id(user_id, deck_number)
        
        # Ensure deck exists in database
        self.create_deck(user_id, deck_number, label)
        
        # Set as current
        return self.set_current_deck(user_id, deck_number)
    
    def update_deck_label(self, deck_id: str, label: str) -> bool:
        """Update the label of a deck."""
        if not self._client:
            return False
        
        try:
            response = self._client.patch(
                f"/user_decks?deck_id=eq.{deck_id}",
                json={"label": label}
            )
            return response.status_code == 204
        except Exception as e:
            current_app.logger.error(f"Error updating deck label: {e}")
            return False


# Global instance
deck_manager = DeckManager()
