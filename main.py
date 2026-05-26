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
    from config import BOT_TOKEN, FREE_LIMIT, ADMIN_ID
except ImportError:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))
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
from name_logo import generate_name_logo_info

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
# PROMPT NAMUNALARI (Har bir kategoriya uchun)
# ============================================================

PROMPT_EXAMPLES = {
    "🎨 Logo": (
        "🎨 <b>Logo — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern minimalist logo for [brand name], black and gold, luxury style</code>\n\n"
        "2️⃣ <code>Clean tech startup logo for [name], blue and white, vector style</code>\n\n"
        "3️⃣ <code>Elegant fashion logo for [name], premium typography, minimalist</code>\n\n"
        "4️⃣ <code>Coffee shop logo for [name], warm colors, vintage branding</code>\n\n"
        "5️⃣ <code>Real estate logo for [name], gold and dark navy, luxury design</code>\n\n"
        "💡 <i>[name] o'rniga o'z nomingizni yozing yoki o'zbekcha yozing.</i>\n\n"
        "✍️ Endi promptingizni yozing:"
    ),
    "🖼 Realistik": (
        "🖼 <b>Realistik Rasm — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Realistic photo of sunset over mountains, golden hour, 8k</code>\n\n"
        "2️⃣ <code>Photorealistic portrait of elderly man with wise eyes, natural light</code>\n\n"
        "3️⃣ <code>Realistic aerial view of Samarkand city, cinematic, detailed</code>\n\n"
        "4️⃣ <code>Ultra realistic red Ferrari on desert road, motion blur</code>\n\n"
        "5️⃣ <code>Realistic photo of traditional Uzbek food on wooden table</code>\n\n"
        "💡 <i>O'zbekcha ham yozishingiz mumkin: 'quyosh', 'tog'lar', 'mashina'</i>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "📱 Avatar": (
        "📱 <b>Avatar — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Professional business avatar, young man in suit, studio lighting</code>\n\n"
        "2️⃣ <code>Anime style avatar of girl with blue hair, vibrant colors</code>\n\n"
        "3️⃣ <code>3D cartoon avatar of smiling boy, Pixar style, friendly look</code>\n\n"
        "4️⃣ <code>Gaming avatar, cyberpunk warrior, neon lights, futuristic</code>\n\n"
        "5️⃣ <code>Minimalist flat avatar for social media, pastel colors</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🏠 Interyer": (
        "🏠 <b>Interyer Dizayn — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern living room interior, minimalist, white and wood, cozy lighting</code>\n\n"
        "2️⃣ <code>Luxury bedroom design, dark theme, gold accents, premium feel</code>\n\n"
        "3️⃣ <code>Traditional Uzbek style guest room, colorful patterns, warm atmosphere</code>\n\n"
        "4️⃣ <code>Modern kitchen interior, marble countertop, Scandinavian style</code>\n\n"
        "5️⃣ <code>Cozy cafe interior design, industrial style, exposed brick walls</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🌄 Landscape": (
        "🌄 <b>Landscape — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Beautiful mountain landscape, green valley, river, sunrise</code>\n\n"
        "2️⃣ <code>Desert landscape at sunset, sand dunes, golden light</code>\n\n"
        "3️⃣ <code>Tropical island beach, crystal clear water, palm trees</code>\n\n"
        "4️⃣ <code>Winter forest landscape, snow covered trees, northern lights</code>\n\n"
        "5️⃣ <code>Uzbekistan countryside, cotton fields, blue sky</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🖥 UI/UX Web Dizayn": (
        "🖥 <b>UI/UX Web Dizayn — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern SaaS landing page design, dark theme, clean interface</code>\n\n"
        "2️⃣ <code>E-commerce website UI, fashion store, minimalist, white background</code>\n\n"
        "3️⃣ <code>Mobile app UI design, food delivery, colorful, user friendly</code>\n\n"
        "4️⃣ <code>Dashboard UI design, analytics, dark mode, professional charts</code>\n\n"
        "5️⃣ <code>Portfolio website design, creative agency, modern layout</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🏢 3D Arxitektura": (
        "🏢 <b>3D Arxitektura — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern 3D house exterior, minimalist, white concrete, glass windows</code>\n\n"
        "2️⃣ <code>Luxury villa 3D render, swimming pool, garden, sunset lighting</code>\n\n"
        "3️⃣ <code>Modern office building exterior, glass facade, urban environment</code>\n\n"
        "4️⃣ <code>Traditional Uzbek mosque 3D render, blue tiles, detailed ornaments</code>\n\n"
        "5️⃣ <code>Skyscraper concept design, futuristic, eco friendly, green building</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "💎 Brending": (
        "💎 <b>Brending — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Complete brand identity for [name], business cards, letterhead, elegant</code>\n\n"
        "2️⃣ <code>Premium coffee brand mockup, packaging, cup design, warm tones</code>\n\n"
        "3️⃣ <code>Fashion brand stationery set, black and gold, luxury presentation</code>\n\n"
        "4️⃣ <code>Tech startup brand kit, blue gradient, modern, professional</code>\n\n"
        "5️⃣ <code>Restaurant brand identity, menu card, logo, vintage style</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🎮 Konsept Art": (
        "🎮 <b>Konsept Art — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Fantasy medieval castle, epic lighting, dragons in sky, detailed</code>\n\n"
        "2️⃣ <code>Cyberpunk city street, neon lights, rain, futuristic vehicles</code>\n\n"
        "3️⃣ <code>Sci-fi space station interior, astronaut, detailed environment</code>\n\n"
        "4️⃣ <code>Ancient Silk Road scene, Samarkand, caravan, historical art</code>\n\n"
        "5️⃣ <code>Underwater fantasy world, coral reef, mythical sea creatures</code>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🏢 Reklama Banneri": (
        "🏢 <b>Reklama Banneri — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Sale banner background, vibrant colors, abstract shapes, empty text area</code>\n\n"
        "2️⃣ <code>Real estate banner, modern buildings, blue sky, clean composition</code>\n\n"
        "3️⃣ <code>Food delivery banner, fresh fruits, bright background, appetizing</code>\n\n"
        "4️⃣ <code>Tech product launch banner, dark gradient, spotlight, premium feel</code>\n\n"
        "5️⃣ <code>Education banner, books, students, bright and friendly colors</code>\n\n"
        "❗ <i>AI matnlarni xato yozadi. Faqat fon va rasmlarni yozing.</i>\n\n"
        "✍️ Endi tavsifingizni yozing:"
    ),
    "🔤 Ism Logo": (
        "🔤 <b>Ism Logo bo'limi</b>\n\n"
        "Ism yoki brand nomi yozing.\n\n"
        "Bot sizga:\n"
        "📖 Ism ma'nosini yozadi\n"
        "💡 Logo g'oyasini beradi\n"
        "🧠 Professional prompt yaratadi\n"
        "🎨 Logo rasm chizib beradi\n\n"
        "<b>Masalan:</b>\n"
        "• Muhammadamin\n"
        "• Zilola\n"
        "• Samarqand Coffee\n"
        "• Amir Tech\n\n"
        "✍️ Endi ism yoki nom yozing:"
    ),
}


# ============================================================
# FOYDALANUVCHI HANDLERLARI
# ============================================================

@dp.message(Command("start"))
async def start_command(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    text = (
        f"👋 Salom, <b>{m.from_user.full_name}</b>!\n\n"
        f"🤖 Men AI rasm va dizayn generator botman.\n\n"
        f"📋 <b>Imkoniyatlarim:</b>\n"
        f"🎨 Logo — professional logotip\n"
        f"🖼 Realistik — haqiqiy foto sifatida rasm\n"
        f"📱 Avatar — profil rasmi\n"
        f"🏠 Interyer — uy dizayn\n"
        f"🌄 Landscape — tabiat manzaralari\n"
        f"🖥 UI/UX — web dizayn\n"
        f"🏢 3D Arxitektura — bino loyihalari\n"
        f"💎 Brending — brand identifikatsiya\n"
        f"🎮 Konsept Art — fantastik san'at\n"
        f"🏢 Reklama Banneri — reklama foni\n"
        f"🔤 Ism Logo — ismga mos logo\n\n"
        f"⚡ Pastdagi menyudan kategoriyani tanlang!\n\n"
        f"📊 /limit — qolgan limitingizni ko'rish"
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
        f"🎁 Bepul: <b>{FREE_LIMIT}</b> ta\n"
        f"💎 Premium: <b>{info['premium_limit']}</b> ta\n"
        f"📌 Umumiy: <b>{info['total_limit']}</b> ta\n"
        f"✅ Ishlatilgan: <b>{info['usage_count']}</b> ta\n"
        f"🔋 Qolgan: <b>{info['remaining']}</b> ta\n\n"
        f"🆔 Sizning ID: <code>{m.from_user.id}</code>"
    )

    if info["remaining"] == 0:
        text += (
            "\n\n❗ <b>Limitingiz tugagan!</b>\n\n"
            "💰 <b>Tariflar:</b>\n"
            "🎨 Start (30 ta) — 19,000 so'm\n"
            "🚀 Professional (100 ta) — 49,000 so'm\n"
            "👑 Biznes (cheksiz) — 99,000 so'm\n\n"
            "💳 Karta: <code>5614 6805 1876 1602</code>\n"
            "👤 Aminjonov Muhammadamin\n"
            "📱 Admin: @muhammad_amin07"
        )

    await m.answer(text)


@dp.message(Command("help"))
async def help_command(m: Message):
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "🚀 /start — botni boshlash\n"
        "📊 /limit — qolgan limitni ko'rish\n"
        "ℹ️ /help — yordam\n\n"
        "❓ Savollar: @muhammad_amin07"
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
            f"👥 Foydalanuvchilar: <b>{users_count}</b> ta\n"
            f"🎨 Generatsiyalar: <b>{total_usage}</b> ta\n\n"
            f"⚙️ <b>Buyruqlar:</b>\n"
            f"<code>/send [matn]</code> — xabar yuborish\n"
            f"<code>/give [id] [son]</code> — limit qo'shish\n"
            f"<code>/reset [id]</code> — limitni tiklash\n"
            f"<code>/userinfo [id]</code> — ma'lumot olish"
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
        await m.answer("❗ Matnni kiriting. Misol: <code>/send Salom!</code>")
        return

    users = get_all_users()
    msg = await m.answer(f"⏳ {len(users)} foydalanuvchiga yuborilmoqda...")

    success, failed = 0, 0
    for u_id in users:
        try:
            await bot.send_message(u_id, text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await msg.edit_text(
        f"✅ Yakunlandi\n"
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

        if amount <= 0:
            await m.answer("❌ Miqdor 0 dan katta bo'lishi kerak.")
            return

        success = add_premium_limit(target_id, amount)
        if success:
            await m.answer(
                f"✅ <code>{target_id}</code> ga <b>+{amount}</b> limit qo'shildi."
            )
            try:
                await bot.send_message(
                    target_id,
                    f"🎉 <b>Premium faollashtirildi!</b>\n"
                    f"Sizga <b>+{amount}</b> ta limit qo'shildi!\n"
                    f"📊 /limit — tekshirish"
                )
            except Exception:
                pass
        else:
            await m.answer("❌ Foydalanuvchi topilmadi.")
    except (IndexError, ValueError):
        await m.answer("❗ Format: <code>/give 512345678 30</code>")


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
    except (IndexError, ValueError):
        await m.answer("❗ Format: <code>/reset 512345678</code>")


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

        total = FREE_LIMIT + info["premium_limit"]
        remaining = max(0, total - info["usage_count"])
        username = info["username"] if info["username"] != "Mavjud emas" else "yo'q"

        text = (
            f"👤 <b>Foydalanuvchi</b>\n\n"
            f"🆔 ID: <code>{info['user_id']}</code>\n"
            f"📛 Ism: {info['full_name']}\n"
            f"🔗 Username: @{username}\n"
            f"📅 Qo'shilgan: {info['joined_date']}\n\n"
            f"📊 <b>Limitlar:</b>\n"
            f"🎁 Bepul: {FREE_LIMIT}\n"
            f"💎 Premium: {info['premium_limit']}\n"
            f"📌 Jami: {total}\n"
            f"✅ Ishlatilgan: {info['usage_count']}\n"
            f"🔋 Qolgan: {remaining}"
        )
        await m.answer(text)
    except (IndexError, ValueError):
        await m.answer("❗ Format: <code>/userinfo 512345678</code>")


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
    "🔤 Ism Logo",
]


@dp.message(F.text.in_(CATEGORIES))
async def category_handler(m: Message):
    user_category[m.from_user.id] = m.text

    default_text = f"✍️ <b>{m.text}</b> uchun tavsif yozing:"

    await m.answer(PROMPT_EXAMPLES.get(m.text, default_text))


# ============================================================
# GENERATSIYA
# ============================================================

@dp.message()
async def generate_handler(m: Message):
    user_id = m.from_user.id

    # Kategoriya tanlangan emasmi?
    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang. /start bosing.")
        return

    user_text = m.text.strip()
    if not user_text:
        return

    # Limit tekshirish (admin cheksiz)
    if not is_admin(user_id) and not check_limit(user_id, FREE_LIMIT):
        await m.answer(
            "❌ <b>Limit tugadi!</b>\n\n"
            "💰 <b>Tariflar:</b>\n"
            "🎨 Start (30 ta) — 19,000 so'm\n"
            "🚀 Professional (100 ta) — 49,000 so'm\n"
            "👑 Biznes (cheksiz) — 99,000 so'm\n\n"
            "💳 Karta: <code>5614 6805 1876 1602</code>\n"
            "👤 Aminjonov Muhammadamin\n"
            "📱 Admin: @muhammad_amin07\n\n"
            f"🆔 Sizning ID: <code>{user_id}</code>"
        )
        return

    category = user_category.pop(user_id)

    # === ISM LOGO ===
    if category == "🔤 Ism Logo":
        msg = await m.answer(
            "⏳ Ism tahlil qilinmoqda va logo yaratilmoqda...\n"
            "Bu 15-30 soniya davom etishi mumkin."
        )
        f = None
        try:
            # 1. Ism tahlili
            info = await generate_name_logo_info(user_text)

            # 2. Logo yaratish
            f, err = await generate_image(info["prompt"], "🎨 Logo")

            # 3. Natijani yuborish
            caption = (
                f"🔤 <b>Ism:</b> {user_text}\n\n"
                f"📖 <b>Ma'nosi:</b>\n{info['meaning']}\n\n"
                f"💡 <b>Logo g'oyasi:</b>\n{info['idea']}\n\n"
                f"🧠 <b>AI Prompt:</b>\n<code>{info['prompt']}</code>"
            )

            if f and os.path.exists(f):
                await m.answer_photo(FSInputFile(f), caption=caption)
            else:
                await m.answer(
                    caption + f"\n\n❌ Logo rasm yaratishda xatolik: {err}"
                )

        except Exception as e:
            logger.error(f"Ism Logo xatosi: {e}")
            await m.answer(f"❌ Xatolik yuz berdi: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)

    # === BARCHA RASM KATEGORIYALARI ===
    else:
        msg = await m.answer(
            f"⏳ <b>{category}</b> uchun rasm yaratilmoqda...\n"
            "Bu 10-20 soniya davom etishi mumkin."
        )
        f = None
        try:
            f, err = await generate_image(user_text, category)

            if f and os.path.exists(f):
                await m.answer_photo(
                    FSInputFile(f),
                    caption=(
                        f"🎨 <b>{category}</b>\n"
                        f"📝 {user_text}"
                    )
                )
            else:
                await m.answer(f"❌ Rasm yaratishda xatolik: {err}")

        except Exception as e:
            logger.error(f"Rasm xatosi: {e}")
            await m.answer(f"❌ Xatolik: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)


# ============================================================
# WEB SERVER (Render / UptimeRobot uchun)
# ============================================================

async def run_web_server():
    app = web.Application()

    async def health(request):
        return web.Response(text="OK", status=200)

    async def status(request):
        users_count, total_usage = get_stats()
        return web.json_response({
            "status": "online",
            "users": users_count,
            "generations": total_usage
        })

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/status", status)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server: http://0.0.0.0:{port}")


# ============================================================
# MAIN
# ============================================================

async def main():
    init_db()

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return

    # Eski webhook va pending update larni tozalash
    await bot.delete_webhook(drop_pending_updates=True)

    # Bot komandalarini sozlash
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Boshlash"),
        BotCommand(command="limit", description="📊 Limitni ko'rish"),
        BotCommand(command="help", description="ℹ️ Yordam"),
    ])

    logger.info("=" * 40)
    logger.info("🤖 Bot ishga tushdi!")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info(f"🎁 Bepul limit: {FREE_LIMIT}")
    logger.info("=" * 40)

    # Web server va polling
    await asyncio.gather(
        run_web_server(),
        dp.start_polling(bot, skip_updates=True)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")
    except Exception as e:
        logger.error(f"Xatolik: {e}")
