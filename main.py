import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import AsyncOpenAI

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://telegram-chatgpt23-bot.onrender.com"  # замени на свой, если другой

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("❌ Не заданы BOT_TOKEN или OPENAI_API_KEY в Render Environment Variables")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"

# === ОБЪЕКТЫ ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def split_message(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

# === ОБРАБОТЧИК /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💬 Задать вопрос")]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        f"Напиши мне вопрос — и я отвечу как ChatGPT.",
        reply_markup=keyboard
    )

# === ОБРАБОТЧИК ЛЮБОГО ТЕКСТА ===
@dp.message(F.text)
async def handle_message(message: types.Message):
    user_text = message.text.strip()
    await message.answer("⌛ Думаю над ответом...")

    try:
        completion = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_text}]
        )
        response = completion.choices[0].message.content
        for chunk in split_message(response):
            await message.answer(chunk)
    except Exception as e:
        logger.exception(e)
        await message.answer("⚠️ Ошибка при обработке запроса. Попробуйте позже.")

# === ВЕБХУК-СЕРВЕР ===
async def handle_webhook(request):
    try:
        update = types.Update(**await request.json())
        await dp.feed_update(bot, update)
        return web.Response()
    except Exception as e:
        logger.error(f"Ошибка обработки апдейта: {e}")
        return web.Response(status=500)

async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("🧹 Webhook удалён при остановке")

# === ИНИЦИАЛИЗАЦИЯ СЕРВЕРА ===
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    logger.info(f"🚀 Запуск на порту {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
