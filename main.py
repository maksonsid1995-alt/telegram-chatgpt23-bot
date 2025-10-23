import os
import openai
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiohttp import web
from tenacity import retry, stop_after_attempt, wait_fixed

# ======== ЛОГИРОВАНИЕ ========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY в Environment Variables")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ======== ИНИЦИАЛИЗАЦИЯ ========
openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ======== ФУНКЦИИ ========
def split_message(text, limit=4000):
    """Разделение длинного текста на части для Telegram."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_openai_response(prompt: str):
    """Запрос к OpenAI с повторными попытками при сбоях."""
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

# ======== ПРИВЕТСТВИЕ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ ========
@dp.message(commands=["start"])
async def welcome(message: types.Message):
    user_name = message.from_user.full_name
    greeting = (
        f"Привет, {user_name}! 👋\n\n"
        "Я бот с ChatGPT. Можешь писать мне любые вопросы, "
        "и я постараюсь дать развёрнутый ответ. 😊"
    )
    await message.answer(greeting)

# ======== ОБРАБОТКА СООБЩЕНИЙ ========
@dp.message()
async def chatgpt_reply(message: types.Message):
    try:
        response = get_openai_response(message.text)
        text = response.choices[0].message["content"]
        for chunk in split_message(text):
            await message.answer(chunk)
    except Exception as e:
        await message.answer("Ошибка при обработке запроса. Попробуйте позже.")
        logger.error(f"OpenAI error: {e}")

# ======== ЗАПУСК WEBHOOK ========
async def on_startup():
    """Удаляем старый webhook и ставим новый."""
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown():
    """Очистка webhook при выключении."""
    await bot.delete_webhook()
    logger.info("Webhook удалён при shutdown")

async def main():
    # Старт webhook сервера
    await on_startup()
    await dp.start_webhook(
        webhook_path=WEBHOOK_PATH,
        host="0.0.0.0",
        port=PORT,
        bot=bot,
        on_shutdown=on_shutdown
    )

if __name__ == "__main__":
    asyncio.run(main())