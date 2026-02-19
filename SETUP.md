# Anki Card Creator - Setup Guide

## Quick Start

### 1. Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run the app
python app.py
```

The app will be available at `http://localhost:5000`

### 2. Database Migration from Old App

Data has been exported from the old SQLite databases:

- **3,956 words** from 6 users
- **24,849 example sentences**
- **6,860 TTS audio files**
- **5,027 stroke GIFs**

Exported files are in `migration_data/`:
- `users.json` - User accounts
- `words.json` - Word entries
- `example_sentences.json` - Example sentences
- `tts_cache_metadata.json` - TTS cache metadata
- `stroke_gifs_metadata.json` - Stroke GIFs metadata

To import to local SQLite:
```bash
python import_to_local.py
```

To migrate to Supabase, use the `migrate_data.py` script with your service key.

### 3. Supabase Setup

1. Go to [supabase.com](https://supabase.com) and create a project
2. Run the SQL in `supabase_migration.sql` in the SQL Editor
3. Copy your credentials to `.env`:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (anon key)
   - `SUPABASE_SERVICE_KEY` (service role key for migrations)

### 4. Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token to `TELEGRAM_BOT_TOKEN`
4. Set your domain with `/setdomain`
5. Add `TELEGRAM_BOT_USERNAME` (without @)

### 5. Email Setup (Optional)

For Gmail:
1. Enable 2-Factor Authentication
2. Generate App Password at https://myaccount.google.com/apppasswords
3. Add to `.env`:
   - `MAIL_USERNAME`: your-email@gmail.com
   - `MAIL_PASSWORD`: your-app-password
   - `MAIL_DEFAULT_SENDER`: your-email@gmail.com

### 6. API Keys (Optional)

- **DeepSeek**: Get from https://platform.deepseek.com/ for AI-generated sentences
- **Unsplash**: Get from https://unsplash.com/developers for card images
- **Google Vision**: Get from https://console.cloud.google.com/ for OCR

## Testing

Run the test suite:
```bash
python test_app.py
```

Test the scraper (requires Firefox):
```bash
python test_scraper.py
```

## Data Migration Status

✓ Users: 6 accounts migrated (1 admin, 5 regular users)
✓ Words: 3,956 words across all users
✓ Example Sentences: 24,849 sentences
✓ TTS Cache: 6,860 audio files
✓ Stroke GIFs: 5,027 GIF files

## Deployment

See `DEPLOYMENT.md` for detailed Koyeb deployment instructions.

### Quick Deploy to Koyeb

1. Push code to GitHub (make sure `.env` is in `.gitignore`!)
2. Connect GitHub repo to Koyeb
3. Set environment variables in Koyeb dashboard
4. Deploy!

## Troubleshooting

### App won't start
- Check all required env variables are set
- Ensure database is initialized

### Email not working
- Verify SMTP settings
- Check spam folders
- For Gmail, use App Password, not regular password

### Scraping not working
- Ensure Firefox is installed
- Check geckodriver path
- Verify extension file exists

### Database connection failed
- Check Supabase credentials
- Ensure database tables are created
- Check network connectivity

## Support

- Flask Docs: https://flask.palletsprojects.com
- Supabase Docs: https://supabase.com/docs
- Koyeb Docs: https://www.koyeb.com/docs
