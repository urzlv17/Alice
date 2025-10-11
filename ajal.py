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

# Kanal sozlamalari
CHANNELS = [
    {"name": "Kanal 1", "link": "https://t.me/+g5pGoUg7fbkwNzM1", "id": -1003000935874}
]

# Kino fayllari (file_id lar)
MOVIES = {
    "111": "BAACAgEAAxkBAAMFaN0nSEYPOBm92m-gthAtpMhVWvQAAmgFAAKwbLlGCLXVfcF8-K42BA",
    "112": "BAACAgUAAxkBAAMJaN0nuudyinyyd1sywNXwKRyXad8AArAWAAIau7hWsTfVTjPPf2w2BA",
    "113": "BAACAgUAAxkBAAMLaN0nx2pXJyIfpLMS_vQWF5JzxsMAArMWAAIau7hWasHhn8Rimjs2BA",
    "114": "BAACAgEAAxkBAAMNaN0nx9gxQ5Bz5SoMYU8pbG5IZIsAAiIHAAKwBcBG1yEOdBkWw2I2BA",
    "115": "BAACAgUAAxkBAAMMaN0nx775kKpW3HrGmmWyolc0htMAAkUYAAJCGMBWJvA6qEiAc-c2BA",
    "116": "BAACAgUAAxkBAAMOaN0nx5LVe55nJ2UuKbQEPQABChlYAAJPGAACQhjIVilo_HEewLmkNgQ"
}

# Kino caption
CAPTION = """🎬 Ajal O'yini
🔑 Janr: Triller | Fantastika | Hayot-mamot
📺 Fasl: 3 (Netflix Original)
⭐ Reyting: Juda yuqori
🌏 Til: Uzbek tilida"""

PENDING_FILE = "pending.json"

# Bot & Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


# FSM (kino kodi uchun)
class CinemaStates(StatesGroup):
    waiting_for_code = State()


# Pending saqlash funksiyalari
def load_pending():
    if not os.path.exists(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error("load_pending error", exc_info=True)
        return {}


def save_pending(data):
    try:
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error("save_pending error", exc_info=True)


# /start handler
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_id, {}).get("confirmed"):
        await message.answer("✅ Siz allaqachon tasdiqlangansiz! Kino kodini yuboring:")
        await state.set_state(CinemaStates.waiting_for_code)
        return

    text = "🎬 Assalomu alaykum!\n\nQuyidagi kanallarga obuna bo‘ling:"
    buttons = [
        [InlineKeyboardButton(text=f"📢 {ch['name']}", url=ch["link"])]
        for ch in CHANNELS
    ]
    buttons.append([InlineKeyboardButton(text="✅ Men obuna bo‘ldim", callback_data="confirmed_request")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text, reply_markup=markup)


# Obuna tekshirish (real-time)
@dp.callback_query(F.data == "confirmed_request")
async def confirmed_request(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_key = str(user_id)
    pending = load_pending()

    not_joined = []
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)

    if not_joined:
        buttons = [
            [InlineKeyboardButton(text=f"📢 {ch['name']}", url=ch["link"])]
            for ch in not_joined
        ]
        buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="confirmed_request")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = "❌ Siz hali quyidagi kanallarga obuna bo‘lmadingiz:\n\n"
        text += "\n".join(f"➡️ {ch['name']}" for ch in not_joined)
        text += "\n\nIltimos, obuna bo‘lib, '✅ Tekshirish' tugmasini bosing."

        await callback.message.edit_text(text, reply_markup=markup)
        await callback.answer()
        return

    # Agar hammasiga obuna bo‘lsa
    pending[user_key] = {"confirmed": True}
    save_pending(pending)

    await callback.message.edit_text("✅ Tabriklaymiz! Endi kino kodini yuboring (masalan: 111).")
    await state.set_state(CinemaStates.waiting_for_code)
    await callback.answer("Tasdiqlandi!")


# Kino kodi qabul qilish
@dp.message(CinemaStates.waiting_for_code)
async def receive_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    user_key = str(message.from_user.id)
    pending = load_pending()

    if pending.get(user_key, {}).get("confirmed"):
        if code in MOVIES:
            file_id = MOVIES[code]
            await message.answer_document(file_id, caption=CAPTION)
            await bot.send_message(
                ADMIN_ID,
                f"🎬 Kino yuborildi: {message.from_user.full_name} ({user_key}) -> kod {code}"
            )
        else:
            await message.answer("❌ Noto‘g‘ri kod! Iltimos, 111–116 orasidan birini yozing.")
    else:
        await message.answer("⚠️ Avval barcha kanallarga obuna bo‘ling va 'Men obuna bo‘ldim' tugmasini bosing.")


# Flask health-check
app = Flask("bot_health")


@app.route("/")
def home():
    return "OK - bot ishlayapti"


def run_flask():
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)


# Botni ishga tushirish
async def run_bot():
    logging.info("Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
