# PolyTracker Deployment Guide

This guide will help you deploy PolyTracker for 24/7 monitoring with alerts.

---

## Architecture Overview

```
┌─────────────────────────────────────┐
│           RAILWAY (Free/$5)         │
│                                     │
│   worker.py (runs 24/7)             │
│   └── Scans Polymarket              │
│   └── Sends Telegram/Slack alerts   │
│   └── Saves to PostgreSQL           │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│      RAILWAY PostgreSQL (Free)      │
│      (Automatic - included)         │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│      STREAMLIT CLOUD (Free)         │
│                                     │
│   dashboard.py                      │
│   └── View suspicious trades        │
│   └── Analyze wallets               │
│   └── Add wallets to monitor        │
└─────────────────────────────────────┘
```

---

## Step 1: Get Your API Keys

Before deploying, you'll need these (all free):

### Required for Alerts (pick at least one):

**Telegram Bot:**
1. Open Telegram, search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Save the **Bot Token** (looks like `123456:ABC-DEF...`)
4. Add the bot to a group or start a chat with it
5. Get your **Chat ID**:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":` in the response

**Slack Webhook:**
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create new app → From scratch
3. Add feature: Incoming Webhooks → Activate
4. Add New Webhook to Workspace
5. Copy the **Webhook URL**

### Optional (but recommended):

**Polygonscan API Key** (for wallet age detection):
1. Go to [polygonscan.com/register](https://polygonscan.com/register)
2. Create account
3. Go to API Keys → Add
4. Copy the key

---

## Step 2: Deploy Worker to Railway

### 2.1 Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub

### 2.2 Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Connect your GitHub and select your PolyTracker repo

### 2.3 Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically create the database

### 2.4 Configure Environment Variables

1. Click on your **worker service** (not the database)
2. Go to **"Variables"** tab
3. Add these variables:

```
# Database (Railway auto-fills this when you link the database)
DATABASE_URL=<auto-filled by Railway>

# Notifications (at least one required)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Optional but recommended
POLYGONSCAN_API_KEY=your_polygonscan_key

# Detection settings (optional - these are defaults)
WALLET_AGE_DAYS=30
MIN_BET_SIZE=10000
MAX_ODDS=0.20
SCAN_INTERVAL_MINUTES=5
CATEGORIES=news,crypto,cryptocurrency,politics,sports
```

### 2.5 Link Database

1. Click on **PostgreSQL** service
2. Go to **"Connect"** tab
3. Copy the **DATABASE_URL**
4. Add it to your worker's variables (if not auto-linked)

### 2.6 Deploy

1. Railway should auto-deploy when you push to GitHub
2. Check the **"Deployments"** tab for status
3. Check **"Logs"** to see if worker is running

**Expected logs:**
```
PolyTracker Worker Starting
✓ DATABASE_URL: post... (PostgreSQL connection)
✓ TELEGRAM_BOT_TOKEN: 1234... (Telegram alerts)
Starting continuous monitoring...
Fetched 150 markets in monitored categories
Scan completed. Found 3 suspicious trades.
Sleeping for 5 minutes...
```

---

## Step 3: Deploy Dashboard to Streamlit Cloud

### 3.1 Create Streamlit Account

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign up with GitHub

### 3.2 Deploy App

1. Click **"New app"**
2. Select your GitHub repo
3. Set **Main file path**: `dashboard.py`
4. Click **"Deploy"**

### 3.3 Add Secrets

1. Click **"Settings"** (gear icon) on your app
2. Go to **"Secrets"**
3. Add your database URL:

```toml
DATABASE_URL = "postgresql://user:pass@host:port/db"
```

(Copy this from Railway → PostgreSQL → Connect → DATABASE_URL)

### 3.4 Access Dashboard

Your dashboard will be live at:
`https://your-app-name.streamlit.app`

---

## Step 4: Test Everything

### Check Worker is Running

1. Go to Railway → Your project → Logs
2. You should see scan messages every 5 minutes

### Check Alerts are Working

1. Wait for a suspicious trade to be detected
2. You should receive a Telegram/Slack message

### Check Dashboard is Connected

1. Open your Streamlit app URL
2. You should see "Database: PostgreSQL" in sidebar
3. Suspicious trades should appear after worker detects them

---

## Customization

### Change Detection Thresholds

In Railway environment variables:

```
WALLET_AGE_DAYS=14      # Flag wallets younger than 14 days
MIN_BET_SIZE=5000       # Flag bets over $5,000
MAX_ODDS=0.15           # Flag bets under 15% odds
```

### Change Scan Interval

```
SCAN_INTERVAL_MINUTES=10    # Scan every 10 minutes instead of 5
```

### Change Categories

```
CATEGORIES=crypto,sports    # Only monitor crypto and sports
```

---

## Troubleshooting

### "No suspicious trades detected"

- Check thresholds aren't too restrictive
- Lower `MIN_BET_SIZE` to see more trades
- Increase `MAX_ODDS` to include more bets

### "Wallet age always unknown"

- Add `POLYGONSCAN_API_KEY` to Railway variables
- Get free key from polygonscan.com

### "Telegram alerts not sending"

- Verify `TELEGRAM_BOT_TOKEN` is correct
- Verify `TELEGRAM_CHAT_ID` is correct
- Make sure bot is added to the chat
- Check Railway logs for error messages

### "Dashboard shows no data"

- Verify `DATABASE_URL` in Streamlit secrets matches Railway
- Check worker is running in Railway logs
- Click "Refresh Data" button in dashboard

### "Railway deploy failed"

- Check build logs for errors
- Ensure `requirements.txt` is in repo root
- Ensure `Procfile` is in repo root

---

## Costs

| Service | Free Tier | Paid |
|---------|-----------|------|
| Railway Worker | 500 hrs/month | $5/month |
| Railway PostgreSQL | 1GB storage | Included |
| Streamlit Cloud | Unlimited | Free |
| **Total** | $0 (with limits) | ~$5/month |

The free tier gives you about 20 days of continuous running. After that, Railway costs about $5/month for always-on.

---

## Security Notes

- Never commit API keys to GitHub
- Use Railway/Streamlit secrets for sensitive values
- The `.env` file is for local development only
- `.gitignore` should include `.env`

---

## Support

If you have issues:
1. Check Railway logs for error messages
2. Check Streamlit logs (Settings → Logs)
3. Verify all environment variables are set correctly

---

*Happy monitoring! 🚨*
