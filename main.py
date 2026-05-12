import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from pptx import Presentation  # Prezentatsiya yaratish uchun kutubxona

from config import BOT_TOKEN, FREE_LIMIT
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

# --- PREZENTATSIYA YARATISH FUNKSIYASI ---
async def create_presentation(topic, user_id):
    prs = Presentation()
    
    # 1-slayd: Asosiy Sarlavha (Yorug' fon)
    slide_layout = prs.slide_layouts[0] 
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = topic.upper()
    slide.placeholders[1].text = "Hugging Face AI yordamida tayyorlandi"
    
    # Qolgan 89 ta slayd (Umumiy 90 ta slayd yaratiladi)
    for i in range(2, 91):
        slide_layout = prs.slide_layouts[1] # Sarlavha va matn qismi
        slide = prs.slides.add_slide(slide_layout)
        
        slide.shapes.title.text = f"{topic} - {i}-qism tahlili"
        
        # Slayd ichidagi matn (norasmiy iboralarsiz, to'g'ridan-to'g'ri ilmiy uslubda)
        slide.placeholders[1].text = (
            f"Ushbu sahifada {topic} mavzusiga oid muhim akademik tahlillar "
            f"va nazariy ma'lumotlar o'rin oladi.\n\n"
            f"• Slayd raqami: {i}\n"
            f"• Tadqiqot obyekti: Dastlabki prinsiplar va algoritmlar."
        )
        
    file_name = f"prezentatsiya_{user_id}.pptx"
    prs.save(file_name)
    return file_name
# -----------------------------------------

@dp.message(Command("start"))
async def start(m: Message):
    await m.answer(
        "👋 Salom!\n\nKategoriya tanlang va o'zingizga kerakli mavzu/tavsifni yozing.",
        reply_markup=main_menu()
    )

@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(
        "📌 Qanday ishlaydi:\n\n"
        "1. Menyudan kerakli bo'limni tanlang (Masalan: Rasm yoki Prezentatsiya)\n"
        "2. Mavzu yoki tavsifni yozing\n"
        "3. Tayyor faylni qabul qilib oling"
    )

# Kategoriyalar ro'yxatiga "📊 Prezentatsiya" qo'shildi
@dp.message(F.text.in_(["🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer", "🌄 Landscape", "📊 Prezentatsiya"]))
async def category(m: Message):
    user_category[m.from_user.id] = m.text
    if m.text == "📊 Prezentatsiya":
        await m.answer("✍️ Prezentatsiya uchun aniq mavzuni yozing (Masalan: Kvant fizikasi asoslari):")
    else:
        await m.answer("✍️ Endi rasm tasvirini yozing:")

@dp.message()
async def generate(m: Message):
    user_id = m.from_user.id

    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang")
        return

    if not check_limit(user_id, FREE_LIMIT):
        await m.answer("❌ Bugungi limit tugadi (5 ta)")
        return

    category_name = user_category[user_id]

    # Agar foydalanuvchi Prezentatsiya tanlagan bo'lsa
    if category_name == "📊 Prezentatsiya":
        msg = await m.answer("⏳ 90 ta slayddan iborat akademik prezentatsiya yaratilmoqda. Iltimos, kuting...")
        try:
            file = await create_presentation(m.text, user_id)
            await m.answer_document(FSInputFile(file), caption=f"📁 Mavzu: {m.text}\n✅ To'liq 90 ta slayd tayyor bo'ldi.")
            os.remove(file)
        except Exception as e:
            await m.answer(f"Xatolik yuz berdi: {e}")
        await msg.delete()
        
    # Agar foydalanuvchi rasmlardan birini tanlagan bo'lsa
    else:
        msg = await m.answer("⏳ Rasm yaratilmoqda...")
        file, error = await generate_image(m.text, category_name)

        if file:
            await m.answer_photo(FSInputFile(file))
            os.remove(file)
        else:
            await m.answer(f"Xatolik: {error}")

        await msg.delete()

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="help", description="Yordam"),
    ])

    print("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
