import os
import json
import logging
import aiohttp
import asyncio
from pathlib import Path
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ChatAction

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID        = int(os.getenv("ADMIN_ID", "0"))   # Your Telegram user ID

# Keys file — persists on disk so they survive restarts
KEYS_FILE    = "keys.json"
MEMORY_FILE  = "memory.json"

# ─── JARVIS PERSONALITY ───────────────────────────────────────────────────────
JARVIS_SYSTEM = """You are JARVIS — an advanced AI assistant, witty, intelligent and loyal.
You speak like the JARVIS from Iron Man:
- Address the user as "Sir" or "Boss" occasionally
- Be confident, clever and slightly humorous
- Give precise, helpful answers
- If asked to do something you can't, say so honestly but creatively
- Keep responses conversational, not too long unless asked
- You have memory of past conversations with the user
You are powered by Mistral AI and were built by the user's developer."""

# Logging
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── KEYS MANAGER ─────────────────────────────────────────────────────────────

def load_keys() -> dict:
    defaults = {
        "HF_API_KEY":      os.getenv("HF_API_KEY", ""),
        "WEATHER_API_KEY": os.getenv("WEATHER_API_KEY", ""),
        "GNEWS_API_KEY":   os.getenv("GNEWS_API_KEY", ""),
    }
    if Path(KEYS_FILE).exists():
        try:
            saved = json.loads(Path(KEYS_FILE).read_text())
            defaults.update({k: v for k, v in saved.items() if v})
        except Exception:
            pass
    return defaults

def save_keys(keys: dict):
    Path(KEYS_FILE).write_text(json.dumps(keys, indent=2))

KEYS = load_keys()

def get_key(name: str) -> str:
    return KEYS.get(name, "")

# ─── PERMANENT MEMORY ─────────────────────────────────────────────────────────

def load_memory() -> dict:
    if Path(MEMORY_FILE).exists():
        try:
            return json.loads(Path(MEMORY_FILE).read_text())
        except Exception:
            pass
    return {}

def save_memory(memory: dict):
    Path(MEMORY_FILE).write_text(json.dumps(memory, indent=2))

def get_user_history(uid: int) -> list:
    memory = load_memory()
    return memory.get(str(uid), [])

def append_user_history(uid: int, user_msg: str, bot_msg: str):
    memory = load_memory()
    key = str(uid)
    if key not in memory:
        memory[key] = []
    memory[key].append({"user": user_msg, "bot": bot_msg})
    # Keep last 30 exchanges
    if len(memory[key]) > 30:
        memory[key] = memory[key][-30:]
    save_memory(memory)

def clear_user_history(uid: int):
    memory = load_memory()
    memory[str(uid)] = []
    save_memory(memory)

# ─── HUGGING FACE CHAT ────────────────────────────────────────────────────────

HF_MODEL   = "mistralai/Mistral-7B-Instruct-v0.3"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

def build_prompt(history: list, user_msg: str) -> str:
    prompt = f"<s>[INST] <<SYS>>\n{JARVIS_SYSTEM}\n<</SYS>>\n\n"
    for turn in history[-6:]:
        prompt += f"{turn['user']} [/INST] {turn['bot']} </s><s>[INST] "
    prompt += f"{user_msg} [/INST]"
    return prompt

async def ask_hf(prompt: str) -> str:
    hf_key = get_key("HF_API_KEY")
    if not hf_key:
        return "⚠️ No Hugging Face API key set. Use `/setkey HF_API_KEY your_key` to set it."

    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 600,
            "temperature": 0.75,
            "repetition_penalty": 1.2,
            "return_full_text": False
        }
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                HF_API_URL, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                data = await resp.json()

            # Model loading — wait and retry once
            if isinstance(data, dict) and "loading" in data.get("error", "").lower():
                wait = data.get("estimated_time", 20)
                await asyncio.sleep(min(wait, 30))
                async with session.post(
                    HF_API_URL, headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp2:
                    data = await resp2.json()

        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "").strip()
            # Clean up any leftover prompt artifacts
            for tag in ["[INST]", "[/INST]", "<<SYS>>", "<</SYS>>", "<s>", "</s>"]:
                text = text.replace(tag, "")
            return text.strip() or "I seem to have nothing to say, Sir. Try again."
        if isinstance(data, dict) and "error" in data:
            return f"⚠️ AI error: {data['error']}"
        return "⚠️ No response from AI."
    except asyncio.TimeoutError:
        return "⚠️ AI took too long to respond, Sir. Please try again."
    except Exception as e:
        logger.error(f"HF error: {e}")
        return "⚠️ AI service hiccup. Please try again."

# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def typing(update: Update):
    await update.effective_chat.send_action(ChatAction.TYPING)

def is_admin(uid: int) -> bool:
    return ADMIN_ID == 0 or uid == ADMIN_ID

# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Sir"
    text = (
        f"🤖 *Good day, {name}. JARVIS online.*\n\n"
        "I am your personal AI assistant — witty, capable, and at your service.\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💬 *Just send any message* to chat with me\n"
        "🔍 `/search <query>` — Web search\n"
        "🌤 `/weather <city>` — Live weather\n"
        "📰 `/news <topic>` — Latest news\n"
        "🎨 `/image <prompt>` — Generate image\n"
        "📁 *Send any file/PDF* — I'll summarize it\n"
        "🔑 `/setkey NAME value` — Update API keys\n"
        "🔑 `/showkeys` — View current keys\n"
        "🗑 `/clear` — Wipe my memory of you\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "_Powered by Mistral AI · Hugging Face · Pollinations_\n"
        "_100% free. No credit card. Ever._"
    )
    keyboard = [
        [InlineKeyboardButton("🔍 Search",  callback_data="menu_search"),
         InlineKeyboardButton("🌤 Weather", callback_data="menu_weather")],
        [InlineKeyboardButton("📰 News",    callback_data="menu_news"),
         InlineKeyboardButton("🎨 Image",   callback_data="menu_image")],
        [InlineKeyboardButton("🔑 Set Key", callback_data="menu_setkey"),
         InlineKeyboardButton("🗑 Clear Memory", callback_data="menu_clear")],
    ]
    await update.message.reply_markdown(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
        "menu_image":   "🎨 Usage: `/image dragon flying over a city at night`",
        "menu_setkey":  "🔑 Usage: `/setkey HF_API_KEY hf_xxxxxxxx`\n\nAvailable keys:\n• `HF_API_KEY`\n• `WEATHER_API_KEY`\n• `GNEWS_API_KEY`",
        "menu_clear":   None,
    }
    if q.data == "menu_clear":
        clear_user_history(q.from_user.id)
        await q.message.reply_text("🗑 Memory wiped clean, Sir.")
    else:
        await q.message.reply_markdown(tips.get(q.data, "Unknown option."))

# ─── AI CHAT ──────────────────────────────────────────────────────────────────

async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid       = update.effective_user.id
    user_text = update.message.text.strip()

    await typing(update)

    history = get_user_history(uid)
    prompt  = build_prompt(history, user_text)
    reply   = await ask_hf(prompt)

    append_user_history(uid, user_text, reply)

    for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
        await update.message.reply_text(chunk)

# ─── /clear ───────────────────────────────────────────────────────────────────

async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    clear_user_history(update.effective_user.id)
    await update.message.reply_text("🗑 Memory cleared, Sir. We start fresh.")

# ─── /setkey ──────────────────────────────────────────────────────────────────

async def setkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Only the admin can update API keys.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_markdown(
            "Usage: `/setkey KEY_NAME your_value`\n\n"
            "Available keys:\n"
            "• `HF_API_KEY` — Hugging Face token\n"
            "• `WEATHER_API_KEY` — OpenWeatherMap\n"
            "• `GNEWS_API_KEY` — GNews\n\n"
            "Example: `/setkey HF_API_KEY hf_aBcDeFgH`"
        )
        return

    key_name  = ctx.args[0].upper()
    key_value = ctx.args[1].strip()
    allowed   = ["HF_API_KEY", "WEATHER_API_KEY", "GNEWS_API_KEY"]

    if key_name not in allowed:
        await update.message.reply_text(
            f"❌ Unknown key '{key_name}'.\nAllowed: {', '.join(allowed)}"
        )
        return

    KEYS[key_name] = key_value
    save_keys(KEYS)

    # Delete the message so key isn't visible in chat
    try:
        await update.message.delete()
    except Exception:
        pass

    await update.effective_chat.send_message(
        f"✅ `{key_name}` updated successfully, Sir! Key saved permanently.",
        parse_mode="Markdown"
    )

# ─── /showkeys ────────────────────────────────────────────────────────────────

async def showkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Admin only.")
        return

    lines = ["🔑 *Current API Keys:*\n"]
    for k, v in KEYS.items():
        if v:
            masked = v[:6] + "..." + v[-4:] if len(v) > 10 else "****"
            lines.append(f"✅ `{k}`: `{masked}`")
        else:
            lines.append(f"❌ `{k}`: _not set_")

    await update.message.reply_markdown("\n".join(lines))

# ─── /search ──────────────────────────────────────────────────────────────────

async def search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args)
    if not query:
        await update.message.reply_text("Usage: `/search your query`", parse_mode="Markdown")
        return

    await typing(update)
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
            lines.append("No results found. Try a different query, Sir.")

        await update.message.reply_markdown("\n".join(lines))
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("⚠️ Search service unavailable.")

# ─── /weather ─────────────────────────────────────────────────────────────────

