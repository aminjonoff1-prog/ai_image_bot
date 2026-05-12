import asyncio
import os
import threading
import aiohttp
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from pptx import Presentation

from config import BOT_TOKEN, FREE_LIMIT, HF_API_KEY # config dan HF_API_KEY ni oladi
from db import check_limit
from keyboards import main_menu
from image_gen import generate_image

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# === RENDER PORT MUAMMOSI UCHUN SOXTA SERVER ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot serverda muammosiz ishlamoqda!")

def run_dummy_server():
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
# ===============================================

bot = Bot(
    token=BOT_TOKEN.strip(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

user_category = {}

# --- HUGGING FACE AI MATN OLISH FUNKSIYASI ---
async def get_ai_content(topic, slide_num):
    url = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # AI uchun akademik buyruq
    prompt = (f"Mavzu: {topic}. Slayd raqami: {slide_num}. "
              f"Ushbu slayd uchun ilmiy, akademik matn yozing. "
              f"Faqat o'zbek tilida va faqat ilmiy faktlarni keltiring. "
              f"Norasmiy so'zlardan qoching.")
    
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 200}}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # AI javobini tozalash
                    text = data[0]['generated_text'].replace(prompt, "").strip()
                    return text if text else f"{topic} mavzusining nazariy tahlili."
                else:
                    return f"{topic} mavzusining {slide_num}-qismi haqida ilmiy ma'lumotlar."
    except Exception:
        return f"{topic} mavzusi bo'yicha akademik tahlillar."

# --- PREZENTATSIYA YARATISH FUNKSIYASI (25 ta slayd) ---
async def create_presentation(topic, user_id):
    prs = Presentation()
    
    # 1-slayd: Titul
    slide_layout = prs.slide_layouts[0] 
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "Sun'iy intellekt (Mistral AI) yordamida tayyorlandi"
    
    # 25 tagacha slayd yaratish
    for i in range(2, 26):
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        
        # Sarlavha
        slide.shapes.title.text = f"{topic} - {i}-bo'lim"
        
        # AI'dan haqiqiy matn olish
        ai_text = await get_ai_content(topic, i)
        
        # Slaydga matnni joylash
        slide.placeholders[1].text = ai_text
        
    file_name = f"prezentatsiya_{user_id}.pptx"
    prs.save(file_name)
    return file_name

# --- BOT HANDLERLARI ---
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("👋 Salom! Kategoriya tanlang.", reply_markup=main_menu())

@dp.message(F.text.in_(["🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer", "🌄 Landscape", "📊 Prezentatsiya"]))
async def category(m: Message):
    user_category[m.from_user.id] = m.text
    await m.answer(f"✍️ {m.text} uchun mavzu yoki tavsif yozing:")

@dp.message()
async def generate(m: Message):
    user_id = m.from_user.id
    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang")
        return

    if not check_limit(user_id, FREE_LIMIT):
        await m.answer("❌ Limit tugadi.")
        return

    category_name = user_category[user_id]

    if category_name == "📊 Prezentatsiya":
        msg = await m.answer("⏳ 25 ta slayddan iborat professional prezentatsiya tayyorlanyapti. Iltimos, kuting (1-2 daqiqa)...")
        try:
            file = await create_presentation(m.text, user_id)
            await m.answer_document(FSInputFile(file), caption=f"📁 Mavzu: {m.text}\n✅ 25 ta slayd tayyor!")
            os.remove(file)
        except Exception as e:
            await m.answer(f"Xatolik: {e}")
        await msg.delete()
    else:
        # Rasm yaratish qismi
        msg = await m.answer("⏳ Rasm chizilyapti...")
        file, error = await generate_image(m.text, category_name)
        if file:
            await m.answer_photo(FSInputFile(file))
            os.remove(file)
        else:
            await m.answer(f"Xatolik: {error}")
        await msg.delete()

async def main():
    await bot.set_my_commands([BotCommand(command="start", description="Boshlash")])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
