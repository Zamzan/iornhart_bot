# 🤖 JARVIS Bot V2 — Full Edition

> Permanent Memory · Custom Personality · API Key Manager · File/PDF Reader
> 100% Free · No Credit Card · 24/7 Online

---

## ✨ New Features in V2

| Feature | Description |
|---|---|
| 🧠 Permanent Memory | Remembers ALL past chats even after restart |
| 🎭 JARVIS Personality | Talks like Iron Man's JARVIS — calls you "Sir" |
| 🔑 Live API Key Updates | Change API keys via Telegram chat (no redeploy!) |
| 📁 File & PDF Reader | Send any PDF/TXT/code file — JARVIS summarizes it |

---

## 🔑 STEP 1 — Get Free API Keys

### 1. 🤗 Hugging Face Token (REQUIRED)
1. Go to → https://huggingface.co/join
2. Create free account
3. Go to → https://huggingface.co/settings/tokens
4. Click "New token" → Role: **Read** → Copy token (`hf_...`)

### 2. 🤖 Telegram Bot Token (REQUIRED)
1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow steps → copy token

### 3. 🆔 Your Telegram User ID (REQUIRED for security)
1. Open Telegram → search **@userinfobot**
2. Send `/start` → it shows your numeric ID
3. Copy that number (e.g. `123456789`)

### 4. 🌤 OpenWeatherMap Key (optional)
- Register at → https://openweathermap.org/api
- Go to API Keys → copy key (wait 10 min to activate)

### 5. 📰 GNews Key (optional)
- Register at → https://gnews.io
- Copy key from dashboard

---

## 🚀 STEP 2 — Deploy on Render.com (Free 24/7)

### A) Push to GitHub
```bash
git init
git add .
git commit -m "JARVIS V2"
git remote add origin https://github.com/YOUR_USERNAME/jarvis-v2.git
git push -u origin main
```

### B) Deploy on Render
1. Go to → https://render.com → sign up free
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub repo
4. Add Environment Variables:

| Key | Value |
|---|---|
| `TELEGRAM_TOKEN` | your telegram token |
| `HF_API_KEY` | your hf_xxx token |
| `ADMIN_ID` | your telegram numeric ID |
| `WEATHER_API_KEY` | your openweathermap key |
| `GNEWS_API_KEY` | your gnews key |

5. Click **"Deploy"** ✅

---

## 💻 Run Locally (Testing)

```bash
pip install -r requirements.txt

# Linux/Mac
export TELEGRAM_TOKEN="xxx"
export HF_API_KEY="hf_xxx"
export ADMIN_ID="123456789"
export WEATHER_API_KEY="xxx"
export GNEWS_API_KEY="xxx"

# Windows PowerShell
$env:TELEGRAM_TOKEN="xxx"
$env:HF_API_KEY="hf_xxx"
$env:ADMIN_ID="123456789"

python bot.py
```

---

## 📱 All Commands

| Command | What it does |
|---|---|
| Any message | AI chat with JARVIS personality + memory |
| `/search query` | DuckDuckGo web search |
| `/weather city` | Live weather |
| `/news topic` | Latest news |
| `/image prompt` | Generate AI image (Pollinations) |
| `/setkey NAME value` | Update any API key live (admin only) |
| `/showkeys` | View masked API key status (admin only) |
| `/clear` | Clear your chat memory |
| `/help` | Show all commands |
| Send PDF/TXT/code file | JARVIS summarizes it |

---

## 🔑 Updating API Keys via Telegram

No need to redeploy! Just send:
```
/setkey HF_API_KEY hf_newkeyhere
/setkey WEATHER_API_KEY newweatherkey
/setkey GNEWS_API_KEY newgnewskey
```
JARVIS will save the key, delete your message for security, and confirm.

---

## 🆓 Everything Free

| Service | Free Limit |
|---|---|
| 🤗 Mistral-7B (HF) | Unlimited personal use |
| 🎨 Pollinations Images | Unlimited |
| 🔍 DuckDuckGo Search | Unlimited |
| 🌤 OpenWeatherMap | 1,000 calls/day |
| 📰 GNews | 100 articles/day |
| ☁️ Render.com | 750 hrs/month |

---

## ⚠️ Notes

- First reply may take ~15–20 sec (HF model loading)
- Memory is saved in `memory.json` on the server
- API keys are saved in `keys.json` on the server
- On Render free tier, files persist between restarts ✅
