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
from presentation_engine import create_professional_presentation

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
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
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
    """Foydalanuvchi admin ekanligini tekshiradi"""
    return user_id == ADMIN_ID


async def safe_delete(message):
    """Xatolik bermay xabarni o'chiradi"""
    try:
        await message.delete()
    except Exception:
        pass


async def safe_remove_file(filename: str):
    """Xatolik bermay faylni o'chiradi"""
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        logger.error(f"Faylni o'chirishda xato: {e}")


# ============================================================
# GEMINI MATN GENERATSIYA
# ============================================================

async def get_ai_content(topic: str, slide_num: int) -> str:
    """Prezentatsiya slaydi uchun matn yaratadi"""
    if not gemini_model:
        return f"{topic} mavzusining {slide_num}-qismi haqida ma'lumotlar."

    prompt = (
        f"Siz professional tahlilchisiz. '{topic}' mavzusida prezentatsiyaning "
        f"{slide_num}-slaydi uchun matn yozing.\n\n"
        f"Talablar:\n"
        f"- Qisqa va tizimli bo'lsin\n"
        f"- Aniq faktlarga asoslangan\n"
        f"- Universitet darajasiga mos akademik o'zbek tilida\n"
        f"- Hech qanday kirish so'zlarisiz\n"
        f"- To'g'ridan-to'g'ri slayd matnini bering\n"
        f"- 4-6 ta qisqa bullet point shaklida"
    )

    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        text = response.text.strip()
        return text if text else f"{topic} bo'yicha tahliliy ma'lumotlar."
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return f"{topic} mavzusi bo'yicha akademik matn."


# ============================================================
# PREZENTATSIYA YARATISH
# ============================================================

async def create_presentation(topic: str, user_id: int) -> str:
    """25 ta slayddan iborat prezentatsiya yaratadi"""
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
            paragraph.font.name = "Arial"

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


# ============================================================
# FOYDALANUVCHI KOMANDALARI
# ============================================================

@dp.message(Command("start"))
async def start_command(m: Message):
    """Botni boshlash"""
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    welcome_text = (
        f"👋 Salom, <b>{m.from_user.full_name}</b>!\n\n"
        f"🤖 Men AI yordamida dizayn yaratuvchi botman.\n\n"
        f"📋 <b>Mening imkoniyatlarim:</b>\n"
        f"🎨 Logo va brending\n"
        f"🖼 Realistik rasmlar\n"
        f"📱 Avatar va portretlar\n"
        f"🏠 Interyer dizayn\n"
        f"📊 25 ta slaydli prezentatsiya\n"
        f"🎬 Video yaratish\n"
        f"🎵 Musiqa yaratish\n\n"
        f"⚡ <b>Boshlash uchun pastdagi kategoriyalardan birini tanlang!</b>\n\n"
        f"ℹ️ /limit - qolgan limitingizni ko'rish"
    )

    await m.answer(welcome_text, reply_markup=main_menu())


@dp.message(Command("limit"))
async def limit_command(m: Message):
    """Foydalanuvchi o'z limitini ko'radi"""
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    # Admin uchun maxsus xabar
    if is_admin(m.from_user.id):
        await m.answer(
            "👑 <b>Siz adminsiz!</b>\n\n"
            "Sizga limitlar taalluqli emas. Cheksiz foydalanishingiz mumkin."
        )
        return

    info = get_limit_info(m.from_user.id, FREE_LIMIT)

    if not info:
        await m.answer("❌ Limit ma'lumotlari topilmadi. /start bosing.")
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
        text += (
            "\n\n❗ <b>Limitingiz tugagan!</b>\n"
            "Premium limit olish uchun: @muhammad_amin07"
        )

    await m.answer(text)


@dp.message(Command("help"))
async def help_command(m: Message):
    """Yordam komandasi"""
    text = (
        "ℹ️ <b>Yordam menyusi</b>\n\n"
        "🚀 /start - botni qayta ishga tushirish\n"
        "📊 /limit - qolgan limitingizni ko'rish\n"
        "ℹ️ /help - yordam menyusi\n\n"
        "❓ <b>Savollar bo'lsa:</b> @muhammad_amin07"
    )
    await m.answer(text)


# ============================================================
# ADMIN KOMANDALARI
# ============================================================

@dp.message(Command("admin"))
async def admin_panel(m: Message):
    """Admin panel - statistika"""
    if not is_admin(m.from_user.id):
        return

    try:
        users_count, total_usage = get_stats()
        text = (
            f"👑 <b>Admin Panel</b>\n\n"
            f"📊 <b>Statistika:</b>\n"
            f"👥 Jami foydalanuvchilar: <b>{users_count}</b> ta\n"
            f"🎨 Jami media yasalgan: <b>{total_usage}</b> marta\n\n"
            f"⚙️ <b>Admin komandalar:</b>\n"
            f"<code>/send [matn]</code> - hammaga xabar\n"
            f"<code>/give [id] [son]</code> - limit qo'shish\n"
            f"<code>/reset [id]</code> - limitni tiklash\n"
            f"<code>/userinfo [id]</code> - foydalanuvchi ma'lumoti\n"
        )
        await m.answer(text)
    except Exception as e:
        await m.answer(f"❌ Xatolik: {e}")


