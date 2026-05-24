import os
import asyncio
import logging
import time
import re

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
    # Eslatma: Agar increment_usage funksiyangiz bo'lsa, shuni ham import qiling
)

# --- MODULLAR ---
from keyboards import main_menu
from image_gen import generate_image
from video_gen import generate_video
from audio_gen import generate_audio
from coursework_gen import generate_coursework

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- GEMINI SOZLAMALARI ---
MODEL_NAMES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

primary_gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        primary_gemini_model = genai.GenerativeModel(MODEL_NAMES[0])
        logger.info("✅ Gemini muvaffaqiyatli yuklandi")
    except Exception as e:
        logger.warning(f"⚠️ Gemini init xatosi: {e}")
        primary_gemini_model = None

# --- BOT VA DISPATCHER ---
bot = Bot(
    token=BOT_TOKEN.strip(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# --- FOYDALANUVCHI HOLATLARI ---
user_category = {}

# ============================================================
# YORDAMCHI FUNKSIYALAR (Helper Functions)
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


# --- DIZAYN FUNKSIYALARI (Yangilangan) ---

def set_slide_background(slide, color1, color2=None):
    """
    Slaydga qattiq rang yoki gradient (ranglar aralashmasi) beradi.
    """
    fill = slide.background.fill
    if color2:
        # Gradient rejim
        fill.gradient()
        fill.gradient_angle = 90
        # Gradient to'xtash nuqtalari (stops)
        fill.gradient_stops[0].color.rgb = color1
        fill.gradient_stops[1].color.rgb = color2
    else:
        # Oddiy qattiq rang
        fill.solid()
        fill.fore_color.rgb = color1


def add_title(slide, title_text, subtitle_text="", dark=True):
    title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(8.8), Inches(1.0))
    tf = title_box.text_frame
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    p1.text = title_text
    p1.font.name = "Georgia"
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(11, 29, 58) if dark else RGBColor(255, 255, 255)

    if subtitle_text:
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.name = "Calibri"
        p2.font.size = Pt(12)
        p2.font.color.rgb = RGBColor(0, 102, 204) if dark else RGBColor(212, 175, 55)
        p2.space_before = Pt(3)


def add_footer(slide, topic, num):
    footer_box = slide.shapes.add_textbox(Inches(0.6), Inches(6.85), Inches(8.8), Inches(0.3))
    tf = footer_box.text_frame
    p = tf.paragraphs[0]
    p.text = f"Loyiha: {topic[:35]}... | Slayd {num}/25 | Maxfiy"
    p.font.name = "Calibri"
    p.font.size = Pt(9)
    p.font.color.rgb = RGBColor(130, 130, 130)


def add_bullets_block(slide, bullets, left=0.7, top=1.55, width=5.0, height=4.6):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True

    for i, bullet in enumerate(bullets[:5]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"• {bullet}"
        p.font.name = "Calibri"
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(40, 50, 65)
        p.space_after = Pt(10)
        p.line_spacing = 1.12


def add_callout_card(slide, title, text, left=6.1, top=1.65, width=3.1, height=4.5):
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor(255, 255, 255)
    card.line.color.rgb = RGBColor(0, 102, 204)
    card.line.width = Pt(1.2)

    box = slide.shapes.add_textbox(Inches(left + 0.12), Inches(top + 0.15), Inches(width - 0.24), Inches(height - 0.3))
    tf = box.text_frame
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    p1.text = title
    p1.font.name = "Calibri"
    p1.font.size = Pt(12)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(0, 102, 204)
    p1.space_after = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = text
    p2.font.name = "Georgia"
    p2.font.size = Pt(13)
    p2.font.color.rgb = RGBColor(11, 29, 58)
    p2.line_spacing = 1.18


def add_kpi_cards(slide, items, left=0.75, top=1.75):
    card_w = 1.52
    card_h = 1.35
    gap = 0.12

    for i, item in enumerate(items[:3]):
        x = left + i * (card_w + gap)
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(x), Inches(top), Inches(card_w), Inches(card_h)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(255, 255, 255)
        card.line.color.rgb = RGBColor(220, 225, 230)
        card.line.width = Pt(1)

        box = slide.shapes.add_textbox(Inches(x + 0.08), Inches(top + 0.08), Inches(card_w - 0.16), Inches(card_h - 0.16))
        tf = box.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = f"{i + 1}"
        p1.font.name = "Georgia"
        p1.font.size = Pt(20)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(0, 102, 204)

        p2 = tf.add_paragraph()
        p2.text = item[:55]
        p2.font.name = "Calibri"
        p2.font.size = Pt(10)
        p2.font.color.rgb = RGBColor(50, 60, 75)
        p2.space_before = Pt(6)

# ============================================================
# AI VA LOGIKA
# ============================================================

async def gemini_generate_text(prompt: str) -> str:
    """Gemini dan matn olish uchun xavfsiz helper."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY topilmadi")

    model_names = MODEL_NAMES[:]

    if primary_gemini_model:
        try:
            response = await asyncio.to_thread(primary_gemini_model.generate_content, prompt)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            logger.warning(f"Primary Gemini model xatosi: {e}")

    last_error = None
    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            response = await asyncio.to_thread(model.generate_content, prompt)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as e:
            last_error = e
            logger.warning(f"Gemini model xatosi ({model_name}): {e}")

    raise last_error if last_error else RuntimeError("Gemini javobi olinmadi")


async def get_ai_slide_content(topic, slide_num):
    """Har bir slayd uchun strukturalangan kontent qaytaradi."""
    if slide_num <= 5:
        stage = "Kirish va dolzarblik"
    elif slide_num <= 12:
        stage = "Asosiy tahlil"
    elif slide_num <= 19:
        stage = "Strategik yondashuv"
    else:
        stage = "Xulosa va tavsiyalar"

    default_data = {
        "title": f"{stage} | {slide_num}-slayd",
        "subtitle": f"{topic} bo'yicha tizimli tahlil",
        "bullets": [
            f"{topic} mavzusining asosiy jihatlari",
            "Muammo va imkoniyatlarning tahlili",
            "Strategik yo'nalishlar",
            "Amaliy tavsiyalar",
        ],
        "callout": "Tahlil natijasida eng muhim strategik xulosa shu slaydda beriladi."
    }

    if not GEMINI_API_KEY:
        return default_data

    prompt = f"""
Siz professional konsalting kompaniya strategisiz va akademik yozuvchisiz.

MAVZU:
{topic}

SLAYD RAQAMI:
{slide_num}

SLAYD BOSQICHI:
{stage}

QAT'IY FORMATDA JAVOB BERING:
TITLE: [qisqa va kuchli sarlavha]
SUBTITLE: [kichik strategik sarlavha]
BULLETS:
- [1-qisqa tahliliy nuqta]
- [2-qisqa tahliliy nuqta]
- [3-qisqa tahliliy nuqta]
- [4-qisqa tahliliy nuqta]
CALLOUT: [1 qatorlik eng muhim xulosa]

QOIDALAR:
- Faqat o'zbek tilida yozing
- Qisqa, akademik va professional bo'lsin
- Hech qanday izoh qo'shmang
- Markdown ishlatmang
- Bulletlar 4 tadan oshmasin
"""

    try:
        text = await gemini_generate_text(prompt)
        data = {
            "title": default_data["title"],
            "subtitle": default_data["subtitle"],
            "bullets": [],
            "callout": default_data["callout"],
        }

        current_section = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            upper = line.upper()

            if upper.startswith("TITLE:"):
                data["title"] = line.split(":", 1)[1].strip()
            elif upper.startswith("SUBTITLE:"):
                data["subtitle"] = line.split(":", 1)[1].strip()
            elif upper.startswith("BULLETS:"):
                current_section = "bullets"
            elif upper.startswith("CALLOUT:"):
                data["callout"] = line.split(":", 1)[1].strip()
                current_section = None
            elif current_section == "bullets":
                clean = re.sub(r"^[-•*\d\.\)\s]+", "", line).strip()
                if clean:
                    data["bullets"].append(clean)

        if not data["bullets"]:
            data["bullets"] = default_data["bullets"]

        return data

    except Exception as e:
        logger.error(f"Gemini slayd xatosi: {e}")
        return default_data


async def add_image_to_right_panel(slide, topic, slide_num):
    """
    O‘ng panelga rasm yoki placeholder qo‘shadi.
    """
    prompt = (
        f"{topic}, professional corporate minimalist illustration, "
        f"flat design, vector art, white background, high quality, 16:9"
    )

    img_added = False
    
    # Rasm yaratishga urinish
    try:
        img_file, error = await generate_image(prompt, "🖼 Realistik")
        if img_file and os.path.exists(img_file):
            # Rasmni joylashtirish
            slide.shapes.add_picture(
                img_file,
                Inches(5.9), Inches(1.6),
                width=Inches(3.8),
                height=Inches(4.0)
            )
            img_added = True
            await safe_remove_file(img_file)
        else:
            logger.info(f"Rasm API'dan kelmadi: {error}")
    except Exception as e:
        logger.error(f"Rasm qo'shish xatosi: {e}")

    # AGAR RASM KELMASA, UNI O'RNIGA PREMIUM "PLACEHOLDER" QO'YAMIZ
    if not img_added:
        # Shaffof fonli romb/shakl
        placeholder = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, 
            Inches(6.0), Inches(1.6), 
            Inches(3.6), Inches(4.0)
        )
        placeholder.fill.solid()
        placeholder.fill.fore_color.rgb = RGBColor(240, 244, 248) # Juda och ko'k
        placeholder.line.color.rgb = RGBColor(0, 102, 204)
        placeholder.line.width = Pt(2)

        # Placeholder ichiga matn (katta ikonka kabi)
        text_box = slide.shapes.add_textbox(
            Inches(6.2), Inches(3.0), 
            Inches(3.2), Inches(1.2)
        )
        tf = text_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"🖼️ VISUAL CONCEPT\n{topic[:20]}..."
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = RGBColor(100, 100, 100)
        p.alignment = PP_ALIGN.CENTER

    return img_added


# ============================================================
# PREZENTATSIYA YARATISH (YANGILANGAN MURAKKAB DIZAYN)
# ============================================================

async def create_presentation(topic: str, user_id: int) -> str:
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    blank = prs.slide_layouts[6]

    # Ranglar
    dark_navy = RGBColor(11, 29, 58)
    light_blue = RGBColor(235, 242, 250)
    white = RGBColor(255, 255, 255)
    accent_blue = RGBColor(0, 102, 204)
    gold = RGBColor(212, 175, 55)
    text_dark = RGBColor(40, 50, 65)

    # 1. COVER SLIDE (Gradient fon)
    slide = prs.slides.add_slide(blank)
    set_slide_background(slide, dark_navy, RGBColor(40, 60, 90)) # Gradient qo'shildi

    # dekorativ bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(6.65),
        Inches(10), Inches(0.85)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_blue
    bar.line.fill.background

    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.1), Inches(8.4), Inches(1.7))
    tf = title_box.text_frame
    tf.word_wrap = True

    p1 = tf.paragraphs[0]
    p1.text = topic.upper()
    p1.font.name = "Georgia"
    p1.font.size = Pt(30)
    p1.font.bold = True
    p1.font.color.rgb = white

    p2 = tf.add_paragraph()
    p2.text = "STRATEGIK TAHLILIY PREZENTATSIYA\nAI yordamida tayyorlandi"
    p2.font.name = "Calibri"
    p2.font.size = Pt(15)
    p2.font.bold = True
    p2.font.color.rgb = gold
    p2.space_before = Pt(16)

    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(2.1), Inches(4.9),
        Inches(5.8), Inches(0.55)
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = white
    badge.line.fill.background

    badge_text = slide.shapes.add_textbox(Inches(2.2), Inches(5.03), Inches(5.6), Inches(0.3))
    tfb = badge_text.text_frame
    pb = tfb.paragraphs[0]
    pb.text = "25 ta premium slayd | AI Generated Design"
    pb.font.name = "Calibri"
    pb.font.size = Pt(12)
    pb.font.bold = True
    pb.font.color.rgb = dark_navy
    pb.alignment = PP_ALIGN.CENTER

    # 2. AGENDA SLIDE
    slide = prs.slides.add_slide(blank)
    set_slide_background(slide, white, light_blue) # Oq va och ko'k gradient
    add_title(slide, "Mundarija", "Prezentatsiyaning asosiy bo'limlari")
    add_bullets_block(
        slide,
        [
            "Mavzuning dolzarbligi va umumiy tavsifi",
            "Asosiy tendensiyalar va rivojlanish omillari",
            "Muammo va imkoniyatlarning tahlili",
            "Strategik yechimlar va ustuvor yo'nalishlar",
            "Yakuniy xulosa va tavsiyalar",
        ],
        left=0.9,
        top=1.7,
        width=5.0,
        height=4.5
    )
    add_callout_card(
        slide,
        "PREZENTATSIYA MAQSADI",
        "Ushbu loyiha mavzuni chuqur tahlil qilib, amaliy va strategik xulosalar berish uchun tayyorlandi.",
        left=6.15,
        top=1.7,
        width=3.05,
        height=4.5
    )
    add_footer(slide, topic, 2)

    # 3-25 SLAYDLAR (Murakkab layoutlar)
    for num in range(3, 26):
        slide = prs.slides.add_slide(blank)
        
        # Har 3 slaydda bir fon o'zgarib turadi (Turli xil gradientlar)
        if num % 3 == 0:
            set_slide_background(slide, white, RGBColor(245, 245, 255))
        elif num % 3 == 1:
            set_slide_background(slide, RGBColor(248, 250, 252), white)
        else:
            set_slide_background(slide, white)

        s_data = await get_ai_slide_content(topic, num)

        # Sarlavha
        add_title(
            slide,
            s_data.get("title", f"{num}-slayd"),
            s_data.get("subtitle", ""),
            dark=True
        )

        bullets = s_data.get("bullets", [])
        callout = s_data.get("callout", "Strategik xulosa.")

        # --- LAYOUT 1: Split Screen (Chapda matn, o'ngda rasm/placeholder) ---
        if num % 2 == 0: 
            # Chap qism - Matn
            text_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(5.0), Inches(5.0))
            tf = text_box.text_frame
            tf.word_wrap = True
            for i, b in enumerate(bullets):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"• {b}"
                p.font.name = "Calibri"
                p.font.size = Pt(16)
                p.font.color.rgb = RGBColor(50, 50, 50)
                p.space_after = Pt(12)
            
            # O'ng qism - Rasm yoki Placeholder
            img_added = await add_image_to_right_panel(slide, topic, num)
            
            if not img_added:
                # Agar rasm bo'lmasa, o'ng tomonga katta xulosa qo'yamiz
                add_callout_card(
                    slide, 
                    "ASOSIY XULOSA", 
                    callout, 
                    left=5.8, 
                    top=1.6, 
                    width=3.6, 
                    height=4.0
                )

        # --- LAYOUT 2: Centered Focus (Markaziy dizayn) ---
        else:
            # Markazda katta konteyner
            center_box = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, 
                Inches(0.6), Inches(1.5), 
                Inches(8.8), Inches(5.0)
            )
            center_box.fill.solid()
            center_box.fill.fore_color.rgb = white # Oq quti
            center_box.line.color.rgb = accent_blue
            center_box.line.width = Pt(1)
            center_box.shadow.inherit = False

            # Ichiga matn
            inner_tf = center_box.text_frame
            inner_tf.word_wrap = True
            inner_tf.margin_top = Inches(0.2)
            inner_tf.margin_bottom = Inches(0.2)
            inner_tf.margin_left = Inches(0.2)
            inner_tf.margin_right = Inches(0.2)

            # Sarlavha ichida
            p_title = inner_tf.paragraphs[0]
            p_title.text = "TAHLIL VA STATISTIKA"
            p_title.font.bold = True
            p_title.font.size = Pt(18)
            p_title.font.color.rgb = accent_blue
            p_title.alignment = PP_ALIGN.CENTER

            # Bulletlar
            for i, b in enumerate(bullets):
                p = inner_tf.add_paragraph()
                p.text = b
                p.font.size = Pt(16)
                p.alignment = PP_ALIGN.CENTER
                p.space_after = Pt(15)
            
            # Pastki izoh
            p_foot = inner_tf.add_paragraph()
            p_foot.text = f"— {callout} —"
            p_foot.font.italic = True
            p_foot.font.size = Pt(14)
            p_foot.font.color.rgb = RGBColor(100, 100, 100)
            p_foot.alignment = PP_ALIGN.CENTER

        add_footer(slide, topic, num)

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
        await m.answer(
            "👑 <b>Siz adminsiz!</b>\n\n"
            "Sizga hech qanday cheklov va limitlar taalluqli emas."
        )
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
    if info["remaining"] == 0:
        text += "\n\n❗ Bepul limitlar tugagan, premium olish uchun adminga bog'laning."

    await m.answer(text)


@dp.message(Command("help"))
async def help_command(m: Message):
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "• /start — botni boshlash\n"
        "• /limit — qolgan limitni ko'rish\n"
        "• /help — yordam\n"
    )
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

        if amount <= 0:
            await m.answer("❗ Miqdor 0 dan katta bo'lishi kerak.")
            return

        success = add_premium_limit(target_id, amount)

        if success:
            await m.answer(
                f"✅ Foydalanuvchi <code>{target_id}</code> hisobiga +{amount} ta premium limit qo'shildi!"
            )
            try:
                await bot.send_message(
                    target_id,
                    f"🎉 Premium faollashtirildi!\nHisobingizga +{amount} yangi imkoniyatlar qo'shildi!"
                )
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

        username = info.get("username")
        safe_username = f"@{username}" if username and username != "Mavjud emas" else "Mavjud emas"

        text = (
            f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
            f"🆔 ID: <code>{info['user_id']}</code>\n"
            f"📛 Ism: {info['full_name']}\n"
            f"🔗 Username: {safe_username}\n"
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
        ),
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
        await m.answer("❗ Avval kategoriyalardan birini tanlang yoki /start bosing.")
        return

    user_text = (m.text or "").strip()
    if not user_text:
        await m.answer("❗ Tushunarsiz yoki bo'sh so'rov. Iltimos, qayta yozing.")
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

    category_name = user_category.pop(user_id, None)
    if not category_name:
        await m.answer("❗ Kategoriya topilmadi. /start bosing.")
        return

    # === 1. KURS ISHI ===
    if category_name == "📚 Kurs Ishi":
        msg = await m.answer(
            "⏳ <b>Mukammal ilmiy ish yozilmoqda...</b>\n"
            "Barcha sahifalar, mundarija va adabiyotlar shakllantirilyapti. Bu bir necha daqiqa olishi mumkin."
        )
        file_path = None
        try:
            file_path = await generate_coursework(user_text, user_id)
            if not file_path or not os.path.exists(file_path):
                raise RuntimeError("Kurs ishi fayli yaratilmadi")

            await m.answer_document(
                FSInputFile(file_path),
                caption=f"📚 <b>Kurs Ishi Tayyor!</b>\n\n📝 <b>Mavzu:</b> {user_text}\n📂 Times New Roman standardida Word (DOCX) fayl."
            )
        except Exception as e:
            logger.error(f"Kurs ishi xatosi: {e}")
            user_category[user_id] = category_name
            await m.answer(f"❌ Kurs ishini yaratishda xatolik yuz berdi: {e}")
        finally:
            await safe_remove_file(file_path)
            await safe_delete(msg)

    # === 2. PREZENTATSIYA ===
    elif category_name == "📊 Prezentatsiya":
        msg = await m.answer(
            "⏳ <b>McKinsey Consulting Presentation Engine</b> ishga tushirildi.\n"
            "25 ta premium slaydlar tayyorlanmoqda (1-2 daqiqa)..."
        )
        file_path = None
        try:
            file_path = await create_presentation(user_text, user_id)
            if not file_path or not os.path.exists(file_path):
                raise RuntimeError("Prezentatsiya fayli yaratilmadi")

            await m.answer_document(
                FSInputFile(file_path),
                caption=f"📊 <b>Prezentatsiya Tayyor!</b>\n\n📝 <b>Mavzu:</b> {user_text}\n🏆 25 ta McKinsey andozasidagi professional tahlil slaydlari."
            )
        except Exception as e:
            logger.error(f"Prezentatsiya xatosi: {e}")
            user_category[user_id] = category_name
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
            if file_path and os.path.exists(file_path):
                await m.answer_video(
                    FSInputFile(file_path),
                    caption=f"🎬 <b>Video:</b> {user_text}\n🔥 Google Veo Video Studio"
                )
            else:
                raise RuntimeError(error or "Video yaratilmadi")
        except Exception as e:
            logger.error(f"Video xatosi: {e}")
            user_category[user_id] = category_name
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
            if file_path and os.path.exists(file_path):
                await m.answer_audio(
                    FSInputFile(file_path),
                    caption=f"🎵 <b>Musiqa:</b> {user_text}\n⚡ Google Lyria 3"
                )
            else:
                raise RuntimeError(error or "Audio yaratilmadi")
        except Exception as e:
            logger.error(f"Audio xatosi: {e}")
            user_category[user_id] = category_name
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
            if file_path and os.path.exists(file_path):
                await m.answer_photo(
                    FSInputFile(file_path),
                    caption=f"🎨 <b>Kategoriya:</b> {category_name}\n📝 {user_text}"
                )
            else:
                raise RuntimeError(error or "Tasvir yaratilmadi")
        except Exception as e:
            logger.error(f"Rasm xatosi: {e}")
            user_category[user_id] = category_name
            await m.answer(f"❌ Tasvir yaratishda xato: {e}")
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

    # TelegramConflictError oldini olish uchun webhookni tozalaymiz
    await bot.delete_webhook(drop_pending_updates=True)

    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Boshlash"),
        BotCommand(command="limit", description="📊 Limitni tekshirish"),
        BotCommand(command="help", description="ℹ️ Yordam"),
    ])

    logger.info("=" * 50)
    logger.info("🤖 AI Professional Assistant Bot ishga tushdi.")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"🎁 Bepul limit: {FREE_LIMIT}")
    logger.info("=" * 50)

    web_task = asyncio.create_task(run_web_server())
    polling_task = asyncio.create_task(dp.start_polling(bot))

    await asyncio.gather(web_task, polling_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("❌ Bot qo'lda to'xtatildi.")
    except Exception as e:
        logger.error(f"❌ Kutilmagan jiddiy xatolik yuz berdi: {e}")
