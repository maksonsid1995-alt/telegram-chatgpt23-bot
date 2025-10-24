import os
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Не заданы BOT_TOKEN или OPENROUTER_API_KEY")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Вспомогательные функции ---

async def get_openrouter_response(prompt: str) -> str:
    """
    Отправляет запрос в OpenRouter API и возвращает текст ответа.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-chatgpt23-bot.onrender.com",
        "X-Title": "Telegram Bot via OpenRouter"
    }

    data = {
        "model": "openai/gpt-4o-mini",  # можно заменить на другую модель, например anthropic/claude-3-sonnet
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.7
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://openrouter.ai/api/v1/chat/completions",
                                headers=headers, json=data) as response:
            if response.status != 200:
                text = await response.text()
                logger.error(f"Ошибка OpenRouter API: {text}")
                return "⚠️ Ошибка при запросе к OpenRouter API."

            result = await response.json()
            return result["choices"][0]["message"]["content"]

def split_message(text: str, limit: int = 4000):
    return [text[i:i + limit] for i in range(0, len(text), limit)]

# --- Обработчики сообщений ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💬 Задать вопрос")]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.full_name}! 🤖\n"
        "Я бот на OpenRouter (GPT-4o-mini). Напиши свой вопрос 👇",
        reply_markup=keyboard
    )

@dp.message()
async def message_handler(message: types.Message):
    user_text = message.text.strip()
    logger.info(f"Получено сообщение от {message.from_user.id}: {user_text}")
    try:
        response = await get_openrouter_response(user_text)
        for chunk in split_message(response):
            await message.answer(chunk)
    except Exception as e:
        logger.exception(f"Ошибка при обработке запроса: {e}")
        await message.answer("⚠️ Ошибка при обработке запроса.")

# --- Вебхук обработчик ---

async def handle(request):
    try:
        data = await request.json()
        logger.info(f"Webhook data: {data}")
        update = types.Update(**data)
        await dp.feed_update(bot, update)  # корректный вызов для aiogram 3.x
        return web.Response(text="ok")
    except Exception as e:
        logger.exception(f"Ошибка обработки webhook: {e}")
        return web.Response(status=500, text="error")

async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("🧹 Webhook удалён при остановке")

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.router.add_get("/", lambda request: web.Response(text="🤖 Bot is running via OpenRouter"))

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
