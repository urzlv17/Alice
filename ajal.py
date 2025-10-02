import asyncio
import logging
import json
import os
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from flask import Flask

# .env dan o‘qish
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6067594310"))

# Kanal va kino sozlamalari
CHANNELS = [
    {"name": "Kanal 1", "link": "https://t.me/+0HH1L-dHrLdmMTUy", "id": -1003053807994},
    {"name": "Kanal 2", "link": "https://t.me/+_tOVOccPH_cwMTcy", "id": -1002758258380},
    {"name": "Kanal 3", "link": "https://t.me/+24H2NggcXrFmNjUy", "id": -1002976392716},
    {"name": "Kanal 4", "link": "https://t.me/+nJuibwCPd0Q4NmE6", "id": -1002920857610}
]

# Kino fayllari va file_id lar
MOVIES = {
    "111": "BAACAgEAAxkBAAMFaN0nSEYPOBm92m-gthAtpMhVWvQAAmgFAAKwbLlGCLXVfcF8-K42BA",
    "112": "BAACAgUAAxkBAAMJaN0nuudyinyyd1sywNXwKRyXad8AArAWAAIau7hWsTfVTjPPf2w2BA",
    "113": "BAACAgUAAxkBAAMLaN0nx2pXJyIfpLMS_vQWF5JzxsMAArMWAAIau7hWasHhn8Rimjs2BA",
    "114": "BAACAgEAAxkBAAMNaN0nx9gxQ5Bz5SoMYU8pbG5IZIsAAiIHAAKwBcBG1yEOdBkWw2I2BA",
    "115": "BAACAgUAAxkBAAMMaN0nx775kKpW3HrGmmWyolc0htMAAkUYAAJCGMBWJvA6qEiAc-c2BA",
    "116": "BAACAgUAAxkBAAMOaN0nx5LVe55nJ2UuKbQEPQABChlYAAJPGAACQhjIVilo_HEewLmkNgQ"
}

# Kino caption (hamma kinoga bir xil)
CAPTION = """🎬 Ajal O'yini

🔑 Janr: Triller | Fantastika | Hayot-mamot
📺 Fasl: 3 (Netflix Original)
⭐ Reyting: Juda yuqori, tomoshabinlar tomonidan iliq kutib olingan.
🌏 Til: Uzbek tilida"""
PENDING_FILE = "pending.json"

# Bot & dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# FSM
class CinemaStates(StatesGroup):
    waiting_for_code = State()

# Pending faylni yuklash/saqlash
def load_pending():
    if not os.path.exists(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"load_pending error: {e}")
        return {}

def save_pending(data):
    try:
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"save_pending error: {e}")

# /start handler
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_id, {}).get("confirmed"):
        await message.answer(
            "✅ Siz allaqachon tasdiqlangansiz! Kino kodini yuboring:",
            reply_markup=None
        )
        await state.set_state(CinemaStates.waiting_for_code)
        return

    text = "🎬 Assalomu alaykum!\n\nQuyidagi kanallarga obuna bo'ling:\n"

    # inline tugmalar (kanallar uchun)
    buttons = [[InlineKeyboardButton(text=f"📢 {ch['name']}", url=ch['link'])] for ch in CHANNELS]

    # "Men obuna bo‘ldim" tugmasi
    buttons.append([InlineKeyboardButton(text="✅ Men obuna bo‘ldim", callback_data="confirmed_request")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

# chat_join_request event
@dp.chat_join_request()
async def on_chat_join_request(update: types.ChatJoinRequest):
    uid = str(update.from_user.id)
    pending = load_pending()
    user_data = pending.get(uid, {})
    joined = user_data.get("joined_channels", [])
    if update.chat.id not in joined:
        joined.append(update.chat.id)
    user_data["joined_channels"] = joined
    pending[uid] = user_data
    save_pending(pending)

    try:
        await bot.send_message(
            ADMIN_ID,
            f"📥 Join request: {update.from_user.full_name} ({uid}) -> {update.chat.title}"
        )
    except Exception:
        pass

# Obuna tekshirish
@dp.callback_query(F.data == "confirmed_request")
async def confirmed_request(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_key = str(user_id)
    pending = load_pending()
    user_data = pending.get(user_key, {})

    joined = set(user_data.get("joined_channels", []))
    required = {ch["id"] for ch in CHANNELS}

    if not required.issubset(joined):
        not_requested = [ch["name"] for ch in CHANNELS if ch["id"] not in joined]
        text = "❌ Siz quyidagi kanallarga hali obuna bo'lmagansiz:\n\n"
        text += "\n".join(f"➡️ {l}" for l in not_requested)
        text += "\n\nIltimos, har bir kanalga obuna bo'ling."
        await callback.answer()
        await callback.message.edit_text(text, reply_markup=callback.message.reply_markup, parse_mode="Markdown")
        return

    # Tasdiqlangan foydalanuvchi holati va FSMni ishga tushirish
    pending[user_key] = {"confirmed": True, "joined_channels": list(joined)}
    save_pending(pending)

    await callback.message.edit_text("✅ Tabriklaymiz! Endi kino kodini yuboring (masalan: 111).", reply_markup=None)
    await state.set_state(CinemaStates.waiting_for_code)

# Kino kodi qabul qilish
@dp.message(CinemaStates.waiting_for_code)
async def receive_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    user_key = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_key) and pending[user_key].get("confirmed"):
        if code in MOVIES:
            file_id = MOVIES[code]
            await message.answer_document(file_id, caption=CAPTION)  # caption qo'shildi
            await bot.send_message(
                ADMIN_ID,
                f"🎬 Kino yuborildi: {message.from_user.full_name} ({user_key}) -> kod {code}"
            )
            return
        else:
            await message.answer("❌ Noto‘g‘ri kod! Iltimos, 111-116 orasidan birini yozing.")
            return
    else:
        await message.answer("⚠️ Avval barcha kanallarga obuna bo'ling va 'Men obuna bo‘ldim' tugmasini bosing.")

# Flask health-check
app = Flask("bot_health")
@app.route("/")
def home():
    return "OK - bot ishlayapti"

def run_flask():
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

# Bot polling run
async def run_bot():
    logging.info("Start polling")
    await dp.start_polling(bot)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
