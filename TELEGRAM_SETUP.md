# Telegram Bot Setup - Step by Step

This guide will walk you through setting up the Telegram bot for Anki Card Creator.

## Overview

The Telegram bot allows users to:
- Add Chinese words by sending text or images
- View their dictionary
- Export to Anki CSV
- Manage multiple decks
- Get statistics

## Step 1: Create Your Bot

### 1.1 Message @BotFather

1. Open Telegram
2. Search for `@BotFather` (official Telegram bot creator)
3. Click **START** or send `/start`

### 1.2 Create a New Bot

1. Send `/newbot` to BotFather
2. When asked for a name, enter: `Anki Card Creator` (or your preferred name)
3. When asked for a username, enter a unique name ending in `bot`:
   - Example: `ankicards_bot`
   - Example: `yourname_anki_bot`
   - Must be globally unique

### 1.3 Save Your Token

BotFather will give you a token that looks like:
```
123456789:ABCdefGHIjklMNOpqrSTUvwxyz123456789
```

**⚠️ IMPORTANT:** Save this token somewhere safe! You'll need it in Step 3.

## Step 2: Configure Domain

This step is REQUIRED for the Telegram Login Widget to work on your website.

### 2.1 Set the Domain

1. Message `@BotFather` again
2. Send `/setdomain`
3. Select your bot from the list
4. Enter your website URL:
   ```
   https://your-app-name.koyeb.app
   ```
   (Replace `your-app-name` with your actual Koyeb app name)

### 2.2 Verify

You should see: `Success! Domain updated.`

## Step 3: Configure Environment Variables

### 3.1 For Koyeb Deployment (Web App)

1. Go to [Koyeb Dashboard](https://app.koyeb.com)
2. Select your app
3. Go to **Settings** → **Environment Variables**
4. Add these variables:

| Variable | Value | Secret? |
|----------|-------|---------|
| `TELEGRAM_BOT_TOKEN` | Your token from Step 1.3 | **YES** |
| `TELEGRAM_BOT_USERNAME` | Your bot username (without @) | No |

Example:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz123456789
TELEGRAM_BOT_USERNAME=ankicards_bot
```

### 3.2 For Telegram Bot (Optional - if running separately)

If you want to run the Telegram bot separately, also set:

```bash
export TELEGRAM_BOT_TOKEN="your-token-here"
export SUPABASE_URL="your-supabase-url"
export SUPABASE_SERVICE_KEY="your-service-key"
export TELEGRAM_ADMIN_ID="your-telegram-id"  # Optional
```

Then run:
```bash
python run_telegram_bot.py
```

## Step 4: Set Up Bot Commands (Recommended)

This adds a command menu in Telegram:

1. Message `@BotFather`
2. Send `/setcommands`
3. Select your bot
4. Send this command list:

```
start - Start the bot and get welcome message
help - Show all available commands
dictionary - View your saved words
dictinfo - Show dictionary statistics
export - Export to Anki CSV
csv - Alias for /export
e - Quick export
list - List your decks
l - Quick list
chosedict - Switch to a different deck
rmdict - Remove a word by index or character
rm - Alias for /rmdict
search - Search for a word
clearmydata - Clear all your data
changelog - See latest updates
admin - Admin menu (admin only)
stats - System statistics (admin only)
```

## Step 5: Test Your Bot

### 5.1 Find Your Bot

1. In Telegram, search for your bot's username (e.g., `@ankicards_bot`)
2. Click **START**

### 5.2 Test Commands

Try these commands:
- `/start` - Should welcome you
- `/help` - Should show commands
- Send Chinese text like `你好世界` - Should extract words

### 5.3 Test Web Login

1. Go to your website login page
2. Click "Login with Telegram"
3. Should redirect to Telegram and back

## Troubleshooting

### "Bot domain invalid" Error
- Make sure you ran `/setdomain` with BotFather
- Ensure the URL includes `https://`
- The URL must match exactly

### Bot Not Responding
- Check that `TELEGRAM_BOT_TOKEN` is set correctly
- Check Koyeb logs for errors
- Try restarting the app

### Login Button Not Working
- Verify `TELEGRAM_BOT_USERNAME` is set (without @)
- Check browser console for JavaScript errors
- Ensure domain is configured correctly

### "Account pending approval"
- New users need admin approval
- Go to Admin Dashboard → Pending Approvals
- Approve the user

## Bot Commands Reference

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and setup |
| `/help` | Show all commands |
| `/dictionary` | View saved words |
| `/export` | Export to CSV |
| `/list` | List decks |
| `/chosedict [num]` | Switch deck |
| `/rmdict [index/char]` | Remove word |
| `/search [word]` | Search dictionary |
| `/clearmydata` | Clear all data |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Admin menu |
| `/stats` | System statistics |
| `/wipedict [user_id]` | Wipe user data |

## Next Steps

1. **Get Your Admin ID** (optional)
   - Message `@userinfobot` on Telegram
   - It will reply with your ID
   - Set `TELEGRAM_ADMIN_ID` in environment variables

2. **Test End-to-End**
   - Register as a new user via web
   - Approve yourself via admin
   - Add words via Telegram
   - Export and import to Anki

3. **Share With Users**
   - Share your bot username
   - Users can start using immediately
   - They'll be pending until you approve them
