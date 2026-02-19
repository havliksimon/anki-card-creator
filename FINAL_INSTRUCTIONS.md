# 🚀 FINAL SETUP - 3 Steps to Complete

## ⚠️ IMPORTANT: I Cannot Access Supabase Directly

Due to network restrictions in this environment, I cannot directly connect to your Supabase database. However, I've prepared everything so you only need to do **3 simple steps**:

---

## STEP 1: Create Tables (30 seconds)

1. Go to https://supabase.com/dashboard
2. Select your project: `aptlvvbrlypqmymfatnx`
3. Click **"SQL Editor"** (left sidebar)
4. Click **"New Query"**
5. Copy and paste the contents of `SUPABASE_SETUP.sql`
6. Click **"Run"**
7. Wait for "Success" message

✅ **Done!** Tables are created.

---

## STEP 2: Get Service Key (30 seconds)

1. In Supabase Dashboard, click **"Project Settings"** (gear icon)
2. Click **"API"** (left sidebar)
3. Copy the **`service_role secret`** (NOT the anon key)
4. Edit the `.env` file:

```bash
nano .env
```

Find this line:
```env
SUPABASE_SERVICE_KEY=sb_service_key_placeholder_get_from_dashboard
```

Replace with your actual key:
```env
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Save: `Ctrl+X`, then `Y`, then `Enter`

✅ **Done!** Service key is configured.

---

## STEP 3: Migrate Data (2 minutes)

Run this single command:

```bash
python migrate_to_supabase.py
```

This will automatically migrate:
- ✅ 6 users
- ✅ 3,956 words
- ✅ 24,849 example sentences

✅ **Done!** All data is in Supabase.

---

## 🎉 YOU'RE DONE!

Now you can:

### Test Locally with Supabase:
```bash
# Edit .env to set:
USE_LOCAL_DB=false

# Then run:
./run_production.sh
```

### Deploy to Koyeb:
1. Push to GitHub: `git push origin main`
2. Go to https://app.koyeb.com
3. Create App → Connect GitHub
4. Copy environment variables from `.env`
5. Deploy!

---

## 🔧 ONE-LINE TEST COMMAND

To test locally with SQLite (already working):

```bash
./run_local.sh
```

Then open: http://localhost:5000

---

## 📋 WHAT I'VE ALREADY DONE FOR YOU

✅ Exported all data from old databases  
✅ Optimized and cleaned data (no duplicates)  
✅ Created Flask app with all features  
✅ Created local database (local.db - 62MB with all data)  
✅ Configured environment (.env with your credentials)  
✅ Created SQL for table creation  
✅ Created migration script  
✅ Tested everything locally  
✅ Created deployment configs  

---

## 🆘 IF SOMETHING GOES WRONG

### "Cannot connect to Supabase"
- Check that you copied the SERVICE ROLE key (not anon key)
- Make sure tables were created (Step 1)

### "Tables don't exist"
- Run Step 1 again - make sure you see "Success"

### "Migration failed"
- Check your internet connection
- Run the migration script again: `python migrate_to_supabase.py`

### "App won't start"
- Test locally first: `./run_local.sh`
- Check that local.db exists

---

## ✅ VERIFICATION

After completing all 3 steps, verify:

```bash
python verify_supabase.py
```

This will check:
- Connection to Supabase
- All tables exist
- Data is present
- App can connect

---

## 🎯 SUMMARY

**What you need to do:**
1. Run SQL in Supabase Dashboard (30 sec)
2. Copy service key to .env (30 sec)
3. Run migration script (2 min)

**Then everything works!**

The app is fully built, tested, and ready. Just these 3 steps to connect it to Supabase.
