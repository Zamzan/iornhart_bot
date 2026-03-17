# 🤖 JARVIS Bot — Hugging Face Edition (100% Free)

> No credit card. No paid API. 100% free forever.

---

## 🧠 AI Model Used
**Mistral-7B-Instruct** via Hugging Face Inference API
- Smart, fast, multilingual
- Free tier: unlimited personal use
- No billing, no limits

---

## 🔑 STEP 1 — Get Your Free API Keys

### 1. 🤗 Hugging Face API Key (FREE — No Credit Card)
1. Go to → https://huggingface.co/join
2. Create a free account
3. Go to → https://huggingface.co/settings/tokens
4. Click **"New token"** → Name it "jarvis" → Role: **Read**
5. Copy the token (starts with `hf_...`)

### 2. 🤖 Telegram Bot Token
1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. "My Jarvis")
4. Choose a username (e.g. `myjarvis_bot`)
5. Copy the token

### 3. 🌤 OpenWeatherMap API Key (FREE)
1. Register at → https://openweathermap.org/api
2. Go to → https://home.openweathermap.org/api_keys
3. Copy your default key
4. ⚠️ Wait ~10 minutes before using

### 4. 📰 GNews API Key (FREE)
1. Register at → https://gnews.io
2. Go to dashboard → copy your key
3. Free tier = 100 articles/day

---

## 🚀 STEP 2 — Deploy Free 24/7 on Render.com

### A) Push to GitHub
```bash
git init
git add .
git commit -m "JARVIS HF bot"
git remote add origin https://github.com/YOUR_USERNAME/jarvis-hf-bot.git
git push -u origin main
```

### B) Deploy on Render
1. Go to → https://render.com (free account)
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub repo
4. Set **Environment Variables**:

```
TELEGRAM_TOKEN   = your_telegram_token
HF_API_KEY       = hf_xxxxxxxxxxxxxxxx
WEATHER_API_KEY  = your_openweathermap_key
GNEWS_API_KEY    = your_gnews_key
```

5. Build Command: `pip install -r requirements.txt`
6. Start Command: `python bot.py`
7. Click **Deploy** ✅

---

## 💻 STEP 3 — Run Locally (Optional / Testing)

```bash
# Install packages
pip install -r requirements.txt

# Set environment variables (Linux/Mac)
export TELEGRAM_TOKEN="your_token"
export HF_API_KEY="hf_xxxxxxxxxx"
export WEATHER_API_KEY="your_key"
export GNEWS_API_KEY="your_key"

# Windows (PowerShell)
$env:TELEGRAM_TOKEN="your_token"
$env:HF_API_KEY="hf_xxxxxxxxxx"
$env:WEATHER_API_KEY="your_key"
$env:GNEWS_API_KEY="your_key"

# Run
python bot.py
```

---

## 📱 Bot Commands

| Command | What it does |
|---|---|
| Send any message | AI Chat (Mistral-7B) |
| `/search <query>` | DuckDuckGo web search |
| `/weather <city>` | Live weather info |
| `/news <topic>` | Latest headlines |
| `/image <prompt>` | AI image (Pollinations, free) |
| `/clear` | Clear chat memory |
| `/help` | Show all commands |

---

## 🆓 Everything is FREE

| Service | Free Limit |
|---|---|
| 🤗 HF Mistral-7B Chat | Unlimited (personal use) |
| 🎨 Pollinations Images | Unlimited |
| 🔍 DuckDuckGo Search | Unlimited |
| 🌤 OpenWeatherMap | 1,000 calls/day |
| 📰 GNews | 100 articles/day |
| ☁️ Render.com | 750 hrs/month (always free) |

---

## ⚠️ Common Issues

**Bot is slow first reply?**
→ HF free tier loads model on first call (~15-20 sec). Normal!

**Model error in reply?**
→ HF sometimes queues free requests. Just try again.

**Weather not working?**
→ Wait 10 mins after creating OpenWeatherMap key.
