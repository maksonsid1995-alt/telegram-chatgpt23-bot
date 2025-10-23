import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

# ---------- ЛОГИРОВАНИЕ ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def split_message(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_openai_response(prompt: str):
    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.full_name or "друг"
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        "Я бот с ChatGPT. Напиши мне сообщение — и я помогу разобраться 🤖"
    )

@dp.message()
async def handle_message(message: types.Message):
    try:
        reply = await get_openai_response(message.text)
        for chunk in split_message(reply):
            await message.answer(chunk)
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        await message.answer("⚠️ Что-то пошло не так. Попробуй позже.")

# ---------- WEBHOOK ----------
async def handle_webhook(request: web.Request):
    """Основная точка входа для Render."""
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    logger.info("Webhook удалён при остановке")

async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # ВАЖНО: Render ожидает явного запуска web-сервера на порту
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    logger.info(f"Сервер запущен и слушает порт {PORT}")
    await site.start()

    while True:
        await asyncio.sleep(3600)  # чтобы приложение не завершалось

if __name__ == "__main__":
    asyncio.run(main())