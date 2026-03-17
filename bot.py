import os
import logging
import aiohttp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ChatAction

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
HF_API_KEY      = os.getenv("HF_API_KEY")          # huggingface.co (free)
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")      # openweathermap.org (free)
GNEWS_API_KEY   = os.getenv("GNEWS_API_KEY")        # gnews.io (free)

# Best free HuggingFace model for chat (no GPU required)
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Per-user chat history (in-memory, last 10 messages)
user_histories: dict[int, list] = {}

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_history(uid: int) -> list:
    if uid not in user_histories:
        user_histories[uid] = []
    return user_histories[uid]

def build_prompt(history: list, user_msg: str) -> str:
    """Build Mistral instruct-format prompt with history."""
    prompt = "<s>"
    for turn in history[-8:]:   # last 4 exchanges
        prompt += f"[INST] {turn['user']} [/INST] {turn['bot']} </s>"
    prompt += f"[INST] {user_msg} [/INST]"
    return prompt

async def typing(update: Update):
    await update.effective_chat.send_action(ChatAction.TYPING)

# ─── HUGGING FACE INFERENCE ───────────────────────────────────────────────────

async def ask_hf(prompt: str) -> str:
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7,
            "repetition_penalty": 1.15,
            "return_full_text": False
        }
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                HF_API_URL, headers=HEADERS, json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                data = await resp.json()

                # Model loading — retry once
                if isinstance(data, dict) and data.get("error", "").startswith("Model"):
                    await asyncio.sleep(20)
                    async with session.post(
                        HF_API_URL, headers=HEADERS, json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp2:
                        data = await resp2.json()

                if isinstance(data, list) and data:
                    return data[0].get("generated_text", "").strip()
                if isinstance(data, dict) and "error" in data:
                    return f"⚠️ Model error: {data['error']}"
                return "⚠️ No response from AI."
    except asyncio.TimeoutError:
        return "⚠️ AI took too long to respond. Please try again."
    except Exception as e:
        logger.error(f"HF error: {e}")
        return "⚠️ AI service error. Try again."

# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "there"
    text = (
        f"👋 Hey *{name}*! I'm *JARVIS* — your free AI assistant.\n\n"
        "🧠 *Powered by Mistral AI (Hugging Face — 100% Free)*\n\n"
        "Here's what I can do:\n"
        "🤖 Just *send any message* to chat with AI!\n"
        "🔍 `/search <query>` — Search the web\n"
        "🌤 `/weather <city>` — Live weather\n"
        "📰 `/news <topic>` — Latest news\n"
        "🎨 `/image <prompt>` — Generate AI image (free!)\n"
        "🗑 `/clear` — Clear my memory\n"
        "ℹ️ `/help` — Show this menu\n\n"
        "_No credit card. No limits. 100% free forever._"
    )
    keyboard = [
        [InlineKeyboardButton("🔍 Search",  callback_data="menu_search"),
         InlineKeyboardButton("🌤 Weather", callback_data="menu_weather")],
        [InlineKeyboardButton("📰 News",    callback_data="menu_news"),
         InlineKeyboardButton("🎨 Image",   callback_data="menu_image")],
    ]
    await update.message.reply_markdown(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── /help ────────────────────────────────────────────────────────────────────

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)

# ─── INLINE BUTTONS ───────────────────────────────────────────────────────────

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tips = {
        "menu_search":  "🔍 Usage: `/search latest AI news`",
        "menu_weather": "🌤 Usage: `/weather Dubai`",
        "menu_news":    "📰 Usage: `/news cricket`",
        "menu_image":   "🎨 Usage: `/image dragon flying over mountains`",
    }
    await q.message.reply_markdown(tips.get(q.data, "Unknown option."))

# ─── AI CHAT ──────────────────────────────────────────────────────────────────

async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_text = update.message.text.strip()

    await typing(update)

    history = get_history(uid)
    prompt  = build_prompt(history, user_text)
    reply   = await ask_hf(prompt)

    # Save to history
    history.append({"user": user_text, "bot": reply})
    if len(history) > 20:
        user_histories[uid] = history[-20:]

    # Send in chunks if too long
    for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
        await update.message.reply_text(chunk)

# ─── /clear ───────────────────────────────────────────────────────────────────

async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text("🗑 Memory cleared! Fresh start.")

# ─── /search ──────────────────────────────────────────────────────────────────

async def search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args)
    if not query:
        await update.message.reply_text("Usage: `/search your query`", parse_mode="Markdown")
        return

    await typing(update)
    from urllib.parse import quote
    url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1&skip_disambig=1"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)

        abstract     = data.get("AbstractText", "")
        abstract_url = data.get("AbstractURL", "")
        related      = data.get("RelatedTopics", [])[:5]

        lines = [f"🔍 *Search: {query}*\n"]
        if abstract:
            lines.append(f"📄 {abstract[:500]}\n")
            if abstract_url:
                lines.append(f"🔗 {abstract_url}\n")
        else:
            lines.append("_Showing related results:_\n")
            for t in related:
                if isinstance(t, dict) and "Text" in t:
                    lines.append(f"• {t['Text'][:120]}\n  {t.get('FirstURL','')}")

        if len(lines) == 1:
            lines.append("No results found. Try a different query.")

        await update.message.reply_markdown("\n".join(lines))
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ Search failed. Try again.")

