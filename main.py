import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import AsyncOpenAI

# ====== ЛОГИ ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== НАСТРОЙКИ ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не заданы BOT_TOKEN или OPENAI_API_KEY в Environment Variables")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ====== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======
def split_message(text, limit=4000):
    return [text[i:i + limit] for i in range(0, len(text), limit)]

async def get_openai_response(prompt: str):
    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.exception(f"Ошибка при обращении к OpenAI API: {e}")
        return "⚠️ Ошибка при обращении к модели. Попробуйте позже."

# ====== ОБРАБОТЧИКИ ======
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💬 Задать вопрос")]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\nНапиши мне вопрос, и я постараюсь ответить.",
        reply_markup=keyboard
    )

@dp.message()
async def message_handler(message: types.Message):
    text = message.text.strip()
    if not text:
        await message.answer("Пожалуйста, введи текст запроса.")
        return

    await message.answer("⏳ Думаю над ответом...")
    response = await get_openai_response(text)

    for chunk in split_message(response):
        await message.answer(chunk)

# ====== ОБРАБОТКА WEBHOOK ======
async def handle(request):
    try:
        data = await request.json()
        logger.info(f"Получен webhook: {data}")
        update = types.Update(**data)
        await dp.process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logger.exception(f"Ошибка обработки запроса: {e}")
        return web.Response(status=500, text="error")

# ====== СТАРТ / ОСТАНОВКА ======
async def on_startup(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("Webhook удалён при завершении работы")

# ====== ЗАПУСК ======
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
