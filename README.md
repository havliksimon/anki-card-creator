# Anki Card Creator

A beautiful web application for creating Anki flashcards from Chinese text. Extract Chinese characters from images or text, automatically generate flashcard data with pinyin, translations, example sentences, and export to Anki.

## Features

- 🔤 **Dual Authentication** - Login with email/password or Telegram
- 📝 **Text Extraction** - Paste Chinese text to extract all unique words
- 🔊 **Audio Pronunciation** - Built-in TTS for pronunciation practice
- 🖌 **Stroke Order** - Visual stroke order GIFs
- 🎨 **Tone Colors** - Color-coded pinyin by tone
- 🤖 **AI Examples** - AI-generated example sentences at appropriate HSK levels
- 📊 **Progress Tracking** - HSK level progress and text coverage estimation
- 📤 **Anki Export** - CSV export formatted for Anki import
- 👨‍💼 **Admin Dashboard** - User approval system and statistics

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: Supabase (PostgreSQL) with SQLite fallback for local development
- **Frontend**: HTML/CSS with dark theme
- **Authentication**: Flask-Login with Telegram Login Widget
- **Email**: Flask-Mail
- **Rate Limiting**: Flask-Limiter

## Quick Start

### Local Development

1. **Clone the repository**:
```bash
git clone <your-repo>
cd anki-card-creator
```

2. **Create virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**:
```bash
python app.py
```

The app will be available at `http://localhost:5000`

### Environment Variables

See `.env.example` for all required environment variables.

Key variables:
- `SECRET_KEY` - Flask secret key
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` - Supabase credentials
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` - Telegram bot credentials
- `MAIL_*` - SMTP settings for email
- `DEEPSEEK_API_KEY` - For AI-generated example sentences
- `UNSPLASH_API_KEY` - For card images

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions on Koyeb with Supabase.

## Usage

### For Users

1. Sign up with email or Telegram
2. Wait for admin approval
3. Add Chinese words via the "Add Words" page
4. View your dictionary and export to Anki

### For Admins

1. Log in with admin credentials
2. Visit `/admin` to see pending approvals
3. Approve or reject users
4. View statistics and manage users

## Anki Import

1. Export your words as CSV
2. In Anki: File → Import
3. Select the CSV file
4. Set field separator to Comma
5. Enable "Allow HTML in fields"
6. Choose your note type and deck
7. Import!

## License

MIT
