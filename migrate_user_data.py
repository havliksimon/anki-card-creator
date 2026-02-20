#!/usr/bin/env python3
"""Migrate words from old user_id to new admin user_id."""
import httpx
import os

supabase_url = os.environ.get('SUPABASE_URL', 'https://aptlvvbrlypqmymfatnx.supabase.co')
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY', '')

client = httpx.Client(
    base_url=f'{supabase_url}/rest/v1',
    headers={'apikey': supabase_key, 'Authorization': f'Bearer {supabase_key}'}
)

# Get words with user_id '1'
words = client.get('/words?user_id=eq.1&select=id').json()
print(f'Found {len(words)} words with user_id=1')

# Get admin user ID
admin = client.get('/users?email=eq.simon2444444@gmail.com&select=id').json()
if not admin:
    print('Admin user not found!')
    exit(1)

admin_id = admin[0]['id']
print(f'Admin ID: {admin_id}')

# Bulk update - update all words at once using in operator
word_ids = [str(w['id']) for w in words]
if word_ids:
    # Supabase doesn't support bulk update with in filter via REST directly
    # So we update each one
    updated = 0
    for word_id in word_ids:
        try:
            response = client.patch(f'/words?id=eq.{word_id}', json={'user_id': admin_id})
            if response.status_code == 204:
                updated += 1
        except Exception as e:
            print(f'Error updating {word_id}: {e}')
    
    print(f'Successfully migrated {updated}/{len(words)} words to admin!')
else:
    print('No words to migrate')