# ─── /weather ─────────────────────────────────────────────────────────────────

async def weather(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    city = " ".join(ctx.args)
    if not city:
        await update.message.reply_text("Usage: `/weather London`", parse_mode="Markdown")
        return

    await typing(update)
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 404:
                    await update.message.reply_text(f"❌ City '{city}' not found.")
                    return
                data = await resp.json()

        desc     = data["weather"][0]["description"].capitalize()
        temp     = data["main"]["temp"]
        feels    = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        wind     = data["wind"]["speed"]
        country  = data["sys"]["country"]
        name     = data["name"]

        emoji_map = {
            "clear sky": "☀️", "few clouds": "🌤", "scattered clouds": "⛅",
            "broken clouds": "🌥", "overcast clouds": "☁️",
            "shower rain": "🌧", "rain": "🌧", "light rain": "🌦",
            "thunderstorm": "⛈", "snow": "❄️", "mist": "🌫", "haze": "🌫"
        }
        icon = next((v for k, v in emoji_map.items() if k in desc.lower()), "🌡")

        msg = (
            f"{icon} *Weather in {name}, {country}*\n\n"
            f"🌡 Temp: *{temp}°C* (feels like {feels}°C)\n"
            f"💧 Humidity: *{humidity}%*\n"
            f"💨 Wind: *{wind} m/s*\n"
            f"📋 Condition: *{desc}*"
        )
        await update.message.reply_markdown(msg)
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("⚠️ Weather service unavailable.")

# ─── /news ────────────────────────────────────────────────────────────────────

async def news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(ctx.args) or "world"
    await typing(update)
    url = (
        f"https://gnews.io/api/v4/search"
        f"?q={topic}&lang=en&max=5&apikey={GNEWS_API_KEY}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()

        articles = data.get("articles", [])
        if not articles:
            await update.message.reply_text(f"No news found for '{topic}'.")
            return

        lines = [f"📰 *Top News: {topic.title()}*\n"]
        for i, a in enumerate(articles, 1):
            title  = a.get("title", "No title")[:100]
            source = a.get("source", {}).get("name", "Unknown")
            link   = a.get("url", "")
            lines.append(f"{i}. *{title}*\n   _{source}_ — [Read]({link})")

        await update.message.reply_markdown(
            "\n\n".join(lines), disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("⚠️ News service unavailable.")

# ─── /image ───────────────────────────────────────────────────────────────────

async def image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(ctx.args)
    if not prompt:
        await update.message.reply_text(
            "Usage: `/image a cat astronaut on the moon`", parse_mode="Markdown"
        )
        return

    await update.effective_chat.send_action(ChatAction.UPLOAD_PHOTO)

    from urllib.parse import quote
    # Pollinations.ai — completely free, no key needed
    image_url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=768&height=768&nologo=true&enhance=true"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    await update.message.reply_photo(
                        photo=img_bytes,
                        caption=f"🎨 *{prompt}*",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text("⚠️ Image generation failed. Try a different prompt.")
    except Exception as e:
        logger.error(f"Image error: {e}")
        await update.message.reply_text("⚠️ Image timed out. Please try again.")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_cmd))
    app.add_handler(CommandHandler("clear",   clear))
    app.add_handler(CommandHandler("search",  search))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("news",    news))
    app.add_handler(CommandHandler("image",   image))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("🤖 JARVIS is online — Powered by Hugging Face (Free)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
