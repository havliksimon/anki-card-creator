# Deployment Guide

This guide will walk you through deploying Anki Card Creator on Koyeb with Supabase as the database.

## Table of Contents

1. [Supabase Setup](#supabase-setup)
2. [Koyeb Setup](#koyeb-setup)
3. [Telegram Bot Setup](#telegram-bot-setup)
4. [Email Setup (Optional)](#email-setup-optional)
5. [Environment Variables](#environment-variables)
6. [Local Development with Supabase](#local-development-with-supabase)

---

## Supabase Setup

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click "New Project"
3. Choose your organization
4. Enter project name: `anki-card-creator`
5. Set a secure database password (save this!)
6. Choose region closest to your users (e.g., `US East` for Koyeb)
7. Click "Create new project"
8. Wait for the project to be created (1-2 minutes)

### 2. Get Your API Keys

1. In your Supabase dashboard, go to **Project Settings** (gear icon)
2. Click **API** in the sidebar
3. Copy the following:
   - `URL` - This is your `SUPABASE_URL`
   - `anon public` - This is your `SUPABASE_KEY`
   - `service_role secret` - This is your `SUPABASE_SERVICE_KEY` (keep this secret!)

### 3. Create Database Tables

In the Supabase dashboard:

1. Go to **SQL Editor** in the sidebar
2. Click **New query**
3. Paste the following SQL and click **Run**:

```sql
-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    telegram_id TEXT UNIQUE,
    telegram_username TEXT,
    password_hash TEXT,
    is_active BOOLEAN DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Words table
CREATE TABLE words (
    id SERIAL PRIMARY KEY,
    character TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pinyin TEXT,
    translation TEXT,
    meaning TEXT,
    stroke_gifs TEXT,
    pronunciation TEXT,
    exemplary_image TEXT,
    anki_usage_examples TEXT,
    real_usage_examples TEXT,
    styled_term TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(character, user_id)
);

-- Example sentences table
CREATE TABLE example_sentences (
    id SERIAL PRIMARY KEY,
    chinese_sentence TEXT UNIQUE,
    styled_pinyin TEXT,
    styled_hanzi TEXT,
    translation TEXT,
    source_name TEXT,
    source_link TEXT,
    word_list TEXT
);

-- Pending approvals table
CREATE TABLE pending_approvals (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Verification tokens table
CREATE TABLE verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    token_type TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TTS cache table
CREATE TABLE tts_cache (
    hanzi TEXT PRIMARY KEY,
    audio BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stroke GIFs cache table
CREATE TABLE stroke_gifs (
    character TEXT NOT NULL,
    stroke_order INTEGER NOT NULL,
    gif_data BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (character, stroke_order)
);

-- Row Level Security (RLS) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE words ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_tokens ENABLE ROW LEVEL SECURITY;
```

### 4. Disable Row Level Security (Optional)

For simplicity with Flask, you can disable RLS (we handle security in the app):

```sql
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE words DISABLE ROW LEVEL SECURITY;
ALTER TABLE pending_approvals DISABLE ROW LEVEL SECURITY;
ALTER TABLE verification_tokens DISABLE ROW LEVEL SECURITY;
```

---

## Koyeb Setup

### 1. Sign Up for Koyeb

1. Go to [koyeb.com](https://www.koyeb.com) and sign up (you can use GitHub)
2. Koyeb offers a generous free tier with 512MB RAM

### 2. Deploy from GitHub

1. Push your code to GitHub (make sure `.env` is in `.gitignore`!)
2. In Koyeb dashboard, click **Create App**
3. Choose **GitHub** as the deployment method
4. Select your repository
5. Configure:
   - **Name**: `anki-card-creator` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Build Command**: (leave default or empty)
   - **Run Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Port**: `8000`

### 3. Add Environment Variables

In the Koyeb dashboard, under your app settings:

1. Go to **Settings** → **Environment Variables**
2. Add all variables from your `.env` file:

| Variable | Value | Secret? |
|----------|-------|---------|
| `SECRET_KEY` | Random string (generate with `openssl rand -hex 32`) | Yes |
| `SUPABASE_URL` | Your Supabase URL | No |
| `SUPABASE_KEY` | Your Supabase anon key | Yes |
| `SUPABASE_SERVICE_KEY` | Your Supabase service role key | Yes |
| `TELEGRAM_BOT_TOKEN` | Your bot token | Yes |
| `TELEGRAM_BOT_USERNAME` | Your bot username (without @) | No |
| `ADMIN_EMAIL` | Your admin email | No |
| `ADMIN_PASSWORD` | Secure admin password | Yes |
| `APP_URL` | Your Koyeb app URL (e.g., `https://anki-card-creator-xxx.koyeb.app`) | No |

Optional but recommended:
| `MAIL_SERVER` | smtp.gmail.com | No |
| `MAIL_PORT` | 587 | No |
| `MAIL_USERNAME` | Your email | No |
| `MAIL_PASSWORD` | App password | Yes |
| `DEEPSEEK_API_KEY` | Your DeepSeek API key | Yes |
| `UNSPLASH_API_KEY` | Your Unsplash API key | Yes |

3. Click **Deploy** or **Save**

### 4. Wait for Deployment

Koyeb will build and deploy your app. This takes 2-5 minutes.

Once deployed, your app will be available at `https://your-app-name.koyeb.app`

---

## Telegram Bot Setup

### 1. Create a Bot with BotFather

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Enter bot name (display name)
   - Enter bot username (must end in `bot`, e.g., `ankicards_bot`)
4. Copy the bot token provided

### 2. Configure Domain

To use Telegram Login Widget, you need to configure the domain:

1. Message [@BotFather](https://t.me/botfather)
2. Send `/setdomain`
3. Select your bot
4. Enter your Koyeb domain: `https://your-app-name.koyeb.app`

### 3. Get Bot Username

Your bot username is what users type to find your bot (e.g., `@ankicards_bot`).

---

## Email Setup (Optional)

For password reset and approval notifications, you need SMTP credentials.

### Gmail / Google Workspace

1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account → Security → App Passwords
3. Generate an app password for "Mail"
4. Use this as `MAIL_PASSWORD`

Configuration:
- `MAIL_SERVER`: `smtp.gmail.com`
- `MAIL_PORT`: `587`
- `MAIL_USE_TLS`: `true`
- `MAIL_USERNAME`: Your Gmail address
- `MAIL_PASSWORD`: Your app password

### Other Providers

| Provider | Server | Port | TLS |
|----------|--------|------|-----|
| Outlook | smtp.office365.com | 587 | true |
| Yahoo | smtp.mail.yahoo.com | 587 | true |
| SendGrid | smtp.sendgrid.net | 587 | true |

---

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Random 32-char string |
| `SUPABASE_URL` | Supabase project URL | https://xxx.supabase.co |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | eyJhbG... |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | 123456:ABC-DEF... |
| `TELEGRAM_BOT_USERNAME` | Bot username without @ | mybot |
| `APP_URL` | Your app's URL | https://myapp.koyeb.app |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_LOCAL_DB` | Use SQLite instead of Supabase | false |
| `ADMIN_EMAIL` | Admin account email | admin@example.com |
| `ADMIN_PASSWORD` | Admin password | (none) |
| `MAIL_SERVER` | SMTP server | smtp.gmail.com |
| `MAIL_PORT` | SMTP port | 587 |
| `MAIL_USE_TLS` | Use TLS | true |
| `MAIL_USERNAME` | SMTP username | (none) |
| `MAIL_PASSWORD` | SMTP password | (none) |
| `DEEPSEEK_API_KEY` | DeepSeek API for AI sentences | (none) |
| `UNSPLASH_API_KEY` | Unsplash API for images | (none) |
| `GOOGLE_VISION_API_KEY` | Google Vision for OCR | (none) |

---

## Local Development with Supabase

To test locally but use Supabase database:

1. Set in `.env`:
```
USE_LOCAL_DB=false
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key
```

2. Run the app:
```bash
python app.py
```

---

## Troubleshooting

### App Won't Start

- Check Koyeb logs for errors
- Verify all required environment variables are set
- Ensure `PORT` is not hardcoded (use `$PORT` env var)

### Database Connection Failed

- Verify Supabase URL and service key
- Check Supabase is in "Active" state
- Ensure database password wasn't changed

### Telegram Login Not Working

- Verify bot token is correct
- Check domain is set with BotFather (`/setdomain`)
- Ensure `TELEGRAM_BOT_USERNAME` matches (without @)

### Email Not Sending

- Verify SMTP settings
- For Gmail, ensure "Less secure app access" is enabled OR use App Password
- Check spam folders

---

## Updating Your App

Simply push to your GitHub repository. Koyeb will automatically redeploy.

To disable auto-deploy:
1. Go to Koyeb dashboard
2. Select your app
3. Settings → GitHub
4. Toggle "Auto-deploy"

---

## Backup & Recovery

### Export Data from Supabase

1. Go to Supabase dashboard → Database → Backups
2. Or use SQL Editor to export specific tables

### Local Backup (SQLite)

If using local SQLite:
```bash
cp local.db local.db.backup.$(date +%Y%m%d)
```

---

## Monitoring

### Koyeb Metrics

Koyeb provides basic metrics:
- CPU usage
- Memory usage
- Request count
- Response times

View in your app dashboard → Metrics

### Logs

View logs in Koyeb dashboard or use CLI:
```bash
koyeb logs -a your-app-name
```

---

## Scaling

Koyeb free tier includes:
- 512MB RAM
- 1 vCPU
- 100GB bandwidth/month

For more resources, upgrade to:
- Starter: 1GB RAM, 1 vCPU
- Professional: 2GB+ RAM, 2+ vCPUs

---

## Security Checklist

- [ ] `SECRET_KEY` is a random, long string
- [ ] `SUPABASE_SERVICE_KEY` is kept secret
- [ ] `TELEGRAM_BOT_TOKEN` is kept secret
- [ ] Admin password is strong
- [ ] `.env` is in `.gitignore`
- [ ] Database backups enabled

---

## Support

- Koyeb Docs: [koyeb.com/docs](https://www.koyeb.com/docs)
- Supabase Docs: [supabase.com/docs](https://supabase.com/docs)
- Flask Docs: [flask.palletsprojects.com](https://flask.palletsprojects.com)
