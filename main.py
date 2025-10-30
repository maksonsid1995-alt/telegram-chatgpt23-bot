import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Не заданы BOT_TOKEN или OPENROUTER_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# OpenRouter client (без прокси)
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Получение ответа от модели
async def get_openrouter_response(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — умный и дружелюбный Telegram-бот."},
                {"role": "user", "content": prompt}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка OpenRouter: {e}")
        return "Произошла ошибка при обращении к модели 😢"

# Обработчик сообщений
@dp.message()
async def handle_message(message: types.Message):
    logger.info(f"Получено сообщение: {message.text}")
    reply = await get_openrouter_response(message.text)
    await message.answer(reply)

# Webhook handler
async def handle(request):
    try:
        data = await request.json()
        logger.info(f"Webhook data: {data}")
        update = types.Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(text="ok")
    except Exception as e:
        logger.exception(f"Ошибка обработки запроса: {e}")
        return web.Response(status=500, text="error")

# Настройка webhook
async def on_startup(app):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook установлен: {webhook_url}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

# Запуск aiohttp
app = web.Application()
app.router.add_post(f"/webhook/{BOT_TOKEN}", handle)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)