@dp.message(Command("send"))
async def broadcast_command(m: Message):
    """Hamma foydalanuvchilarga xabar yuborish"""
    if not is_admin(m.from_user.id):
        return

    text = m.text.replace("/send", "", 1).strip()
    if not text:
        await m.answer(
            "❗ Xabar matnini kiriting.\n"
            "Misol: <code>/send Assalomu alaykum!</code>"
        )
        return

    users = get_all_users()
    if not users:
        await m.answer("❌ Foydalanuvchilar topilmadi.")
        return

    msg = await m.answer(f"⏳ {len(users)} ta foydalanuvchiga yuborilmoqda...")

    success = 0
    failed = 0

    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await msg.edit_text(
        f"✅ <b>Xabar yuborildi</b>\n\n"
        f"✔️ Muvaffaqiyatli: <b>{success}</b>\n"
        f"❌ Xatolik: <b>{failed}</b>\n"
        f"📊 Jami: <b>{len(users)}</b>"
    )


@dp.message(Command("give"))
async def give_limit_command(m: Message):
    """Foydalanuvchiga premium limit qo'shish"""
    if not is_admin(m.from_user.id):
        return

    try:
        parts = m.text.split()
        if len(parts) < 3:
            await m.answer(
                "❗ <b>To'g'ri foydalanish:</b>\n"
                "<code>/give [user_id] [miqdor]</code>\n\n"
                "Misol: <code>/give 512345678 30</code>"
            )
            return

        target_user_id = int(parts[1])
        amount = int(parts[2])

        if amount <= 0:
            await m.answer("❌ Miqdor 0 dan katta bo'lishi kerak.")
            return

        success = add_premium_limit(target_user_id, amount)

        if success:
            await m.answer(
                f"✅ <b>Limit qo'shildi!</b>\n\n"
                f"👤 Foydalanuvchi: <code>{target_user_id}</code>\n"
                f"💎 Qo'shildi: <b>+{amount}</b> ta limit"
            )
            try:
                await bot.send_message(
                    target_user_id,
                    f"🎉 <b>Premium faollashtirildi!</b>\n\n"
                    f"💎 Sizga <b>+{amount}</b> ta yangi limit qo'shildi!\n"
                    f"📊 /limit - qolgan limitni ko'rish"
                )
            except Exception:
                await m.answer("⚠️ Foydalanuvchiga xabar yuborilmadi.")
        else:
            await m.answer(
                "❌ Foydalanuvchi topilmadi.\n"
                "U avval /start bosgan bo'lishi kerak."
            )

    except (IndexError, ValueError):
        await m.answer(
            "❗ <b>Xato format!</b>\n"
            "Misol: <code>/give 512345678 30</code>"
        )


@dp.message(Command("reset"))
async def reset_command(m: Message):
    """Foydalanuvchining ishlatgan limitini 0 ga tushirish"""
    if not is_admin(m.from_user.id):
        return

    try:
        parts = m.text.split()
        if len(parts) < 2:
            await m.answer(
                "❗ <b>To'g'ri foydalanish:</b>\n"
                "<code>/reset [user_id]</code>\n\n"
                "Misol: <code>/reset 512345678</code>"
            )
            return

        target_user_id = int(parts[1])
        success = reset_user_usage(target_user_id)

        if success:
            await m.answer(
                f"✅ <b>Limit tiklandi!</b>\n\n"
                f"👤 Foydalanuvchi: <code>{target_user_id}</code>\n"
                f"🔄 Ishlatilgan limit 0 ga tushirildi"
            )
        else:
            await m.answer("❌ Foydalanuvchi topilmadi.")

    except (IndexError, ValueError):
        await m.answer(
            "❗ <b>Xato format!</b>\n"
            "Misol: <code>/reset 512345678</code>"
        )


