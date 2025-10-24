import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY в Environment Variables")

# === Настройки Webhook ===
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# === Инициализация клиентов ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение к OpenRouter API (аналог OpenAI)
openai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

# === Утилиты ===
def split_message(text, limit=4000):
    return [text[i:i + limit] for i in range(0, len(text), limit)]

# === OpenRouter-запрос ===
async def get_openai_response(prompt: str) -> str:
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка при запросе к OpenRouter: {e}")
        return "⚠️ Ошибка при обращении к OpenRouter. Проверь ключ или попробуй позже."

# === Обработчики ===
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💬 Задать вопрос")]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я бот на базе OpenRouter (ChatGPT-модель). Напиши вопрос, и я отвечу.",
        reply_markup=keyboard
    )

async def message_handler(message: types.Message):
    await message.answer("⌛ Думаю над ответом...")
    reply = await get_openai_response(message.text)
    for chunk in split_message(reply):
        await message.answer(chunk)

# === Регистрация ===
dp.message.register(start_handler, Command("start"))
dp.message.register(message_handler)

# === Веб-сервер ===
async def handle(request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.process_update(update)
    except Exception as e:
        logger.exception(f"Ошибка при обработке апдейта: {e}")
    return web.Response()

async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("🧹 Webhook удалён при остановке")

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

# === Запуск ===
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
