import os
import openai
from aiogram import Bot, Dispatcher, executor, types

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

@dp.message_handler()
async def chatgpt_reply(message: types.Message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message.text}]
    )
    await message.answer(response.choices[0].message["content"])

if __name__ == "__main__":
    executor.start_polling(dp)
