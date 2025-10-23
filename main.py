import os
import asyncio
import openai
from aiogram import Bot, Dispatcher, types
from aiohttp import web

# ======== ПЕРЕМЕННЫЕ ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

# URL твоего Render-сервиса
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ======== ИНИЦИАЛИЗАЦИЯ ========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

# ======== ОБРАБОТКА СООБЩЕНИЙ ========
@dp.message()
async def chatgpt_reply(message: types.Message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message.text}]
    )
    await message.answer(response.choices[0].message["content"])

# ======== HANDLER ДЛЯ WEBHOOK ========
async def handle(request):
    update = types.Update(**await request.json())
    await dp.feed_update(update)
    return web.Response()

# ======== СТАРТ СЕРВЕРА ========
async def main():
    # Сбрасываем старые webhook
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

    # Запускаем веб-сервер
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"Bot started at {WEBHOOK_URL}")
    while True:
        await asyncio.sleep(3600)  # держим сервер живым

if __name__ == "__main__":
    asyncio.run(main())