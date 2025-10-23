import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
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
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY в Environment Variables")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ---------- ИНИЦИАЛИЗАЦИЯ ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def split_message(text: str, limit: int = 4000):
    """Разделяет длинный текст на части, чтобы Telegram не ругался."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_openai_response(prompt: str):
    """Асинхронный запрос к OpenAI с повторными попытками."""
    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ---------- ОБРАБОТЧИКИ ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение."""
    user_name = message.from_user.full_name or "друг"
    text = (
        f"Привет, {user_name}! 👋\n\n"
        "Я бот с ChatGPT. Задай мне любой вопрос — "
        "и я постараюсь ответить максимально полезно и вежливо. 🤖"
    )
    await message.answer(text)

@dp.chat_member()
async def greet_new_user(event: ChatMemberUpdated):
    """Приветствие новых участников в группе."""
    if event.new_chat_member.status == "member":
        user = event.new_chat_member.user
        await bot.send_message(
            event.chat.id,
            f"👋 Добро пожаловать, {user.first_name}! "
            f"Я тут, чтобы поддерживать разговор и помогать 😉"
        )

@dp.message()
async def handle_message(message: Message):
    """Главная логика диалога с ChatGPT."""
    try:
        user_text = message.text.strip()
        if not user_text:
            return await message.answer("Напиши текст, чтобы я мог ответить 🙂")

        reply = await get_openai_response(user_text)

        for part in split_message(reply):
            await message.answer(part)

    except Exception as e:
        logger.exception(f"Ошибка при обработке сообщения: {e}")
        await message.answer("⚠️ Что-то пошло не так. Попробуй снова через минуту.")

# ---------- WEBHOOK-СЕРВЕР ----------
async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    logger.info("Webhook удалён при остановке")

async def run_webhook():
    """Запуск aiohttp-сервера под Render."""
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, dp.resolve_event(Update=types.Update))
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    logger.info(f"Сервер запущен на порту {PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_webhook())