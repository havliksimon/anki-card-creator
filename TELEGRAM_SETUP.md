# Telegram Login Widget Setup

This guide explains how to set up Telegram login for your Anki Card Creator app.

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Enter a **name** for your bot (display name, e.g., "Anki Card Creator")
   - Enter a **username** for your bot (must end in `bot`, e.g., `ankicards_bot`)
4. Copy the **bot token** provided (looks like `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`)

## Step 2: Configure Domain

To use the Telegram Login Widget, you must set your domain:

1. Message [@BotFather](https://t.me/botfather)
2. Send `/setdomain`
3. Select your bot from the list
4. Enter your Koyeb domain: `https://your-app-name.koyeb.app`
   - Replace `your-app-name` with your actual Koyeb app name

## Step 3: Set Environment Variables

In your Koyeb dashboard:

1. Go to your app → **Settings** → **Environment Variables**
2. Add these variables:

| Variable | Value | Secret? |
|----------|-------|---------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from Step 1 | **Yes** |
| `TELEGRAM_BOT_USERNAME` | Your bot username (without @, e.g., `ankicards_bot`) | No |

## Step 4: Deploy

Koyeb will automatically redeploy when you update environment variables.

## Testing

1. Visit your app login page
2. You should see "Login with Telegram" button
3. Click it - Telegram will ask you to confirm
4. After confirming, you'll be redirected back to your app

## Troubleshooting

**"Bot domain invalid" error:**
- Make sure you set the domain with BotFather using `/setdomain`
- Ensure the domain matches exactly (including https://)

**Login button not appearing:**
- Check that `TELEGRAM_BOT_USERNAME` is set correctly (without @)
- Verify `TELEGRAM_BOT_TOKEN` is correct

**"Authentication failed" error:**
- Check Koyeb logs for detailed error messages
- Ensure your domain is properly configured

## Admin Setup (Optional)

To make yourself an admin via Telegram:

1. Set `TELEGRAM_ADMIN_ID` in environment variables with your Telegram numeric ID
2. You can get your ID by messaging [@userinfobot](https://t.me/userinfobot) on Telegram
3. The admin will be auto-created on first app startup
