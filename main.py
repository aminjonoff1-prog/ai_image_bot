import os
import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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
# FOYDALANUVCHI HANDLERLARI
# ============================================================

@dp.message(Command("start"))
async def start_command(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    text = (
        f"👋 Salom, <b>{m.from_user.full_name}</b>!\n\n"
        f"🤖 Men AI media generator botman.\n\n"
        f"📋 <b>Imkoniyatlarim:</b>\n"
        f"🎨 Logo\n"
        f"🖼 Realistik rasm\n"
        f"📱 Avatar\n"
        f"🏠 Interyer\n"
        f"🌄 Landscape\n"
        f"🖥 UI/UX Web Dizayn\n"
        f"🏢 3D Arxitektura\n"
        f"💎 Brending\n"
        f"🎮 Konsept Art\n"
        f"🏢 Reklama Banneri\n"
        f"🎬 Video Generatsiya\n"
        f"🎵 Audio/Musiqa\n\n"
        f"⚡ Pastdagi menyudan kategoriyani tanlang."
    )
    await m.answer(text, reply_markup=main_menu())


@dp.message(Command("limit"))
async def limit_command(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    if is_admin(m.from_user.id):
        await m.answer("👑 <b>Siz adminsiz!</b>\nSizga limit qo'llanilmaydi.")
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
            f"👥 Jami foydalanuvchilar: <b>{users_count}</b> ta\n"
            f"🎨 Jami generatsiyalar: <b>{total_usage}</b> ta\n\n"
            f"⚙️ <b>Buyruqlar:</b>\n"
            f"<code>/send [matn]</code>\n"
            f"<code>/give [id] [son]</code>\n"
            f"<code>/reset [id]</code>\n"
            f"<code>/userinfo [id]</code>"
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
        await m.answer("❗ Yuboriladigan matnni kiriting.")
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
        f"✅ Yakunlandi\n\n"
        f"✔️ Yuborildi: <b>{success}</b>\n"
        f"❌ Yuborilmadi: <b>{failed}</b>"
    )


@dp.message(Command("give"))
async def give_limit_command(m: Message):
    if not is_admin(m.from_user.id):
        return

    try:
        parts = m.text.split()
        if len(parts) < 3:
            await m.answer("❗ Format: <code>/give [id] [son]</code>")
            return

        target_id = int(parts[1])
        amount = int(parts[2])

        success = add_premium_limit(target_id, amount)
        if success:
            await m.answer(f"✅ <code>{target_id}</code> ga +{amount} limit qo‘shildi.")
            try:
                await bot.send_message(
                    target_id,
                    f"🎉 Sizga +{amount} ta premium limit qo‘shildi!"
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
            await m.answer(f"✅ <code>{target_id}</code> limiti tiklandi.")
        else:
            await m.answer("❌ Foydalanuvchi topilmadi.")
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
            await m.answer("❌ Foydalanuvchi topilmadi.")
            return

        text = (
            f"👤 <b>Foydalanuvchi ma'lumoti</b>\n\n"
            f"🆔 ID: <code>{info['user_id']}</code>\n"
            f"📛 Ism: {info['full_name']}\n"
            f"🔗 Username: @{info['username']}\n"
            f"📅 Sana: {info['joined_date']}\n"
            f"📊 Ishlatilgan: {info['usage_count']}\n"
            f"💎 Premium: {info['premium_limit']}"
        )
        await m.answer(text)
    except Exception as e:
        await m.answer(f"Xato: {e}")


# ============================================================
# KATEGORIYALAR
# ============================================================

CATEGORIES = [
    "🎨 Logo",
    "🖼 Realistik",
    "📱 Avatar",
    "🏠 Interyer",
    "🌄 Landscape",
    "🖥 UI/UX Web Dizayn",
    "🏢 3D Arxitektura",
    "💎 Brending",
    "🎮 Konsept Art",
    "🏢 Reklama Banneri",
    "🎬 Video Generatsiya",
    "🎵 Audio/Musiqa",
]

@dp.message(F.text.in_(CATEGORIES))
async def category_handler(m: Message):
    user_category[m.from_user.id] = m.text

    messages = {
        "🎬 Video Generatsiya": "🎬 Video uchun tavsif yozing:",
        "🎵 Audio/Musiqa": "🎵 Audio yoki musiqa uchun tavsif yozing:",
        "🏢 Reklama Banneri": "🏢 Banner uchun fon va tasvir tavsifini yozing:",
    }

    await m.answer(messages.get(m.text, f"✍️ <b>{m.text}</b> uchun tavsif yozing:"))


# ============================================================
# GENERATSIYA
# ============================================================

@dp.message()
async def generate_handler(m: Message):
    user_id = m.from_user.id

    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang.")
        return

    user_text = m.text.strip()
    if not user_text:
        return

    if not is_admin(user_id) and not check_limit(user_id, FREE_LIMIT):
        await m.answer(
            "❌ <b>Limit tugadi.</b>\n\n"
            "Premium olish uchun adminga yozing.\n"
            f"🆔 Sizning ID: <code>{user_id}</code>"
        )
        return

    category = user_category.pop(user_id)

    if category == "🎬 Video Generatsiya":
        msg = await m.answer("⏳ Video tayyorlanmoqda...")
        f = None
        try:
            f, err = await generate_video(user_text)
            if f and os.path.exists(f):
                await m.answer_video(FSInputFile(f), caption="🎬 Video tayyor")
            else:
                await m.answer(f"❌ Xatolik: {err}")
        except Exception as e:
            await m.answer(f"❌ Xato: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)

    elif category == "🎵 Audio/Musiqa":
        msg = await m.answer("⏳ Audio tayyorlanmoqda...")
        f = None
        try:
            f, err = await generate_audio(user_text)
            if f and os.path.exists(f):
                await m.answer_audio(FSInputFile(f), caption="🎵 Audio tayyor")
            else:
                await m.answer(f"❌ Xatolik: {err}")
        except Exception as e:
            await m.answer(f"❌ Xato: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)

    else:
        msg = await m.answer("⏳ Rasm yaratilmoqda...")
        f = None
        try:
            f, err = await generate_image(user_text, category)
            if f and os.path.exists(f):
                await m.answer_photo(FSInputFile(f), caption=f"🎨 {category}")
            else:
                await m.answer(f"❌ Xatolik: {err}")
        except Exception as e:
            await m.answer(f"❌ Xato: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)


# ============================================================
# WEB SERVER
# ============================================================

async def run_web_server():
    app = web.Application()

    async def hp(request):
        return web.Response(text="OK")

    app.router.add_get("/", hp)
    app.router.add_get("/health", hp)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()


# ============================================================
# MAIN
# ============================================================

async def main():
    init_db()

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi")
        return

    await bot.delete_webhook(drop_pending_updates=True)

    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="limit", description="Limitni ko‘rish"),
    ])

    logger.info("Bot ishga tushdi.")
    await asyncio.gather(run_web_server(), dp.start_polling(bot, skip_updates=True))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to‘xtatildi.")
