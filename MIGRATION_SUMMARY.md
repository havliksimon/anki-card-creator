# Anki Card Creator - Migration Summary

## Overview

Successfully migrated the old Telegram-based Anki Card Creator to a modern Flask web application with:
- Dual authentication (Email + Telegram)
- Beautiful web UI with dark theme
- Admin approval system
- Full data migration from old SQLite databases

## Data Migration Status

### Source Data (from old app)
- **chinese_words.db**: 3,956 words from 6 users
- **example_sentences.db**: 24,849 example sentences
- **cache.db**: 6,860 TTS audio files + 5,027 stroke GIFs

### Migration Results
✓ **Users**: 6 accounts migrated
  - 1 admin (ID: 5624590693)
  - 5 regular users with Telegram IDs
  
✓ **Words**: 3,956 words with full data
  - Pinyin with tone colors
  - Translations
  - Audio pronunciations
  - Example sentences
  - Images

✓ **Example Sentences**: 24,849 sentences
  - Chinese text
  - Pinyin
  - English translations
  - Source attribution

✓ **Cache Data**: Metadata exported
  - TTS audio files (6,860)
  - Stroke GIFs (5,027)

## New Features

### Authentication
- Email/password login with verification
- Telegram Login Widget integration
- Password reset via email
- Admin approval required for new accounts

### Web Interface
- Modern dark theme UI
- Responsive design
- Dashboard with statistics
- Dictionary management
- Word detail views
- CSV export for Anki

### Admin Panel
- User approval queue
- User management
- Statistics overview
- Admin promotion/demotion

### API Integrations
- DeepSeek API (AI-generated sentences)
- Unsplash API (card images)
- gTTS (text-to-speech)
- Google Vision (OCR - optional)

## File Structure

```
anki_card_creator/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── .env.example             # Environment template
├── .gitignore               # Git ignore rules
├── Procfile                 # Koyeb deployment config
├── runtime.txt              # Python version
├── README.md                # Project documentation
├── DEPLOYMENT.md            # Deployment guide
├── SETUP.md                 # Setup instructions
├── MIGRATION_SUMMARY.md     # This file
├── supabase_migration.sql   # Supabase database schema
├── migrate_data.py          # Supabase migration script
├── import_to_local.py       # Local SQLite import
├── export_data.py           # Data export from old DB
├── test_app.py              # Test suite
├── verify_setup.py          # Setup verification
├── migration_data/          # Exported JSON data
│   ├── users.json
│   ├── words.json
│   ├── example_sentences.json
│   ├── tts_cache_metadata.json
│   └── stroke_gifs_metadata.json
├── src/
│   ├── config.py
│   ├── models/
│   │   ├── database.py     # Database layer
│   │   └── user.py         # User model
│   ├── routes/
│   │   ├── auth.py         # Authentication routes
│   │   ├── main.py         # Main app routes
│   │   └── admin.py        # Admin routes
│   ├── services/
│   │   ├── dictionary_service.py
│   │   └── scraper_service.py
│   └── utils/
│       ├── chinese_utils.py
│       └── email_service.py
└── templates/               # HTML templates
    ├── base.html
    ├── index.html
    ├── dashboard.html
    ├── dictionary.html
    ├── auth/
    ├── admin/
    ├── email/
    └── errors/
```

## Environment Variables

### Required
```env
SECRET_KEY=your-secret-key
SUPABASE_URL=https://aptlvvbrlypqmymfatnx.supabase.co
SUPABASE_KEY=sb_publishable_7Mp1_7oM9Nr-xmj-Ld1kTA_cM26jDlA
SUPABASE_SERVICE_KEY=your-service-key
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_USERNAME=your_bot_username
APP_URL=https://your-app.koyeb.app
```

### Optional
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
DEEPSEEK_API_KEY=your-key
UNSPLASH_API_KEY=your-key
GOOGLE_VISION_API_KEY=your-key
```

## Deployment

### Local Development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env
python app.py
```

### Koyeb Deployment
1. Push to GitHub
2. Connect repo to Koyeb
3. Set environment variables
4. Deploy!

See `DEPLOYMENT.md` for detailed instructions.

## Testing

All tests passing:
- ✓ App factory
- ✓ Database operations
- ✓ Authentication
- ✓ Chinese utilities
- ✓ Email tokens
- ✓ Routes
- ✓ TTS API

Run tests:
```bash
python test_app.py
python verify_setup.py
```

## Known Issues & Notes

1. **Scraping**: Full scraping functionality requires Firefox and geckodriver. The scraper is configured to use the binaries from the old app location.

2. **Email**: Email notifications require SMTP configuration. Without it, users can still register but won't receive verification emails.

3. **Supabase**: Direct PostgreSQL connection might be blocked by network. Use the REST API through the Supabase client instead.

4. **Data**: All existing user data has been preserved. Users can log in with their Telegram accounts once approved.

## Next Steps

1. Deploy to Koyeb with Supabase
2. Configure Telegram bot with domain
3. Set up email (optional but recommended)
4. Add API keys for enhanced features (optional)
5. Notify existing users about the new web interface

## Credits

- Original app: Telegram-based Anki Card Creator
- New framework: Flask 3.0
- Database: Supabase (PostgreSQL) with SQLite fallback
- UI: Custom dark theme with responsive design
- Hosting: Optimized for Koyeb free tier (512MB RAM)
