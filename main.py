import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import openai
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======== Переменные окружения ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY в Environment Variables")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ======== Инициализация бота и openai ========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

# ======== Функции ========
def split_message(text: str, limit: int = 4000):
    """Разделяем длинные ответы на части для Telegram."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def get_openai_response(prompt: str) -> str:
    """Асинхронный запрос к ChatGPT через новый API."""
    response = await openai.chat.completions.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ======== Обработчики ========
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💬 Задать вопрос")]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Напиши мне вопрос, и я дам ответ.",
        reply_markup=keyboard
    )

async def message_handler(message: types.Message):
    try:
        response = await get_openai_response(message.text)
        for chunk in split_message(response):
            await message.answer(chunk)
    except Exception as e:
        logger.exception(f"Ошибка при обработке запроса: {e}")
        await message.answer("Ошибка при обработке запроса. Попробуйте позже.")

# ======== Регистрация обработчиков ========
dp.message.register(start_handler, Command(commands=["start"]))
dp.message.register(message_handler)

# ======== Webhook сервер ========
async def handle(request):
    try:
        data = await request.json()
        logger.info(f"Webhook data: {data}")
        update = types.Update(**data)
        await dp.feed_update(update)  # правильный метод в Aiogram 3.x
        return web.Response(text="ok")
    except Exception as e:
        logger.exception(f"Ошибка обработки запроса: {e}")
        return web.Response(status=500, text="error")

async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("Webhook удалён при shutdown")

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