@dp.message(Command("userinfo"))
async def userinfo_command(m: Message):
    """Foydalanuvchi haqida to'liq ma'lumot"""
    if not is_admin(m.from_user.id):
        return

    try:
        parts = m.text.split()
        if len(parts) < 2:
            await m.answer(
                "❗ <b>To'g'ri foydalanish:</b>\n"
                "<code>/userinfo [user_id]</code>"
            )
            return

        target_user_id = int(parts[1])
        info = get_user_info(target_user_id)

        if not info:
            await m.answer("❌ Foydalanuvchi topilmadi.")
            return

        total_limit = FREE_LIMIT + info["premium_limit"]
        remaining = max(0, total_limit - info["usage_count"])

        username = f"@{info['username']}" if info["username"] and info["username"] != "Mavjud emas" else "Mavjud emas"

        text = (
            f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
            f"🆔 ID: <code>{info['user_id']}</code>\n"
            f"📛 Ism: <b>{info['full_name']}</b>\n"
            f"🔗 Username: {username}\n"
            f"📅 Qo'shilgan: {info['joined_date']}\n\n"
            f"📊 <b>Limit holati:</b>\n"
            f"🎁 Bepul: <b>{FREE_LIMIT}</b> ta\n"
            f"💎 Premium: <b>{info['premium_limit']}</b> ta\n"
            f"📌 Jami: <b>{total_limit}</b> ta\n"
            f"✅ Ishlatilgan: <b>{info['usage_count']}</b> ta\n"
            f"🔋 Qolgan: <b>{remaining}</b> ta"
        )

        await m.answer(text)

    except (IndexError, ValueError):
        await m.answer(
            "❗ <b>Xato format!</b>\n"
            "Misol: <code>/userinfo 512345678</code>"
        )


# ============================================================
# KATEGORIYA TANLASH
# ============================================================

CATEGORIES = [
    "🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer",
    "🌄 Landscape", "📊 Prezentatsiya", "🖥 UI/UX Web Dizayn",
    "🏢 3D Arxitektura", "💎 Brending", "🎮 Konsept Art",
    "🏢 Reklama Banneri", "🎬 Video Generatsiya", "🎵 Audio/Musiqa",
]


@dp.message(F.text.in_(CATEGORIES))
async def category_handler(m: Message):
    """Kategoriya tanlash"""
    user_category[m.from_user.id] = m.text

    messages = {
        "🏢 Reklama Banneri": (
            "✍️ <b>Reklama Banneri</b>\n\n"
            "Bannerda qanday tasvirlar bo'lishini xohlaysiz?\n\n"
            "❗ <i>AI matnlarni xato yozadi. Faqat fon va tasvirlarni yozing.</i>"
        ),
        "🎬 Video Generatsiya": (
            "🎬 <b>Google Veo Video Studio</b>\n\n"
            "Qanday video yaratishni xohlaysiz?\n"
            "Batafsil yozing - tizim mos klip tayyorlaydi."
        ),
        "🎵 Audio/Musiqa": (
            "🎵 <b>Google Lyria 3 Ovoz Studiyasi</b>\n\n"
            "Qanday janr va kayfiyatda musiqa kerak?\n\n"
            "<i>Misol: 'reklama uchun sokin royal ohangi'</i>"
        ),
        "📊 Prezentatsiya": (
            "📊 <b>Prezentatsiya Yaratish</b>\n\n"
            "Mavzuni yozing - 25 ta slaydli professional prezentatsiya tayyorlanadi.\n\n"
            "<i>Misol: 'O'zbekiston iqtisodiyoti 2024'</i>"
        ),
    }

    default_text = (
        f"✍️ <b>{m.text}</b>\n\n"
        f"Mavzu yoki tavsifni batafsil yozing.\n\n"
        f"<i>Qancha batafsil yozsangiz, natija shuncha yaxshi bo'ladi.</i>"
    )

    await m.answer(messages.get(m.text, default_text))


# ============================================================
# ASOSIY GENERATSIYA HANDLER
# ============================================================

