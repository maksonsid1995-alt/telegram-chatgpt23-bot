import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import openai

# ==== Логирование ====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== Настройки окружения ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")
if not OPENAI_API_KEY:
    raise ValueError("❌ Переменная OPENAI_API_KEY не задана!")

# ==== Конфигурация Webhook ====
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"https://telegram-chatgpt23-bot.onrender.com{WEBHOOK_PATH}"

# ==== Инициализация бота и OpenAI ====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
openai.api_key = OPENAI_API_KEY

# ==== Вспомогательные функции ====
def split_message(text, limit=4000):
    """Делит длинный текст для Telegram"""
    return [text[i:i + limit] for i in range(0, len(text), limit)]

async def get_openai_response(prompt: str):
    """Отправляет запрос в OpenAI"""
    try:
        resp = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message["content"]
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "⚠️ Ошибка при обращении к OpenAI API. Проверь ключ."

# ==== Обработчики ====
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💬 Задать вопрос")]],
        resize_keyboard=True
    )
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        f"Напиши мне вопрос — я постараюсь ответить как ChatGPT.",
        reply_markup=keyboard
    )

@dp.message()
async def message_handler(message: types.Message):
    user_text = message.text.strip()
    logger.info(f"Сообщение от {message.from_user.id}: {user_text}")
    response = await get_openai_response(user_text)
    for chunk in split_message(response):
        await message.answer(chunk)

# ==== Webhook обработчик ====
async def handle(request):
    data = await request.json()
    logger.info(f"📩 Пришёл апдейт: {data}")
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response()

# ==== Запуск / остановка приложения ====
async def on_startup(app):
    logger.info("🚀 Запуск приложения...")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Вебхук установлен: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    logger.info("🛑 Вебхук удалён при завершении")

# ==== Приложение AIOHTTP ====
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_shutdown)

if __name__ == "__main__":
    logger.info(f"🌐 Запуск веб-сервера на порту {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
