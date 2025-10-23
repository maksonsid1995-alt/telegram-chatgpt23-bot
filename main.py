import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import openai

# ===== ЛОГИРОВАНИЕ =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY в Environment Variables")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ===== ИНИЦИАЛИЗАЦИЯ =====
openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== ФУНКЦИИ =====
def split_message(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def get_openai_response(prompt: str):
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]

# ===== КНОПКА СТАРТ =====
@dp.message()
async def welcome(message: types.Message):
    if message.text.lower() in ["/start", "start", "начать", "старт"]:
        user_name = message.from_user.full_name
        greeting = (
            f"Привет, {user_name}! 👋\n\n"
            "Я бот с ChatGPT. Можешь писать мне любые вопросы, "
            "и я постараюсь дать развёрнутый ответ. 😊"
        )
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Старт")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(greeting, reply_markup=keyboard)

# ===== ОБРАБОТКА СООБЩЕНИЙ =====
@dp.message()
async def chatgpt_reply(message: types.Message):
    if message.text.lower() in ["старт", "/start"]:
        return
    try:
        text = await get_openai_response(message.text)
        for chunk in split_message(text):
            await message.answer(chunk)
    except Exception as e:
        await message.answer("Ошибка при обработке запроса. Попробуйте позже.")
        logger.error(f"OpenAI error: {e}")

# ===== ROOT ОБРАБОТЧИК =====
async def root_handler(request):
    return web.Response(text="🤖 Telegram ChatGPT бот работает! Отправьте /start в Telegram.", content_type="text/plain")

# ===== WEBHOOK =====
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    logger.info("Webhook удалён при shutdown")

async def main():
    # Создаём веб-приложение aiohttp
    app = web.Application()
    app.router.add_get("/", root_handler)

    await on_startup()
    await dp.start_webhook(
        webhook_path=WEBHOOK_PATH,
        host="0.0.0.0",
        port=PORT,
        bot=bot,
        on_shutdown=on_shutdown
    )
    # Запуск aiohttp сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"Сервер слушает порт {PORT}")

if __name__ == "__main__":
    asyncio.run(main())