import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import openai
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
openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- ФУНКЦИИ ----------
def split_message(text, limit=4000):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_openai_response(prompt: str):
    """Асинхронный запрос к OpenAI."""
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    return response.choices[0].message["content"]

# ---------- ХЕНДЛЕРЫ ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет 👋 Я ChatGPT-бот. Напиши что-нибудь — и я отвечу!")

@dp.message()
async def reply(message: types.Message):
    try:
        answer = await get_openai_response(message.text)
        for chunk in split_message(answer):
            await message.answer(chunk)
    except Exception as e:
        logger.exception(e)
        await message.answer("⚠️ Ошибка при обработке запроса. Попробуй позже.")

# ---------- WEBHOOK ----------
async def handle_webhook(request: web.Request):
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

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Сервер слушает порт {PORT}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())