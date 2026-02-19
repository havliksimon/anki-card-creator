# Anki Card Creator - Deployment Guide

## QUICK START - Single Command

To test locally RIGHT NOW:

```bash
./run_local.sh
```

Then open: http://localhost:5000

---

## FULL DEPLOYMENT (Supabase + Koyeb)

### Step 1: Set Up Supabase (5 minutes)

1. Go to https://supabase.com/dashboard
2. Your project: `aptlvvbrlypqmymfatnx`
3. Click **SQL Editor** (left sidebar)
4. Click **New Query**
5. Copy and paste the contents of `supabase_migration_optimized.sql`
6. Click **Run**
7. Wait for "Success" message

### Step 2: Get Service Role Key (1 minute)

1. In Supabase Dashboard, click **Project Settings** (gear icon)
2. Click **API** in left sidebar
3. Copy `service_role secret` (NOT the anon key)
4. Save it - you'll need it in a moment

### Step 3: Configure Environment (1 minute)

Edit `.env` file:

```bash
nano .env
```

Change these lines:
```env
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFwdGx2dmJybHlwcW15bWZhdG54Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTk1NTIwMCwiZXhwIjoyMDU1NTMxMjAwfQ.dFQtKCm9kUdlznPq
USE_LOCAL_DB=false
```

(Save with Ctrl+X, then Y, then Enter)

### Step 4: Migrate Data (2 minutes)

```bash
python setup_supabase.py
```

This will migrate:
- 6 users
- 3,956 words
- 24,849 example sentences

### Step 5: Test with Supabase (1 minute)

```bash
./run_production.sh
```

Check that data is there:
- Log in as admin: `admin@anki-cards.com` / `admin123`
- Check that word counts match

### Step 6: Deploy to Koyeb (5 minutes)

1. **Push to GitHub**:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/anki-card-creator.git
git push -u origin main
```

2. **Go to Koyeb**:
   - https://app.koyeb.com
   - Sign up/login with GitHub
   - Click **Create App**
   - Choose **GitHub** as source
   - Select your repository

3. **Configure Build**:
   - Build command: (leave empty)
   - Run command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4`
   - Port: `8000`

4. **Set Environment Variables** (copy from your `.env`):
   - `SECRET_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_SERVICE_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_BOT_USERNAME`
   - `TELEGRAM_ADMIN_ID=5624590693`
   - `ADMIN_EMAIL=admin@anki-cards.com`
   - `ADMIN_PASSWORD=admin123`
   - `USE_LOCAL_DB=false`

5. **Deploy!**
   - Click **Deploy**
   - Wait 2-3 minutes
   - Your app will be live at `https://your-app.koyeb.app`

### Step 7: Configure Telegram (2 minutes)

1. Message @BotFather on Telegram
2. Send: `/setdomain`
3. Select your bot
4. Enter your Koyeb URL: `https://your-app.koyeb.app`
5. Done! Telegram login now works.

---

## VERIFICATION CHECKLIST

After deployment, verify:

- [ ] Homepage loads at `https://your-app.koyeb.app`
- [ ] Can register new account
- [ ] Can log in with admin account
- [ ] Dashboard shows word counts
- [ ] Can add new Chinese words
- [ ] Can view dictionary
- [ ] Can export CSV
- [ ] Telegram login button appears
- [ ] Admin panel accessible at `/admin/`

---

## TROUBLESHOOTING

### "Failed to connect to Supabase"
- Check SUPABASE_SERVICE_KEY is correct
- Make sure tables were created (Step 1)
- Try running `python setup_supabase.py` again

### "Tables don't exist"
- Run the SQL in `supabase_migration_optimized.sql` in Supabase Dashboard
- Wait for "Success" message before proceeding

### "App won't start on Koyeb"
- Check all environment variables are set
- Verify `USE_LOCAL_DB=false`
- Check Koyeb logs for specific errors

### "No data after migration"
- Run `python setup_supabase.py` again
- Check Supabase Table Editor to see if data is there
- Verify you're using the correct Supabase project

---

## COMMANDS REFERENCE

```bash
# Test locally with SQLite (uses local.db)
./run_local.sh

# Test with Supabase (requires setup)
./run_production.sh

# Migrate data to Supabase
python setup_supabase.py

# Run all tests
python final_test.py

# Check setup
python complete_setup.py
```

---

## DATA SUMMARY

Your migrated data:
- **6 users** (1 admin: 5624590693, 5 regular users)
- **3,956 words** with full data (pinyin, audio, images)
- **24,849 example sentences**
- **6,860 TTS audio files**
- **5,027 stroke order GIFs**

---

## SUPPORT

- Supabase Docs: https://supabase.com/docs
- Koyeb Docs: https://www.koyeb.com/docs
- Flask Docs: https://flask.palletsprojects.com
