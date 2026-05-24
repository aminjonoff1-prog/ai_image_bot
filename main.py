import os
import asyncio
import logging
import time

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

import google.generativeai as genai

# --- CONFIG IMPORT ---
try:
    from config import BOT_TOKEN, FREE_LIMIT, GEMINI_API_KEY, ADMIN_ID
except ImportError:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# --- DB FUNKSIYALARI ---
from db import (
    check_limit,
    init_db,
    add_user,
    get_stats,
    get_all_users,
    add_premium_limit,
    get_limit_info,
    reset_user_usage,
    get_user_info,
)

# --- MODULLAR ---
from keyboards import main_menu
from image_gen import generate_image
from video_gen import generate_video
from audio_gen import generate_audio
from coursework_gen import generate_coursework  # Yangi kurs ishi moduli

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- GEMINI SOZLAMALARI ---
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest")
        logger.info("✅ Gemini muvaffaqiyatli yuklandi")
    except Exception as e:
        logger.error(f"❌ Gemini init xatosi: {e}")

# --- BOT VA DISPATCHER ---
bot = Bot(
    token=BOT_TOKEN.strip(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# --- FOYDALANUVCHI HOLATLARI ---
user_category = {}


# ============================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def safe_delete(message):
    try:
        await message.delete()
    except Exception:
        pass


async def safe_remove_file(filename: str):
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        logger.error(f"Faylni o'chirishda xato: {e}")


# ============================================================
# GEMINI PROFESSIONAL PRESENTATION PROMPT
# ============================================================

async def get_ai_slide_content(topic: str, slide_num: int) -> dict:
    """Slayd uchun professional tahliliy matn yaratadi"""
    default_data = {
        "title": f"{slide_num}-Bo'lim: {topic[:25]}",
        "subtitle": "Tahlil va strategik yondashuv",
        "bullets": [
            "Mavzu bo'yicha tahliliy o'rganish ishlari olib borilmoqda.",
            "Infratuzilma va asosiy o'sish ko'rsatkichlari tahlil qilindi.",
            "Strategik reja loyihasi ishlab chiqildi."
        ],
        "callout": "Raqamli tahlil muvaffaqiyat garovidir."
    }

    if not gemini_model:
        return default_data

    prompt = (
        f"Siz dunyodagi eng nufuzli McKinsey va BCG konsalting kompaniyalarining bosh strategisiz.\n"
        f"Mavzu: '{topic}' bo'yicha tayyorlanayotgan professional prezentatsiyaning {slide_num}-slaydi uchun o'zbek tilida matn yozing.\n\n"
        f"Format qat'iy ravishda quyidagicha bo'lsin (Hech qanday boshqa so'z yozmang, faqat shu formatda):\n"
        f"TITLE: [Slaydning qisqa va kuchli sarlavhasi]\n"
        f"SUBTITLE: [Slaydning kichik strategik sarlavhasi]\n"
        f"BULLETS:\n"
        f"- [Asosiy tahliliy fakt yoki drayver, juda professional tilda]\n"
        f"- [Ikkinchi tahliliy fakt, raqamlar yoki statistika bilan boyitilgan]\n"
        f"- [Uchinchi muhim yo'nalish yoki strategik chora-tadbir]\n"
        f"- [To'rtinchi muhim xulosa yoki xalqaro tajriba]\n"
        f"CALLOUT: [Ushbu slayddan olinadigan eng muhim konsalting xulosasi yoki oltin qoida - 1 qator]"
    )

    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        text = response.text.strip()
        
        # AI javobini tahlil qilish (parsing)
        lines = text.split("\n")
        data = {
            "title": f"Mavzu: {topic[:30]}",
            "subtitle": "",
            "bullets": [],
            "callout": ""
        }
        
        current_section = None
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            if line_str.upper().startswith("TITLE:"):
                data["title"] = line_str[6:].strip().replace("[", "").replace("]", "")
            elif line_str.upper().startswith("SUBTITLE:"):
                data["subtitle"] = line_str[9:].strip().replace("[", "").replace("]", "")
            elif line_str.upper().startswith("BULLETS:"):
                current_section = "bullets"
            elif line_str.upper().startswith("CALLOUT:"):
                data["callout"] = line_str[8:].strip().replace("[", "").replace("]", "")
                current_section = None
            elif current_section == "bullets" and (line_str.startswith("-") or line_str.startswith("•") or line_str.startswith("*")):
                bullet_text = line_str[1:].strip().replace("[", "").replace("]", "")
                if bullet_text:
                    data["bullets"].append(bullet_text)

        if not data["bullets"]:
            data["bullets"] = default_data["bullets"]
        if not data["callout"]:
            data["callout"] = default_data["callout"]

        return data
    except Exception as e:
        logger.error(f"Gemini slayd xatosi: {e}")
        return default_data


# ============================================================
# MCKINSEY STYLE SLIDE BUILDER (PROFESSIONAL DESIGN)
# ============================================================

async def create_presentation(topic: str, user_id: int) -> str:
    """Dizaynerlik darajasidagi, 25 slayddan iborat PowerPoint yaratadi"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Ranglar palitrasi (Navy Corporate Theme)
    c_dark_navy = RGBColor(11, 29, 58)    # #0B1D3A
    c_light_gray = RGBColor(245, 247, 250)  # #F5F7FA
    c_pure_white = RGBColor(255, 255, 255)
    c_text_dark = RGBColor(40, 50, 65)
    c_accent_blue = RGBColor(0, 102, 204)  # #0066CC
    c_accent_gold = RGBColor(212, 175, 55)  # #D4AF37

    # 1-slayd: Premium Sarlavha Slaydi (To'q ko'k fonda)
    blank_slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Orqa fonni to'q ko'k qilish
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(10), Inches(7.5))
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = c_dark_navy
    bg_shape.line.fill.background()

    # Sarlavha matni
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.2), Inches(8), Inches(2))
    tf = title_box.text_frame
    tf.word_wrap = True
    p1 = tf.paragraphs[0]
    p1.text = topic.upper()
    p1.font.name = "Georgia"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = c_pure_white
    p1.alignment = PP_ALIGN.LEFT

    # Kichik sarlavha (Gold accent)
    p2 = tf.add_paragraph()
    p2.text = "📈 STRATEGIK VA TAHLILIY HISOBOT\nKompaniya faoliyatini rivojlantirish dasturi"
    p2.font.name = "Calibri"
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = c_accent_gold
    p2.space_before = Pt(20)

    # 2-25 Slaydlar (Mckinsey standard: 2-kolonkali mukammal tuzilma)
    for num in range(2, 26):
        slide = prs.slides.add_slide(blank_slide_layout)
        
        # Orqa fon (Och kulrang)
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(10), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = c_light_gray
        bg.line.fill.background()

        # Ma'lumotlarni AI dan olish
        s_data = await get_ai_slide_content(topic, num)

        # 1. Tepada Header chizig'i va Sarlavha
        header_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(8.8), Inches(1))
        htf = header_box.text_frame
        htf.word_wrap = True
        
        hp1 = htf.paragraphs[0]
        hp1.text = s_data["title"]
        hp1.font.name = "Georgia"
        hp1.font.size = Pt(24)
        hp1.font.bold = True
        hp1.font.color.rgb = c_dark_navy

        if s_data["subtitle"]:
            hp2 = htf.add_paragraph()
            hp2.text = s_data["subtitle"]
            hp2.font.name = "Calibri"
            hp2.font.size = Pt(12)
            hp2.font.color.rgb = c_accent_blue
            hp2.space_before = Pt(4)

        # 2. Chap ustun: Asosiy ma'lumotlar (Bullets)
        left_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(5.4), Inches(4.5))
        ltf = left_box.text_frame
        ltf.word_wrap = True
        
        for idx, bullet in enumerate(s_data["bullets"]):
            bp = ltf.paragraphs[0] if idx == 0 else ltf.add_paragraph()
            bp.text = f"•  {bullet}"
            bp.font.name = "Calibri"
            bp.font.size = Pt(14)
            bp.font.color.rgb = c_text_dark
            bp.space_after = Pt(14)
            bp.line_spacing = 1.15

        # 3. O'ng ustun: Tahliliy blok (Highlight/Callout Box)
        # Fon shakli (Oq to'rtburchak ko'k chiziq va yorqin foni bilan)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.3), Inches(1.6), Inches(3.1), Inches(4.5))
        card.fill.solid()
        card.fill.fore_color.rgb = c_pure_white
        card.line.color.rgb = c_accent_blue
        card.line.width = Pt(1.5)

        # Tahliliy blok ichidagi matn
        card_box = slide.shapes.add_textbox(Inches(6.4), Inches(1.8), Inches(2.9), Inches(4.1))
        ctf = card_box.text_frame
        ctf.word_wrap = True
        
        cp1 = ctf.paragraphs[0]
        cp1.text = "STRATEGIK TAHLIL"
        cp1.font.name = "Calibri"
        cp1.font.size = Pt(12)
        cp1.font.bold = True
        cp1.font.color.rgb = c_accent_blue
        cp1.space_after = Pt(12)

        cp2 = ctf.add_paragraph()
        cp2.text = s_data["callout"]
        cp2.font.name = "Georgia"
        cp2.font.size = Pt(14)
        cp2.font.color.rgb = c_dark_navy
        cp2.line_spacing = 1.25

        # 4. Footer qismi
        footer_box = slide.shapes.add_textbox(Inches(0.6), Inches(6.8), Inches(8.8), Inches(0.4))
        ftf = footer_box.text_frame
        fp = ftf.paragraphs[0]
        fp.text = f"Loyiha: {topic[:35]}... | Slayd {num} / 25 | Maxfiy"
        fp.font.name = "Calibri"
        fp.font.size = Pt(9)
        fp.font.color.rgb = RGBColor(150, 150, 150)

    filename = f"prezentatsiya_{user_id}_{int(time.time())}.pptx"
    prs.save(filename)
    return filename


# ============================================================
# FOYDALANUVCHI HANDLERLARI
# ============================================================

@dp.message(Command("start"))
async def start_command(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    welcome_text = (
        f"👋 Salom, <b>{m.from_user.full_name}</b>!\n\n"
        f"🤖 Men AI professional dizayner va akademik yordamchiman.\n\n"
        f"📋 <b>Mening imkoniyatlarim:</b>\n"
        f"📚 <b>Kurs Ishi</b> - mukammal ilmiy ish (DOCX)\n"
        f"📊 <b>Prezentatsiya</b> - McKinsey uslubidagi 25 ta slayd (PPTX)\n"
        f"🎨 <b>Logo va rasmlar</b> - Stabiltiy AI rasm generatori\n"
        f"🎬 <b>Video yaratish</b> - Google Veo Studio\n"
        f"🎵 <b>Musiqa yaratish</b> - Google Lyria 3\n\n"
        f"⚡ <b>Boshlash uchun pastdagi menyudan kategoriya tanlang!</b>"
    )
    await m.answer(welcome_text, reply_markup=main_menu())


@dp.message(Command("limit"))
async def limit_command(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    if is_admin(m.from_user.id):
        await m.answer("👑 <b>Siz adminsiz!</b>\n\nSizga hech qanday cheklov va limitlar taalluqli emas.")
        return

    info = get_limit_info(m.from_user.id, FREE_LIMIT)
    if not info:
        await m.answer("❌ Limit topilmadi. /start bosing.")
        return

    text = (
        f"📊 <b>Sizning limitingiz</b>\n\n"
        f"🎁 Bepul limit: <b>{FREE_LIMIT}</b> ta\n"
        f"💎 Premium limit: <b>{info['premium_limit']}</b> ta\n"
        f"📌 Umumiy limit: <b>{info['total_limit']}</b> ta\n"
        f"✅ Ishlatilgan: <b>{info['usage_count']}</b> ta\n"
        f"🔋 Qolgan: <b>{info['remaining']}</b> ta\n\n"
        f"🆔 Sizning ID: <code>{m.from_user.id}</code>"
    )
    if info['remaining'] == 0:
        text += "\n\n❗ Bepul limitlar tugagan, premium olish uchun adminga bog'laning."
    await m.answer(text)


# ============================================================
# ADMIN HANDLERLARI
# ============================================================

@dp.message(Command("admin"))
async def admin_panel(m: Message):
    if not is_admin(m.from_user.id):
        return
    try:
        users_count, total_usage = get_stats()
        text = (
            f"👑 <b>Admin Panel</b>\n\n"
            f"👥 Jami a'zolar: <b>{users_count}</b> ta\n"
            f"🎨 Jami yaratilgan media: <b>{total_usage}</b> marta\n\n"
            f"⚙️ <b>Buyruqlar:</b>\n"
            f"<code>/send [matn]</code> - hammaga xabar yuborish\n"
            f"<code>/give [id] [son]</code> - premium limit qo'shish\n"
            f"<code>/reset [id]</code> - foydalanuvchi limitini tiklash\n"
            f"<code>/userinfo [id]</code> - to'liq ma'lumot olish"
        )
        await m.answer(text)
    except Exception as e:
        await m.answer(f"Xato: {e}")


@dp.message(Command("send"))
async def broadcast_command(m: Message):
    if not is_admin(m.from_user.id):
        return

    text = m.text.replace("/send", "", 1).strip()
    if not text:
        await m.answer("❗ Yuboriladigan xabar matnini kiriting.")
        return

    users = get_all_users()
    msg = await m.answer(f"⏳ {len(users)} ta foydalanuvchiga yuborilmoqda...")
    success, failed = 0, 0

    for u_id in users:
        try:
            await bot.send_message(u_id, text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await msg.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi:</b>\n\n"
        f"✔️ Muvaffaqiyatli: <b>{success}</b>\n"
        f"❌ Muammoli: <b>{failed}</b>"
    )


@dp.message(Command("give"))
async def give_limit_command(m: Message):
    if not is_admin(m.from_user.id):
        return
    try:
        parts = m.text.split()
        if len(parts) < 3:
            await m.answer("❗ Format xato: <code>/give [id] [son]</code>")
            return
        
        target_id = int(parts[1])
        amount = int(parts[2])
        success = add_premium_limit(target_id, amount)

        if success:
            await m.answer(f"✅ Foydalanuvchi <code>{target_id}</code> hisobiga +{amount} ta premium limit qo'shildi!")
            try:
                await bot.send_message(target_id, f"🎉 Premium faollashtirildi!\nHisobingizga +{amount} yangi imkoniyatlar qo'shildi!")
            except Exception:
                pass
        else:
            await m.answer("❌ Foydalanuvchi topilmadi.")
    except Exception as e:
        await m.answer(f"Xato: {e}")


@dp.message(Command("reset"))
async def reset_command(m: Message):
    if not is_admin(m.from_user.id):
        return
    try:
        parts = m.text.split()
        if len(parts) < 2:
            await m.answer("❗ Format: <code>/reset [id]</code>")
            return
        
        target_id = int(parts[1])
        success = reset_user_usage(target_id)
        if success:
            await m.answer(f"✅ Foydalanuvchi <code>{target_id}</code> limiti muvaffaqiyatli tiklandi.")
        else:
            await m.answer("❌ Xatolik yuz berdi yoki foydalanuvchi topilmadi.")
    except Exception as e:
        await m.answer(f"Xato: {e}")


@dp.message(Command("userinfo"))
async def userinfo_command(m: Message):
    if not is_admin(m.from_user.id):
        return
    try:
        parts = m.text.split()
        if len(parts) < 2:
            await m.answer("❗ Format: <code>/userinfo [id]</code>")
            return
        
        target_id = int(parts[1])
        info = get_user_info(target_id)
        if not info:
            await m.answer("❌ Foydalanuvchi bazadan topilmadi.")
            return

        text = (
            f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
            f"🆔 ID: <code>{info['user_id']}</code>\n"
            f"📛 Ism: {info['full_name']}\n"
            f"🔗 Username: @{info['username']}\n"
            f"📅 Sana: {info['joined_date']}\n\n"
            f"📊 <b>Limit ma'lumotlari:</b>\n"
            f"🎁 Ishlatilgan limit: {info['usage_count']} ta\n"
            f"💎 Premium limitlar: {info['premium_limit']} ta"
        )
        await m.answer(text)
    except Exception as e:
        await m.answer(f"Xato: {e}")


# ============================================================
# KATEGORIYALAR TIZIMI
# ============================================================

CATEGORIES = [
    "🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer",
    "🌄 Landscape", "📊 Prezentatsiya", "📚 Kurs Ishi", "🖥 UI/UX Web Dizayn",
    "🏢 3D Arxitektura", "💎 Brending", "🎮 Konsept Art",
    "🏢 Reklama Banneri", "🎬 Video Generatsiya", "🎵 Audio/Musiqa",
]


@dp.message(F.text.in_(CATEGORIES))
async def category_handler(m: Message):
    user_category[m.from_user.id] = m.text

    captions = {
        "📚 Kurs Ishi": (
            "📚 <b>Kurs Ishi (Academic Writer)</b>\n\n"
            "Mavzuni kiritishingiz bilan tizim sizga Times New Roman standardida mundarijali, "
            "boblar, tahlil va foydalanilgan adabiyotlar ro'yxatiga ega mukammal kurs ishini yaratib beradi.\n\n"
            "✍️ Iltimos, kurs ishi mavzusini batafsil yozib yuboring:"
        ),
        "📊 Prezentatsiya": (
            "📊 <b>McKinsey & Co. Premium Presentation</b>\n\n"
            "Tizim sizga jahon andozalariga mos, tahliliy bloklar va professional vizualizatsiyaga "
            "ega 25 ta premium slayd yaratadi.\n\n"
            "✍️ Iltimos, slaydlar qanday mavzuda bo'lishini yozing:"
        ),
        "🎬 Video Generatsiya": (
            "🎬 <b>Google Veo Video Studio</b>\n\n"
            "Qanday video yaratmoqchisiz? Batafsil yozib bering:"
        ),
        "🎵 Audio/Musiqa": (
            "🎵 <b>Google Lyria 3 Ovoz Studiyasi</b>\n\n"
            "Janr va yo'nalishni kiritishingiz bilan sizga musiqa bastalab beriladi:"
        )
    }

    default_text = (
        f"✍️ <b>{m.text} uchun tavsif yuboring:</b>\n\n"
        f"AI siz kiritgan har bir jumla bo'yicha mukammal natija generatsiya qiladi."
    )
    await m.answer(captions.get(m.text, default_text))


# ============================================================
# GENERATSIYA JARAYONI
# ============================================================

@dp.message()
async def generate_handler(m: Message):
    user_id = m.from_user.id

    if user_id not in user_category:
        await m.answer("❗ Avval kategoriyalardan birini tanlang yoki botni qayta ishga tushirish uchun /start bosing.")
        return

    # Limit tekshiruvi (Adminlar cheksiz foydalana oladilar)
    if not is_admin(user_id) and not check_limit(user_id, FREE_LIMIT):
        tariff_text = (
            "❌ <b>Sizning bepul limitlaringiz tugadi!</b>\n\n"
            "Davom ettirish uchun premium paketni sotib oling:\n"
            "🎨 <b>Start (30 ta limit)</b> - 19,000 so'm\n"
            "🚀 <b>Professional (100 ta limit)</b> - 49,000 so'm\n"
            "👑 <b>Biznes (Cheksiz limit)</b> - 99,000 so'm\n\n"
            "💳 Karta: <code>5614 6805 1876 1602</code>\n"
            "👤 Aminjonov Muhammadamin\n\n"
            "⚠️ To'lovdan so'ng chek va profilingiz ID raqamini adminga yuboring:\n"
            "📱 Aloqa: @muhammad_amin07\n\n"
            f"🆔 Sizning ID: <code>{user_id}</code>"
        )
        await m.answer(tariff_text)
        return

    category_name = user_category.pop(user_id)
    user_text = m.text.strip()

    if not user_text:
        await m.answer("❗ Tushunarsiz yoki bo'sh so'rov. Iltimos, qayta yozing.")
        user_category[user_id] = category_name
        return

    # === 1. KURS ISHI ===
    if category_name == "📚 Kurs Ishi":
        msg = await m.answer("⏳ <b>Mukammal ilmiy ish yozilmoqda...</b>\nBarcha sahifalar, mundarija va adabiyotlar shakllantirilyapti. Bu bir necha daqiqa olishi mumkin.")
        file_path = None
        try:
            file_path = await generate_coursework(user_text, user_id)
            await m.answer_document(
                FSInputFile(file_path),
                caption=f"📚 <b>Kurs Ishi Tayyor!</b>\n\n📝 <b>Mavzu:</b> {user_text}\n📂 Times New Roman standardida Word (DOCX) fayl."
            )
        except Exception as e:
            logger.error(f"Kurs ishi xatosi: {e}")
            await m.answer(f"❌ Kurs ishini yaratishda xatolik yuz berdi: {e}")
        finally:
            await safe_remove_file(file_path)
            await safe_delete(msg)

    # === 2. PREZENTATSIYA ===
    elif category_name == "📊 Prezentatsiya":
        msg = await m.answer("⏳ <b>McKinsey Consulting Presentation Engine</b> ishga tushirildi. 25 ta premium slaydlar tayyorlanmoqda (1-2 daqiqa)...")
        file_path = None
        try:
            file_path = await create_presentation(user_text, user_id)
            await m.answer_document(
                FSInputFile(file_path),
                caption=f"📊 <b>Prezentatsiya Tayyor!</b>\n\n📝 <b>Mavzu:</b> {user_text}\n🏆 25 ta McKinsey andozasidagi professional tahlil slaydlari."
            )
        except Exception as e:
            logger.error(f"Prezentatsiya xatosi: {e}")
            await m.answer(f"❌ Prezentatsiya yaratishda muammo yuz berdi: {e}")
        finally:
            await safe_remove_file(file_path)
            await safe_delete(msg)

    # === 3. VIDEO ===
    elif category_name == "🎬 Video Generatsiya":
        msg = await m.answer("⏳ Video generatsiya qilinmoqda...")
        file_path = None
        try:
            file_path, error = await generate_video(user_text)
            if file_path:
                await m.answer_video(FSInputFile(file_path), caption=f"🎬 <b>Video:</b> {user_text}\n🔥 Google Veo Video Studio")
            else:
                await m.answer(f"❌ Xatolik: {error}")
        except Exception as e:
            await m.answer(f"❌ Tizim xatosi: {e}")
        finally:
            await safe_remove_file(file_path)
            await safe_delete(msg)

    # === 4. AUDIO ===
    elif category_name == "🎵 Audio/Musiqa":
        msg = await m.answer("⏳ Musiqa bastalanmoqda...")
        file_path = None
        try:
            file_path, error = await generate_audio(user_text)
            if file_path:
                await m.answer_audio(FSInputFile(file_path), caption=f"🎵 <b>Musiqa:</b> {user_text}\n⚡ Google Lyria 3")
            else:
                await m.answer(f"❌ Xatolik: {error}")
        except Exception as e:
            await m.answer(f"❌ Xatolik: {e}")
        finally:
            await safe_remove_file(file_path)
            await safe_delete(msg)

    # === 5. RASMLAR VA DIZAYNLAR ===
    else:
        msg = await m.answer("⏳ Rasm chizilmoqda...")
        file_path = None
        try:
            file_path, error = await generate_image(user_text, category_name)
            if file_path:
                await m.answer_photo(FSInputFile(file_path), caption=f"🎨 <b>Kategoriya:</b> {category_name}\n📝 {user_text}")
            else:
                await m.answer(f"❌ Tasvir yaratishda xato: {error}")
        except Exception as e:
            await m.answer(f"❌ Tizim xatoligi: {e}")
        finally:
            await safe_remove_file(file_path)
            await safe_delete(msg)


# ============================================================
# WEB SERVER (Uptime Robot & Health check)
# ============================================================

async def run_web_server():
    app = web.Application()

    async def health_check(request):
        return web.Response(text="✅ Bot is running properly!", status=200)

    async def dashboard(request):
        users_count, total_usage = get_stats()
        return web.json_response({
            "status": "online",
            "registered_users": users_count,
            "generations": total_usage
        })

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/status", dashboard)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ Web Health Check Server: http://0.0.0.0:{port}")
    await asyncio.Future()


# ============================================================
# TIZIMNI ISHGA TUSHIRISH
# ============================================================

async def main():
    init_db()

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN xatoligi: config.py yoki o'zgaruvchilarni tekshiring!")
        return

    await bot.delete_webhook(drop_pending_updates=True)

    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Boshlash"),
        BotCommand(command="limit", description="📊 Limitni tekshirish"),
    ])

    logger.info("=" * 50)
    logger.info("🤖 AI Professional Assistant Bot ishga tushdi.")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"🎁 Bepul limit: {FREE_LIMIT}")
    logger.info("=" * 50)

    # Web server va botni parallel rejimda ishga tushirish
    web_task = asyncio.create_task(run_web_server())
    polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))

    await asyncio.gather(web_task, polling_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("❌ Bot qo'lda to'xtatildi.")
    except Exception as e:
        logger.error(f"❌ Kutilmagan jiddiy xatolik yuz berdi: {e}")
