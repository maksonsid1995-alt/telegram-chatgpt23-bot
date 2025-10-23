import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiohttp import web
import openai
from tenacity import retry, stop_after_attempt, wait_fixed

# ======== ЛОГИРОВАНИЕ ========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))  # Render задаёт свой порт через $PORT

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
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]

# ======== ОБРАБОТКА СООБЩЕНИЙ ========
@dp.message()
async def chatgpt_reply(message: types.Message):
    try:
        text = get_openai_response(message.text)
        for chunk in split_message(text):
            await message.answer(chunk)
    except Exception as e:
        await message.answer("Ошибка при обработке запроса. Попробуйте позже.")
        logger.error(f"OpenAI error: {e}")

# ======== ПРИВЕТСТВИЕ С КНОПКОЙ ========
@dp.message(commands=["start"])
async def welcome(message: types.Message):
    user_name = message.from_user.full_name
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(text="💬 Задать вопрос"))
    greeting = (
        f"Привет, {user_name}! 👋\n\n"
        "Я бот с ChatGPT. Нажми кнопку ниже, чтобы задать вопрос."
    )
    await message.answer(greeting, reply_markup=keyboard)

# ======== ВЕБ-СЕРВЕР ========
async def handle_webhook(request: web.Request):
    """Обработка входящих обновлений Telegram через webhook."""
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def on_startup(app):
    """Удаляем старый webhook и ставим новый."""
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(app):
    """Очистка webhook при выключении."""
    await bot.delete_webhook()
    logger.info("Webhook удалён при shutdown")

# ======== MAIN ========
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    logger.info(f"Сервер слушает порт {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