async def weather(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    city = " ".join(ctx.args)
    if not city:
        await update.message.reply_text("Usage: `/weather London`", parse_mode="Markdown")
        return

    w_key = get_key("WEATHER_API_KEY")
    if not w_key:
        await update.message.reply_text("⚠️ No weather key. Use `/setkey WEATHER_API_KEY your_key`", parse_mode="Markdown")
        return

    await typing(update)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={quote(city)}&appid={w_key}&units=metric"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 404:
                    await update.message.reply_text(f"❌ City '{city}' not found, Sir.")
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
            "clear sky":"☀️","few clouds":"🌤","scattered clouds":"⛅",
            "broken clouds":"🌥","overcast clouds":"☁️","shower rain":"🌧",
            "rain":"🌧","light rain":"🌦","thunderstorm":"⛈","snow":"❄️",
            "mist":"🌫","haze":"🌫","fog":"🌫"
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
    topic  = " ".join(ctx.args) or "world"
    n_key  = get_key("GNEWS_API_KEY")
    if not n_key:
        await update.message.reply_text("⚠️ No GNews key. Use `/setkey GNEWS_API_KEY your_key`", parse_mode="Markdown")
        return

    await typing(update)
    url = f"https://gnews.io/api/v4/search?q={quote(topic)}&lang=en&max=5&apikey={n_key}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()

        articles = data.get("articles", [])
        if not articles:
            await update.message.reply_text(f"No news found for '{topic}', Sir.")
            return

        lines = [f"📰 *Top News: {topic.title()}*\n"]
        for i, a in enumerate(articles, 1):
            title  = a.get("title", "No title")[:100]
            source = a.get("source", {}).get("name", "Unknown")
            link   = a.get("url", "")
            lines.append(f"{i}. *{title}*\n   _{source}_ — [Read]({link})")

        await update.message.reply_markdown("\n\n".join(lines), disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("⚠️ News service unavailable.")

# ─── /image ───────────────────────────────────────────────────────────────────

async def image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(ctx.args)
    if not prompt:
        await update.message.reply_text("Usage: `/image a cat astronaut on the moon`", parse_mode="Markdown")
        return

    await update.effective_chat.send_action(ChatAction.UPLOAD_PHOTO)
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
        await update.message.reply_text("⚠️ Image service timed out. Please try again.")

# ─── FILE / PDF HANDLER ───────────────────────────────────────────────────────

async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg        = update.message
    file_obj   = None
    file_name  = "file"
    is_pdf     = False

    if msg.document:
        doc       = msg.document
        file_name = doc.file_name or "document"
        is_pdf    = file_name.lower().endswith(".pdf") or doc.mime_type == "application/pdf"
        file_obj  = await ctx.bot.get_file(doc.file_id)
    elif msg.photo:
        photo     = msg.photo[-1]   # highest resolution
        file_name = "image.jpg"
        file_obj  = await ctx.bot.get_file(photo.file_id)

    if not file_obj:
        await msg.reply_text("⚠️ Could not process that file type, Sir.")
        return

    await typing(update)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_obj.file_path, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                file_bytes = await resp.read()

        if is_pdf:
            # Extract text from PDF using PyMuPDF if available, else raw bytes hint
            try:
                import fitz  # PyMuPDF
                doc_pdf = fitz.open(stream=file_bytes, filetype="pdf")
                text = ""
                for page in doc_pdf:
                    text += page.get_text()
                doc_pdf.close()
                text = text[:3000]  # limit to 3000 chars for HF
                user_prompt = f"Please summarize this PDF document concisely:\n\n{text}"
            except ImportError:
                await msg.reply_text(
                    "⚠️ PDF reading library not installed on server.\n"
                    "Add `PyMuPDF` to requirements.txt and redeploy, Sir."
                )
                return
        elif file_name.lower().endswith((".txt", ".md", ".py", ".js", ".html", ".csv")):
            text        = file_bytes.decode("utf-8", errors="ignore")[:3000]
            user_prompt = f"Please summarize or explain this file ({file_name}):\n\n{text}"
        elif file_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            await msg.reply_text(
                "🖼 Image received! For image analysis, an AI vision model is needed.\n"
                "Currently I can only analyse text files and PDFs. "
                "Type a question about what you want to know!"
            )
            return
        else:
            await msg.reply_text(
                f"📁 I received *{file_name}*.\n"
                "I can summarize: PDF, TXT, MD, PY, JS, HTML, CSV files.\n"
                "Send one of those and I'll get right on it, Sir!",
                parse_mode="Markdown"
            )
            return

        uid     = update.effective_user.id
        history = get_user_history(uid)
        prompt  = build_prompt(history, user_prompt)
        reply   = await ask_hf(prompt)

        append_user_history(uid, f"[File: {file_name}]", reply)

        await msg.reply_text(f"📄 *Summary of {file_name}:*\n\n{reply}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"File handler error: {e}")
        await msg.reply_text("⚠️ Error processing your file. Please try again.")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("help",     help_cmd))
    app.add_handler(CommandHandler("clear",    clear))
    app.add_handler(CommandHandler("search",   search))
    app.add_handler(CommandHandler("weather",  weather))
    app.add_handler(CommandHandler("news",     news))
    app.add_handler(CommandHandler("image",    image))
    app.add_handler(CommandHandler("setkey",   setkey))
    app.add_handler(CommandHandler("showkeys", showkeys))
    app.add_handler(CallbackQueryHandler(button_handler))

    # File & photo handler
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO, handle_file
    ))
    # Text chat (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("🤖 JARVIS ONLINE — Full Edition")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
