import os
import asyncio
import openai
from aiogram import Bot, Dispatcher, types
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://<your-render-service>.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

@dp.message()
async def chatgpt_reply(message: types.Message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message.text}]
    )
    await message.answer(response.choices[0].message["content"])

async def handle(request):
    update = types.Update(**await request.json())
    await dp.feed_update(update)
    return web.Response()

async def main():
    # Устанавливаем webhook
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
    await site.start()

    print("Bot started")
    while True:
        await asyncio.sleep(3600)  # держим сервер живым

if __name__ == "__main__":
    asyncio.run(main())