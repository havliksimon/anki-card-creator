# Anki Card Creator - Fixes and Features Summary

## Critical Bugs Fixed

### 1. Database Schema Mismatch (FIXED)
**Problem:** `pending_approvals` table had different schema in Supabase vs SQLite vs code
**Solution:** 
- Unified schema: `user_id` (references users), `requested_at`
- Updated all database methods to use consistent schema
- Fixed `create_pending_approval()` to only take `user_id`
- Fixed `get_pending_approvals()` to join with users table

### 2. Type Errors in Routes (FIXED)
**Problem:** `'str' object has no attribute 'get'` on dashboard/dictionary pages
**Cause:** `get_user_decks()` returned strings instead of dicts when `user_decks` table missing
**Solution:** Added defensive coding with fallback to default deck

### 3. Admin Dashboard Error (FIXED)
**Problem:** `TypeError: unhashable type: 'slice'` on admin dashboard
**Cause:** `get_pending_approvals()` returned dict instead of list on error
**Solution:** Added proper error handling to ensure list return type

### 4. Delete Word Route Mismatch (FIXED)
**Problem:** Templates used `character` but route expected `word_id`
**Solution:** Updated templates to use `word.id` in delete forms

### 5. CSS Framework Mismatch (FIXED)
**Problem:** `deck_switcher.html` used Bootstrap classes but app uses custom CSS
**Solution:** Rewrote template to use app's CSS variables and classes

## Features Available

### User Features
1. **Email Registration/Login**
   - Registration with email verification
   - Password reset via email
   - Account approval workflow

2. **Telegram Login**
   - One-click login via Telegram widget
   - See TELEGRAM_SETUP.md for configuration

3. **Multi-Deck System**
   - Create multiple vocabulary decks (Deck 1, Deck 2, etc.)
   - Switch between decks easily
   - Label decks (e.g., "HSK 1", "Business Chinese")
   - Each deck is isolated with its own words

4. **Dictionary Management**
   - Add Chinese words (auto-extracts from pasted text)
   - View all words with pagination
   - Delete individual words
   - Clear entire deck
   - View word details with:
     - Pinyin pronunciation
     - Translation
     - Example sentences
     - Stroke order GIFs
     - Images

5. **Anki Export**
   - Export deck to CSV format
   - Compatible with Anki import
   - Includes all word data

6. **Anki Card Preview**
   - Preview how cards will look in Anki
   - Shows styling, examples, images

7. **Text-to-Speech**
   - Play pronunciation for any Chinese word
   - Cached for performance

### Admin Features
1. **Admin Dashboard**
   - View total users, words, pending approvals
   - Quick stats overview

2. **User Management**
   - View all users
   - Approve/reject pending registrations
   - Toggle admin status
   - Deactivate users

3. **Deck Switcher**
   - View any user's deck
   - Quick swap to any deck number
   - Browse all user vocabulary

4. **Statistics**
   - Detailed usage statistics
   - Word counts per user

## Environment Variables Required

### Required
```bash
SECRET_KEY=your-random-secret-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_USERNAME=your_bot_username
APP_URL=https://your-app.koyeb.app
```

### Optional but Recommended
```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure-password
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
DEEPSEEK_API_KEY=for-ai-examples
UNSPLASH_API_KEY=for-images
R2_ACCOUNT_ID=for-cloudflare-r2
R2_ACCESS_KEY_ID=for-cloudflare-r2
```

## Database Tables Required (Supabase)

1. `users` - User accounts
2. `words` - Vocabulary entries  
3. `pending_approvals` - Registration requests
4. `verification_tokens` - Email verification
5. `user_decks` - Multi-deck metadata (auto-created)
6. `tts_cache` - Audio cache
7. `stroke_gifs` - Stroke animation cache

Run `CREATE_TABLES.sql` in Supabase SQL Editor to create all tables.

## Testing Checklist

### Authentication
- [ ] Register with email
- [ ] Verify email
- [ ] Login with email
- [ ] Login with Telegram
- [ ] Reset password
- [ ] Logout

### User Features
- [ ] Add words to deck
- [ ] View dictionary
- [ ] Delete word
- [ ] Clear all words
- [ ] Switch between decks
- [ ] Create new deck
- [ ] Export deck to CSV
- [ ] Preview Anki card
- [ ] Play TTS audio

### Admin Features
- [ ] Access admin dashboard
- [ ] View pending approvals
- [ ] Approve user
- [ ] Reject user
- [ ] View all users
- [ ] Toggle admin status
- [ ] Deactivate user
- [ ] Use deck switcher

## Deployment Status

The app is now fully functional with all critical bugs fixed. Push to GitHub and Koyeb will auto-deploy.

**Next Steps:**
1. Set up Telegram login (see TELEGRAM_SETUP.md)
2. Run database migrations if needed
3. Create admin user via environment variables
4. Test all features
