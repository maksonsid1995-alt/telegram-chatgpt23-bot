import os
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.filters import BaseFilter
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обработка сообщений
@dp.message()
async def chatgpt_reply(message: types.Message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message.text}]
    )
    await message.answer(response.choices[0].message["content"])

# Запуск webhook
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown():
    await bot.delete_webhook()

# Создание веб-сервера aiohttp
async def run_app():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, dp)
    return app

if __name__ == "__main__":
    import asyncio
    app = asyncio.run(run_app())
    web.run_app(app, host="0.0.0.0", port=PORT)