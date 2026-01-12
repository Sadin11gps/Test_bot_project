import asyncio
import logging
import os
import aiosqlite
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update, Message, CallbackQuery, InlineKeyboardBuilder
from aiogram.filters import CommandStart, Command

# লগিং
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Settings
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8059084521:AAGuVxr-6-X0Izld_uOD4nazPqd3yaKQgzo"  # fallback for test
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'test-bot-project1.onrender.com')}{WEBHOOK_PATH}"

REFERRAL_BONUS = 10
BOT_USERNAME = "testing_bux_bot"  # ← তোমার আসল বটের ইউজারনেম দাও এখানে!!!

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# Router for handlers
router = Router()
dp.include_router(router)

# DB functions (same as before)
async def init_db():
    async with aiosqlite.connect('users.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                referrer_id INTEGER
            )
        ''')
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect('users.db') as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def add_user(user_id: int, username: str, referrer_id: int = None):
    async with aiosqlite.connect('users.db') as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, balance, referrer_id) VALUES (?, ?, 0, ?)",
            (user_id, username, referrer_id)
        )
        await db.commit()

        if referrer_id and referrer_id != user_id:
            await db.execute(
                "UPDATE users SET referrals = referrals + 1, balance = balance + ? WHERE user_id = ?",
                (REFERRAL_BONUS, referrer_id)
            )
            await db.commit()

# Handlers using Router
@router.message(CommandStart(deep_link=True))
async def start_with_ref(message: Message):
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    await add_user(user_id, username, referrer_id)

    text = (
        f"🌟 স্বাগতম {message.from_user.first_name}! 🌟\n\n"
        f"তোমার রেফারেল লিংক: https://t.me/{BOT_USERNAME}?start={user_id}\n\n"
        f"প্রতি সফল রেফারেলে {REFERRAL_BONUS} পয়েন্ট!\n"
        "টাস্ক দেখতে /tasks দাও"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="টাস্ক দেখি →", callback_data="show_tasks")

    await message.answer(text, reply_markup=builder.as_markup(), disable_web_page_preview=True)

@router.message(CommandStart())
async def start_command(message: Message):
    await start_with_ref(message)

@router.message(Command("balance"))
async def balance_command(message: Message):
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(f"💰 ব্যালেন্স: {user[2]} পয়েন্ট\n👥 রেফারেল: {user[3]} জন")
    else:
        await message.answer("প্রথমে /start করো!")

@router.message(Command("tasks"))
async def tasks_command(message: Message):
    await message.answer("📋 টাস্ক:\n1. চ্যানেল জয়েন → ৫ পয়েন্ট (শীঘ্রই অটো)")

# Callback handler - এটাই আগে মিসিং ছিল!
@router.callback_query(lambda c: c.data == "show_tasks")
async def show_tasks_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 টাস্ক মেনু:\n"
        "• চ্যানেল জয়েন → ৫ পয়েন্ট\n"
        "• পোস্ট শেয়ার → ৩ পয়েন্ট\n\n"
        "আরো আসছে শীঘ্রই! 🚀"
    )
    await callback.answer()  # Progress bar বন্ধ করার জন্য

# Webhook
@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await init_db()
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set: {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