@dp.message()
async def generate_handler(m: Message):
    """Asosiy generatsiya funksiyasi"""
    user_id = m.from_user.id

    # Kategoriya tanlanmaganmi?
    if user_id not in user_category:
        await m.answer(
            "❗ Avval kategoriya tanlang.\n"
            "/start - boshlash"
        )
        return

    # Limit tekshirish (admin cheklanmaydi)
    if not is_admin(user_id) and not check_limit(user_id, FREE_LIMIT):
        tariff_text = (
            "❌ <b>Bepul limitlaringiz tugadi!</b>\n\n"
            "💰 <b>Tariflar:</b>\n"
            "🎨 <b>Start (30 ta)</b> - 19,000 so'm\n"
            "🚀 <b>Professional (100 ta)</b> - 49,000 so'm\n"
            "👑 <b>Biznes (1 oy cheksiz)</b> - 99,000 so'm\n\n"
            "💳 <b>Karta (Uzcard/Humo):</b>\n"
            "<code>5614 6805 1876 1602</code>\n"
            "👤 Aminjonov Muhammadamin\n\n"
            "⚠️ <i>To'lov qilgach, chekni va ID raqamingizni adminga yuboring:</i>\n"
            "📱 @muhammad_amin07\n\n"
            f"🆔 <b>Sizning ID:</b> <code>{user_id}</code>"
        )
        await m.answer(tariff_text)
        return

    category_name = user_category.pop(user_id)
    user_text = m.text.strip()

    if not user_text:
        await m.answer("❗ Iltimos, tavsif yozing.")
        user_category[user_id] = category_name
        return

    # ===== PREZENTATSIYA =====
    if category_name == "📊 Prezentatsiya":
        msg = await m.answer("⏳ 25 ta slayd tayyorlanyapti (1-2 daqiqa)...")
        file = None
        try:
            file = await create_professional_presentation(user_text, user_id)
            await m.answer_document(
                FSInputFile(file),
                caption=f"📁 <b>Mavzu:</b> {user_text}\n✅ 25 ta slayd tayyor!"
            )
        except Exception as e:
            logger.error(f"Prezentatsiya xatosi: {e}")
            await m.answer(f"❌ <b>Xatolik:</b> {e}")
        finally:
            await safe_remove_file(file)
            await safe_delete(msg)

    # ===== VIDEO =====
    elif category_name == "🎬 Video Generatsiya":
        msg = await m.answer("⏳ Video tayyorlanmoqda va ovoz qo'shilmoqda...")
        file = None
        try:
            file, error = await generate_video(user_text)
            if file:
                await m.answer_video(
                    FSInputFile(file),
                    caption=f"🎬 <b>G'oya:</b> {user_text}\n🔥 Google Veo Studio"
                )
            else:
                await m.answer(f"❌ <b>Xatolik:</b> {error}")
        except Exception as e:
            logger.error(f"Video xatosi: {e}")
            await m.answer(f"❌ <b>Xatolik:</b> {e}")
        finally:
            await safe_remove_file(file)
            await safe_delete(msg)

    # ===== AUDIO =====
    elif category_name == "🎵 Audio/Musiqa":
        msg = await m.answer("⏳ Musiqa bastalanmoqda...")
        file = None
        try:
            file, error = await generate_audio(user_text)
            if file:
                await m.answer_audio(
                    FSInputFile(file),
                    caption=f"🎵 <b>Uslub:</b> {user_text}\n⚡ Google Lyria 3"
                )
            else:
                await m.answer(f"❌ <b>Xatolik:</b> {error}")
        except Exception as e:
            logger.error(f"Audio xatosi: {e}")
            await m.answer(f"❌ <b>Xatolik:</b> {e}")
        finally:
            await safe_remove_file(file)
            await safe_delete(msg)

    # ===== RASM =====
    else:
        msg = await m.answer("⏳ Rasm chizilmoqda...")
        file = None
        try:
            file, error = await generate_image(user_text, category_name)
            if file:
                await m.answer_photo(
                    FSInputFile(file),
                    caption=f"🎨 <b>{category_name}</b>\n📝 {user_text}"
                )
            else:
                await m.answer(f"❌ <b>Xatolik:</b> {error}")
        except Exception as e:
            logger.error(f"Rasm xatosi: {e}")
            await m.answer(f"❌ <b>Xatolik:</b> {e}")
        finally:
            await safe_remove_file(file)
            await safe_delete(msg)


# ============================================================
# WEB SERVER (UptimeRobot uchun)
# ============================================================

async def run_web_server():
    """UptimeRobot uchun health check server"""
    app = web.Application()

    async def health_check(request):
        return web.Response(text="✅ Bot is running!", status=200)

    async def status(request):
        users_count, total_usage = get_stats()
        return web.json_response({
            "status": "ok",
            "users": users_count,
            "total_usage": total_usage
        })

    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/status", status)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"✅ Web server: http://0.0.0.0:{port}")
    await asyncio.Future()


# ============================================================
# ASOSIY FUNKSIYA
# ============================================================

async def main():
    """Botni ishga tushirish"""
    # DB ni ishga tushirish
    init_db()

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN aniqlanmagan!")
        return

    if ADMIN_ID == 0:
        logger.warning("⚠️ ADMIN_ID o'rnatilmagan!")

    # Bot komandalari
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="limit", description="📊 Qolgan limit"),
        BotCommand(command="help", description="ℹ️ Yordam"),
    ])

    logger.info("=" * 50)
    logger.info("🚀 Bot ishga tushdi!")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info(f"🎁 Bepul limit: {FREE_LIMIT}")
    logger.info("=" * 50)

    # Web server va polling
    web_task = asyncio.create_task(run_web_server())
    polling_task = asyncio.create_task(
        dp.start_polling(bot, skip_updates=True)
    )

    await asyncio.gather(web_task, polling_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("❌ Bot to'xtatildi")
    except Exception as e:
        logger.error(f"❌ Kutilmagan xatolik: {e}")
