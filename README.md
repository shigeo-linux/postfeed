# Postfeed

An AI-powered Gmail digest that sends a summary of your emails to Telegram every 12 hours. Runs automatically in the background as a systemd timer on Linux.

---

## Features

- **Automatic email digest** — fetches your recent Gmail emails and summarises them with AI
- **Telegram delivery** — sends the digest directly to your Telegram chat
- **Runs every 12 hours** — via systemd timer, no manual intervention needed
- **Catch-up on boot** — if the computer was off, the digest runs automatically when it powers back on
- **GTK settings window** — easy configuration of all settings
- **Run Now button** — trigger a digest at any time
- **Activity log** — view the log of all runs and errors

---

## Requirements

- Ubuntu 24.04 / Linux Mint 22.x (or any systemd-based Linux)
- Python 3.10+
- A Gmail account with Gmail API access (one-time setup)
- A Telegram account and bot (free, takes ~5 minutes to set up)
- An OpenRouter API key (free tier at [openrouter.ai/keys](https://openrouter.ai/keys))

---

## Installation

```bash
cd postfeed/
chmod +x install.sh
./install.sh
```

Then launch the settings window with:
```bash
postfeed
```

---

## Setup Guide

### Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Save the **bot token** (e.g. `123456789:ABCdef...`)
4. Start a chat with your new bot
5. Find your **chat ID** by visiting:
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
   Look for `"id"` inside `"chat"`

### Step 2 — Set up Gmail API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable the **Gmail API** (APIs & Services → Enable APIs)
4. Go to APIs & Services → **Credentials**
5. Create **OAuth 2.0 credentials** → Desktop app
6. Download the JSON file and save it as:
   ```
   ~/.config/postfeed/credentials.json
   ```

### Step 3 — Configure Postfeed

1. Launch `postfeed`
2. Enter your **OpenRouter API key**
3. Enter your **Telegram bot token** and **chat ID**
4. Click **Save Settings**
5. Click **Test Telegram** to verify the connection
6. Click **Run Now** — a browser window will open to authorise Gmail access
7. Your first digest will be sent to Telegram

After first authorisation, Postfeed runs automatically every 12 hours.

---

## Telegram digest format

```
📬 Email Digest — 5 emails

📧 From: John Smith | Subject: Meeting tomorrow at 3pm
→ John is confirming the 3pm meeting and asking you to bring the report.

📧 From: GitHub | Subject: New pull request on your repo
→ A new pull request has been opened requesting a bug fix.

🕐 Sent by Postfeed at 08:00 on 17 May 2026
```

---

## Data storage

| Data | Location |
|---|---|
| Settings & API keys | `~/.config/postfeed/config.json` |
| Gmail OAuth token | `~/.config/postfeed/token.json` |
| Gmail credentials | `~/.config/postfeed/credentials.json` |
| Activity log | `~/.config/postfeed/postfeed.log` |

---

## Recommended models (via OpenRouter)

| Model | Notes |
|---|---|
| `anthropic/claude-3.5-sonnet` | Best overall quality (default) |
| `openai/gpt-4o` | Strong alternative |
| `openai/gpt-4o-mini` | Faster, lower cost |

---

## Managing the timer

```bash
# Check timer status
systemctl --user status postfeed.timer

# Stop the timer
systemctl --user stop postfeed.timer

# Disable the timer
systemctl --user disable postfeed.timer

# View logs
journalctl --user -u postfeed.service
```

---

## Troubleshooting

**Digest not arriving**
- Check the log: click **View Log** in the app or open `~/.config/postfeed/postfeed.log`
- Verify your Telegram token and chat ID with the **Test Telegram** button

**Gmail authorisation errors**
- Delete `~/.config/postfeed/token.json` and click **Run Now** to re-authorise

**App won't start**
```bash
python3 /opt/postfeed/postfeed.py
```

---

## Uninstall

```bash
systemctl --user stop postfeed.timer
systemctl --user disable postfeed.timer
rm ~/.config/systemd/user/postfeed.*
sudo rm -rf /opt/postfeed
sudo rm -f /usr/local/bin/postfeed
sudo rm -f /usr/share/applications/postfeed.desktop
sudo rm -f /usr/share/icons/hicolor/scalable/apps/postfeed.svg
rm -rf ~/.config/postfeed
```
