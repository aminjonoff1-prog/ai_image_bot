import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# config.py dan GEMINI_API_KEY ham chaqiriladi
try:
    from config import BOT_TOKEN, FREE_LIMIT, GEMINI_API_KEY
except ImportError:
    from config import BOT_TOKEN, FREE_LIMIT
    GEMINI_API_KEY = None

from db import check_limit
from keyboards import main_menu
from image_gen import generate_image

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import google.generativeai as genai

# --- GEMINI SOZLAMALARI ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.strip())
    # Asosiy matn yaratish uchun kuchli modelni tanlaymiz
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')

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

# --- GEMINI ORQALI MATN OLISH FUNKSIYASI ---
async def get_ai_content(topic, slide_num):
    if not GEMINI_API_KEY:
        return f"{topic} mavzusining {slide_num}-qismi haqida ma'lumotlar. (API kalit kiritilmagan)"

    prompt = (f"Siz professional tahlilchisiz. '{topic}' mavzusida 25 ta slayddan iborat "
              f"loyihaning {slide_num}-qismi uchun matn yozishingiz kerak. "
              f"Matn xalqaro konsalting standartlari uslubida, qisqa, tizimli, aniq faktlarga "
              f"asoslangan va universitet darajasiga mos akademik o'zbek tilida bo'lsin. "
              f"Hech qanday kirish so'zlarisiz, to'g'ridan-to'g'ri slayd matnini bering. "
              f"Agar tahliliy grafiklar bo'yicha ma'lumot yozsangiz, Toshkent ko'k, Buxoro yashil, "
              f"Samarqand sabzirang va Namangan binafsha rangda ifodalanishini alohida ta'kidlang.")
    
    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        text = response.text.strip()
        return text if text else f"{topic} bo'yicha tahliliy ma'lumotlar."
    except Exception as e:
        print(f"Gemini xatosi: {e}")
        return f"{topic} mavzusi bo'yicha akademik matn (Vaqtinchalik xato)."

# --- PREZENTATSIYA YARATISH FUNKSIYASI (Xalqaro standartlarda) ---
async def create_presentation(topic, user_id):
    prs = Presentation()
    
    # 1-slayd: Titul (Professional Title Slide)
    title_slide_layout = prs.slide_layouts[0] 
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    # Titul sarlavhasi dizayni
    title.text = topic.upper()
    if title.text_frame.paragraphs:
        title.text_frame.paragraphs[0].font.bold = True
        title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 51, 102) # To'q ko'k rang
    
    subtitle.text = "Tahliliy Hisobot\nGemini AI yordamida avtomatik tayyorlandi"
    
    # 25 tagacha slayd yaratish (1 titul + 24 matnli slayd)
    for i in range(2, 26):
        slide_layout = prs.slide_layouts[1] # Sarlavha va matn qolipi
        slide = prs.slides.add_slide(slide_layout)
        
        # Sarlavha dizayni (chapga tekislangan, to'q ko'k rang)
        title_shape = slide.shapes.title
        title_shape.text = f"{i}-bo'lim: {topic[:30]}..."
        if title_shape.text_frame.paragraphs:
            p = title_shape.text_frame.paragraphs[0]
            p.font.size = Pt(28)
            p.font.color.rgb = RGBColor(0, 51, 102)
            p.alignment = PP_ALIGN.LEFT
        
        # Matnni Gemini'dan olish
        ai_text = await get_ai_content(topic, i)
        
        # Asosiy matn dizayni
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.text = ai_text
        
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(15)
            paragraph.font.name = 'Arial'
            
        # Footer qo'shish (Slaydning pastki qismi)
        left = Inches(0.5)
        top = Inches(7.0)
        width = Inches(9.0)
        height = Inches(0.5)
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf_footer = txBox.text_frame
        p_footer = tf_footer.add_paragraph()
        p_footer.text = f"Maxfiy | Loyiha: {topic[:15]}... | Slayd {i}"
        p_footer.font.size = Pt(10)
        p_footer.font.color.rgb = RGBColor(128, 128, 128) # Kulrang
        
    file_name = f"prezentatsiya_{user_id}.pptx"
    prs.save(file_name)
    return file_name

# --- BOT HANDLERLARI ---
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("👋 Salom! Kategoriya tanlang.", reply_markup=main_menu())

@dp.message(F.text.in_([
    "🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer", "🌄 Landscape", "📊 Prezentatsiya",
    "🖥 UI/UX Web Dizayn", "🏢 3D Arxitektura", "💎 Brending", "🎮 Konsept Art", "🏢 Reklama Banneri"
]))
async def category(m: Message):
    user_category[m.from_user.id] = m.text
    # Reklama banneri uchun maxsus tushuntirish xabari
    if m.text == "🏢 Reklama Banneri":
        await m.answer(f"✍️ Bannerda qanday tasvirlar bo'lishini xohlaysiz?\n\n"
                       f"❗ Eslatma: AI matnlarni xato yozadi. Shuning uchun faqat fon, muhit va tasvirlarni yozing (masalan: 'kitob ushlagan bola, o'quv markazi foni'). Matn uchun bo'sh joy tashlab beriladi.")
    else:
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
