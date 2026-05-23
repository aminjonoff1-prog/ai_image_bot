import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Config import
try:
    from config import BOT_TOKEN, FREE_LIMIT, GEMINI_API_KEY, ADMIN_ID
except ImportError:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

from db import (
    check_limit, 
    init_db, 
    add_user, 
    get_stats, 
    get_all_users, 
    add_premium_limit
)

from keyboards import main_menu
from image_gen import generate_image
from video_gen import generate_video
from audio_gen import generate_audio

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import google.generativeai as genai
import logging
import time
import threading

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- GEMINI SOZLAMALARI ---
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini muvaffaqiyatli yuklandi")
    except Exception as e:
        logger.error(f"Gemini init xatosi: {e}")

bot = Bot(
    token=BOT_TOKEN.strip(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
user_category = {}

# --- GEMINI MATN OLISH FUNKSIYASI ---
async def get_ai_content(topic, slide_num):
    if not gemini_model:
        return f"{topic} mavzusining {slide_num}-qismi haqida ma'lumotlar."

    prompt = (
        f"Siz professional tahlilchisiz. '{topic}' mavzusida prezentatsiyaning "
        f"{slide_num}-slaydi uchun matn yozing. "
        f"Matn qisqa, tizimli, aniq faktlarga asoslangan bo'lsin. "
        f"Universitet darajasiga mos akademik o'zbek tilida yozing. "
        f"Hech qanday kirish so'zlarisiz, to'g'ridan-to'g'ri slayd matnini bering."
    )
    
    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        text = response.text.strip()
        return text if text else f"{topic} bo'yicha tahliliy ma'lumotlar."
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return f"{topic} mavzusi bo'yicha akademik matn."

# --- PREZENTATSIYA YARATISH ---
async def create_presentation(topic, user_id):
    prs = Presentation()
    
    # 1-slayd: Sarlavha
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = topic.upper()
    for paragraph in title.text_frame.paragraphs:
        paragraph.font.bold = True
        paragraph.font.color.rgb = RGBColor(0, 51, 102)
    
    subtitle.text = "📊 Tahliliy Hisobot\nGemini AI yordamida tayyorlandi"
    
    # 2-25 slaydlar
    for i in range(2, 26):
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        
        title_shape = slide.shapes.title
        title_shape.text = f"{i}-bo'lim"
        for paragraph in title_shape.text_frame.paragraphs:
            paragraph.font.size = Pt(28)
            paragraph.font.color.rgb = RGBColor(0, 51, 102)
            paragraph.alignment = PP_ALIGN.LEFT
        
        ai_text = await get_ai_content(topic, i)
        
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        tf.text = ai_text
        
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(14)
            paragraph.font.name = 'Arial'
        
        # Footer
        left = Inches(0.5)
        top = Inches(7.0)
        width = Inches(9.0)
        height = Inches(0.5)
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf_footer = txBox.text_frame
        p_footer = tf_footer.paragraphs[0]
        p_footer.text = f"📌 {topic[:30]}... | Slayd {i}/25"
        p_footer.font.size = Pt(10)
        p_footer.font.color.rgb = RGBColor(128, 128, 128)
    
    file_name = f"prezentatsiya_{user_id}_{int(time.time())}.pptx"
    prs.save(file_name)
    return file_name

# --- BOT HANDLERLARI ---
@dp.message(Command("start"))
async def start(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)
    await m.answer("👋 Salom! Kategoriya tanlang.", reply_markup=main_menu())

@dp.message(Command("admin"))
async def admin_panel(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    
    try:
        users_count, total_usage = get_stats()
        text = (
            f"📊 <b>Bot Statistikasi</b>\n\n"
            f"👥 Jami foydalanuvchilar: {users_count} ta\n"
            f"🎨 Jami media/slayd yasalgan: {total_usage} marta"
        )
        await m.answer(text)
    except Exception as e:
        await m.answer(f"Xatolik: {e}")

@dp.message(Command("send"))
async def broadcast(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    
    text = m.text.replace("/send", "").strip()
    if not text:
        await m.answer("❗ Xabar matnini kiriting.\nMisol: <code>/send Assalomu alaykum!</code>")
        return
    
    users = get_all_users()
    count = 0
    msg = await m.answer("⏳ Xabar yuborilmoqda...")
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    
    await msg.edit_text(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.")

@dp.message(Command("give"))
async def give_limit_command(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = m.text.split()
        if len(parts) < 3:
            await m.answer("❗ To'g'ri foydalanish:\n<code>/give [user_id] [miqdor]</code>")
            return
        
        target_user_id = int(parts[1])
        amount = int(parts[2])
        
        success = add_premium_limit(target_user_id, amount)
        
        if success:
            await m.answer(f"✅ Foydalanuvchi <code>{target_user_id}</code> hisobiga +{amount} ta limit qo'shildi!")
            try:
                await bot.send_message(
                    target_user_id, 
                    f"🎉 Premium faollashtirildi!\nHisobingizga +{amount} ta yangi limit qo'shildi!"
                )
            except Exception:
                pass
        else:
            await m.answer("❌ Bunday ID ga ega foydalanuvchi topilmadi.")
            
    except (IndexError, ValueError):
        await m.answer("❗ Xato format. To'g'ri foydalanish:\n<code>/give 512345678 30</code>")

CATEGORIES = [
    "🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer", 
    "🌄 Landscape", "📊 Prezentatsiya", "🖥 UI/UX Web Dizayn",
    "🏢 3D Arxitektura", "💎 Brending", "🎮 Konsept Art",
    "🏢 Reklama Banneri", "🎬 Video Generatsiya", "🎵 Audio/Musiqa"
]

@dp.message(F.text.in_(CATEGORIES))
async def category(m: Message):
    user_category[m.from_user.id] = m.text
    
    messages = {
        "🏢 Reklama Banneri": "✍️ Bannerda qanday tasvirlar bo'lishini xohlaysiz?\n\n❗ AI matnlarni xato yozadi. Faqat fon va tasvirlarni yozing.",
        "🎬 Video Generatsiya": "🎬 <b>Google Veo Video Studio</b>\n\nQanday video yaratishni xohlaysiz? Batafsil yozing.",
        "🎵 Audio/Musiqa": "🎵 <b>Google Lyria 3 Ovoz Studiyasi</b>\n\nQanday musiqa yaratish kerak? (Masalan: 'reklama uchun sokin royal ohangi')"
    }
    
    await m.answer(messages.get(m.text, f"✍️ {m.text} uchun mavzu yoki tavsif yozing:"))

@dp.message()
async def generate(m: Message):
    user_id = m.from_user.id
    
    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang /start bosing")
        return

    # Limit tekshirish
    if user_id != ADMIN_ID and not check_limit(user_id, FREE_LIMIT):
        tariff_text = (
            "❌ <b>Bepul limitlaringiz tugadi!</b>\n\n"
            "💰 Tariflar:\n"
            "🎨 <b>Start (30 ta)</b> - 19,000 so'm\n"
            "🚀 <b>Professional (100 ta)</b> - 49,000 so'm\n"
            "👑 <b>Biznes (1 oy cheksiz)</b> - 99,000 so'm\n\n"
            "💳 Karta: <code>5614 6805 1876 1602</code>\n"
            "📱 Admin: @muhammad_amin07\n"
            f"🆔 Sizning ID: <code>{user_id}</code>"
        )
        await m.answer(tariff_text)
        return

    category_name = user_category[user_id]
    del user_category[user_id]

    # Prezentatsiya
    if category_name == "📊 Prezentatsiya":
        msg = await m.answer("⏳ 25 ta slayd tayyorlanyapti (1-2 daqiqa)...")
        try:
            file = await create_presentation(m.text, user_id)
            await m.answer_document(
                FSInputFile(file), 
                caption=f"📁 Mavzu: {m.text}\n✅ 25 ta slayd tayyor!"
            )
            os.remove(file)
        except Exception as e:
            await m.answer(f"❌ Xatolik: {e}")
        finally:
            try:
                await msg.delete()
            except Exception:
                pass

    # Video
    elif category_name == "🎬 Video Generatsiya":
        msg = await m.answer("⏳ Video hisoblanmoqda va ovoz qo'shmoqda...")
        try:
            file, error = await generate_video(m.text)
            if file:
                await m.answer_video(
                    FSInputFile(file), 
                    caption=f"🎬 G'oya: {m.text}\n🔥 Google Veo Studio"
                )
                os.remove(file)
            else:
                await m.answer(f"❌ Xatolik: {error}")
        except Exception as e:
            await m.answer(f"❌ Xatolik: {e}")
        finally:
            try:
                await msg.delete()
            except Exception:
                pass

    # Audio
    elif category_name == "🎵 Audio/Musiqa":
        msg = await m.answer("⏳ Musiqa bastalanmoqda...")
        try:
            file, error = await generate_audio(m.text)
            if file:
                await m.answer_audio(
                    FSInputFile(file), 
                    caption=f"🎵 Uslub: {m.text}\n⚡ Google Lyria 3"
                )
                os.remove(file)
            else:
                await m.answer(f"❌ Xatolik: {error}")
        except Exception as e:
            await m.answer(f"❌ Xatolik: {e}")
        finally:
            try:
                await msg.delete()
            except Exception:
                pass

    # Rasm generatsiya
    else:
        msg = await m.answer("⏳ Rasm chizilyapti...")
        try:
            file, error = await generate_image(m.text, category_name)
            if file:
                await m.answer_photo(FSInputFile(file))
                os.remove(file)
            else:
                await m.answer(f"❌ Xatolik: {error}")
        except Exception as e:
            await m.answer(f"❌ Xatolik: {e}")
        finally:
            try:
                await msg.delete()
            except Exception:
                pass

# --- WEB SERVER (UptimeRobot uchun) ---
async def run_web_server():
    """Oddiy web server - UptimeRobot uchun"""
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text="OK", status=200)
    
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    port = int(os.environ.get("PORT", 8080))
    
    # Web serverni ishga tushirish
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ Web server ishga tushdi: http://0.0.0.0:{port}")
    
    # Cheksiz ushlab turish
    await asyncio.Future()

# --- ASOSIY FUNKSIYA ---
async def main():
    init_db()
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN aniqlanmagan!")
        return
    
    # Bot komandalarini o'rnatish
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
    ])
    
    logger.info("🚀 Bot ishga tushmoqda...")
    
    # Web serverni alohida taskda ishga tushirish
    web_task = asyncio.create_task(run_web_server())
    
    # Polling ni ishga tushirish
    polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))
    
    # Ikkalasini ham kuzatish
    await asyncio.gather(web_task, polling_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("❌ Bot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Kutilmagan xatolik: {e}")
