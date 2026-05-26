import os
import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi! Render Environment ga qo'ying.")

FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# GEMINI_API_KEY faqat kerak bo'lsa:
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- DB ---
from db import (
    check_limit, init_db, add_user, get_stats,
    get_all_users, add_premium_limit, get_limit_info,
    reset_user_usage, get_user_info,
)

# --- MODULLAR ---
from keyboards import main_menu, prompt_categories_menu
from image_gen import generate_image
from name_logo import generate_name_logo_info

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- BOT ---
bot = Bot(token=BOT_TOKEN.strip(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
user_category = {}


# ============================================================
# YORDAMCHI
# ============================================================

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

async def safe_delete(msg):
    try: await msg.delete()
    except: pass

async def safe_remove_file(f):
    try:
        if f and os.path.exists(f): os.remove(f)
    except: pass


# ============================================================
# PROMPT NAMUNALAR (ALOHIDA BO'LIM)
# ============================================================

PROMPT_SAMPLES = {
    "📝 Logo Promptlar": (
        "🎨 <b>Logo — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern minimalist logo for [name], black and gold, luxury style</code>\n\n"
        "2️⃣ <code>Clean tech startup logo for [name], blue and white, vector</code>\n\n"
        "3️⃣ <code>Elegant fashion logo for [name], premium typography</code>\n\n"
        "4️⃣ <code>Coffee shop logo for [name], warm colors, vintage</code>\n\n"
        "5️⃣ <code>Real estate logo for [name], gold and navy, luxury</code>\n\n"
        "💡 <i>[name] o'rniga o'z nomingizni yozing</i>"
    ),
    "📝 Realistik Promptlar": (
        "🖼 <b>Realistik — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Realistic sunset over mountains, golden hour, 8k</code>\n\n"
        "2️⃣ <code>Photorealistic portrait of old man, natural light</code>\n\n"
        "3️⃣ <code>Realistic red Ferrari on desert road, motion blur</code>\n\n"
        "4️⃣ <code>Ultra realistic Uzbek food on wooden table</code>\n\n"
        "5️⃣ <code>Realistic aerial view of Samarkand, cinematic</code>\n\n"
        "💡 <i>O'zbekcha ham yozishingiz mumkin!</i>"
    ),
    "📝 Avatar Promptlar": (
        "📱 <b>Avatar — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Professional business avatar, man in suit, studio light</code>\n\n"
        "2️⃣ <code>Anime style avatar, girl with blue hair, vibrant</code>\n\n"
        "3️⃣ <code>3D cartoon avatar, smiling boy, Pixar style</code>\n\n"
        "4️⃣ <code>Gaming avatar, cyberpunk warrior, neon lights</code>\n\n"
        "5️⃣ <code>Minimalist flat avatar, pastel colors, social media</code>"
    ),
    "📝 Interyer Promptlar": (
        "🏠 <b>Interyer — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern living room, minimalist, white and wood</code>\n\n"
        "2️⃣ <code>Luxury bedroom, dark theme, gold accents</code>\n\n"
        "3️⃣ <code>Traditional Uzbek guest room, colorful patterns</code>\n\n"
        "4️⃣ <code>Modern kitchen, marble countertop, Scandinavian</code>\n\n"
        "5️⃣ <code>Cozy cafe interior, industrial style, brick walls</code>"
    ),
    "📝 Landscape Promptlar": (
        "🌄 <b>Landscape — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Mountain landscape, green valley, river, sunrise</code>\n\n"
        "2️⃣ <code>Desert at sunset, sand dunes, golden light</code>\n\n"
        "3️⃣ <code>Tropical island, crystal clear water, palm trees</code>\n\n"
        "4️⃣ <code>Winter forest, snow covered trees, northern lights</code>\n\n"
        "5️⃣ <code>Uzbekistan countryside, cotton fields, blue sky</code>"
    ),
    "📝 UI/UX Promptlar": (
        "🖥 <b>UI/UX — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern SaaS landing page, dark theme, clean</code>\n\n"
        "2️⃣ <code>E-commerce website, fashion store, minimalist</code>\n\n"
        "3️⃣ <code>Mobile app UI, food delivery, colorful</code>\n\n"
        "4️⃣ <code>Dashboard UI, analytics, dark mode, charts</code>\n\n"
        "5️⃣ <code>Portfolio website, creative agency, modern layout</code>"
    ),
    "📝 3D Promptlar": (
        "🏢 <b>3D Arxitektura — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Modern 3D house, minimalist, white concrete, glass</code>\n\n"
        "2️⃣ <code>Luxury villa 3D render, pool, garden, sunset</code>\n\n"
        "3️⃣ <code>Office building, glass facade, urban environment</code>\n\n"
        "4️⃣ <code>Uzbek mosque 3D render, blue tiles, ornaments</code>\n\n"
        "5️⃣ <code>Futuristic skyscraper, eco friendly, green building</code>"
    ),
    "📝 Brending Promptlar": (
        "💎 <b>Brending — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Brand identity for [name], business cards, elegant</code>\n\n"
        "2️⃣ <code>Coffee brand mockup, packaging, cup design</code>\n\n"
        "3️⃣ <code>Fashion brand stationery, black and gold, luxury</code>\n\n"
        "4️⃣ <code>Tech startup brand kit, blue gradient, modern</code>\n\n"
        "5️⃣ <code>Restaurant brand identity, menu, logo, vintage</code>"
    ),
    "📝 Konsept Promptlar": (
        "🎮 <b>Konsept Art — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Fantasy castle, epic lighting, dragons in sky</code>\n\n"
        "2️⃣ <code>Cyberpunk city, neon lights, rain, futuristic</code>\n\n"
        "3️⃣ <code>Sci-fi space station, astronaut, detailed</code>\n\n"
        "4️⃣ <code>Silk Road scene, Samarkand, caravan, historical</code>\n\n"
        "5️⃣ <code>Underwater fantasy, coral reef, sea creatures</code>"
    ),
    "📝 Banner Promptlar": (
        "🏢 <b>Reklama Banneri — Prompt namunalari:</b>\n\n"
        "1️⃣ <code>Sale banner background, vibrant, abstract shapes</code>\n\n"
        "2️⃣ <code>Real estate banner, buildings, blue sky, clean</code>\n\n"
        "3️⃣ <code>Food delivery banner, fresh fruits, bright</code>\n\n"
        "4️⃣ <code>Tech product launch, dark gradient, spotlight</code>\n\n"
        "5️⃣ <code>Education banner, books, students, friendly</code>\n\n"
        "❗ <i>Matn yozmang, faqat fon va rasmlarni yozing</i>"
    ),
}


# ============================================================
# FOYDALANUVCHI HANDLERLARI
# ============================================================

@dp.message(Command("start"))
async def start_command(m: Message):
    is_new = add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)

    text = (
        f"👋 Salom, <b>{m.from_user.full_name}</b>!\n\n"
        f"🤖 Men AI rasm va dizayn generator botman.\n\n"
        f"📋 <b>Imkoniyatlarim:</b>\n"
        f"🎨 Logo — professional logotip\n"
        f"🖼 Realistik — haqiqiy foto\n"
        f"📱 Avatar — profil rasm\n"
        f"🏠 Interyer — uy dizayn\n"
        f"🌄 Landscape — tabiat\n"
        f"🖥 UI/UX — web dizayn\n"
        f"🏢 3D Arxitektura — bino loyiha\n"
        f"💎 Brending — brand dizayn\n"
        f"🎮 Konsept Art — fantastik rasm\n"
        f"🏢 Reklama Banneri — reklama foni\n"
        f"🔤 Ism Logo — ismga mos logo\n"
        f"📝 Prompt Namunalar — tayyor promptlar\n\n"
        f"⚡ Pastdagi menyudan tanlang!\n"
        f"📊 /limit — qolgan limit"
    )
    await m.answer(text, reply_markup=main_menu())

    # Admin ga yangi foydalanuvchi haqida xabar (Xavfsiz va to'g'rilangan)
    if ADMIN_ID:
        try:
            username = f"@{m.from_user.username}" if m.from_user.username else "yo'q"
            admin_text = (
                f"🆕 <b>Yangi yoki faol foydalanuvchi!</b>\n\n"
                f"👤 Ism: <b>{m.from_user.full_name}</b>\n"
                f"🔗 Username: {username}\n"
                f"🆔 ID: <code>{m.from_user.id}</code>\n"
                f"📊 is_new holati: {is_new}\n"
            )
            users_count, _ = get_stats()
            admin_text += f"\n📊 Jami foydalanuvchilar: <b>{users_count}</b>"
            await m.bot.send_message(chat_id=ADMIN_ID, text=admin_text)
        except Exception as e:
            logger.error(f"Adminga xabar yuborishda xatolik: {e}")

@dp.message(Command("users"))
async def users_list_command(m: Message):
    if not is_admin(m.from_user.id):
        return

    try:
        from db import get_recent_users
        users = get_recent_users(20)

        if not users:
            await m.answer("❌ Foydalanuvchilar topilmadi.")
            return

        text = "👥 <b>Oxirgi 20 ta foydalanuvchi:</b>\n\n"

        for i, user in enumerate(users, 1):
            username = f"@{user['username']}" if user['username'] != "Mavjud emas" else "—"
            text += (
                f"{i}. <b>{user['full_name']}</b>\n"
                f"    🆔 <code>{user['user_id']}</code> | {username}\n"
                f"    📊 Ishlatgan: {user['usage_count']} | 💎 Premium: {user['premium_limit']}\n"
                f"    📅 {user['joined_date']}\n\n"
            )

        users_count, total_usage = get_stats()
        text += f"📊 <b>Jami:</b> {users_count} ta foydalanuvchi, {total_usage} ta generatsiya"

        await m.answer(text)

    except Exception as e:
        await m.answer(f"Xato: {e}")
        
@dp.message(Command("limit"))
async def limit_command(m: Message):
    add_user(m.from_user.id, m.from_user.username, m.from_user.full_name)
    if is_admin(m.from_user.id):
        await m.answer("👑 Siz adminsiz! Limit yo'q.")
        return
    info = get_limit_info(m.from_user.id, FREE_LIMIT)
    if not info:
        await m.answer("❌ /start bosing.")
        return
    text = (
        f"📊 <b>Limitingiz</b>\n\n"
        f"🎁 Bepul: <b>{FREE_LIMIT}</b>\n"
        f"💎 Premium: <b>{info['premium_limit']}</b>\n"
        f"📌 Jami: <b>{info['total_limit']}</b>\n"
        f"✅ Ishlatilgan: <b>{info['usage_count']}</b>\n"
        f"🔋 Qolgan: <b>{info['remaining']}</b>\n\n"
        f"🆔 ID: <code>{m.from_user.id}</code>"
    )
    if info["remaining"] == 0:
        text += (
            "\n\n❗ <b>Limit tugagan!</b>\n"
            "💳 Karta: <code>5614 6805 1876 1602</code>\n"
            "📱 Admin: @muhammad_amin07"
        )
    await m.answer(text)


@dp.message(Command("help"))
async def help_command(m: Message):
    await m.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "/start — boshlash\n"
        "/limit — limit\n"
        "/help — yordam\n\n"
        "❓ @muhammad_amin07"
    )


# ============================================================
# ADMIN HANDLERLARI
# ============================================================

@dp.message(Command("admin"))
async def admin_panel(m: Message):
    if not is_admin(m.from_user.id): return
    users_count, total_usage = get_stats()
    await m.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b>\n"
        f"🎨 Generatsiyalar: <b>{total_usage}</b>\n\n"
        f"<code>/send [matn]</code>\n"
        f"<code>/give [id] [son]</code>\n"
        f"<code>/reset [id]</code>\n"
        f"<code>/userinfo [id]</code>"
    )


@dp.message(Command("send"))
async def broadcast_command(m: Message):
    if not is_admin(m.from_user.id): return
    text = m.text.replace("/send", "", 1).strip()
    if not text:
        await m.answer("❗ Matn kiriting.")
        return
    users = get_all_users()
    msg = await m.answer(f"⏳ {len(users)} foydalanuvchiga yuborilmoqda...")
    s, f = 0, 0
    for uid in users:
        try:
            await m.bot.send_message(chat_id=uid, text=text); s += 1
            await asyncio.sleep(0.05)
        except: f += 1
    await msg.edit_text(f"✅ Yuborildi: <b>{s}</b>\n❌ Xato: <b>{f}</b>")


@dp.message(Command("give"))
async def give_limit_command(m: Message):
    if not is_admin(m.from_user.id): return
    try:
        parts = m.text.split()
        if len(parts) < 3:
            await m.answer("❗ <code>/give [id] [son]</code>"); return
        tid, amt = int(parts[1]), int(parts[2])
        if add_premium_limit(tid, amt):
            await m.answer(f"✅ <code>{tid}</code> ga +{amt} limit.")
            try: await m.bot.send_message(chat_id=tid, text=f"🎉 +{amt} limit qo'shildi!")
            except: pass
        else: await m.answer("❌ Topilmadi.")
    except: await m.answer("❗ <code>/give 512345678 30</code>")


@dp.message(Command("reset"))
async def reset_command(m: Message):
    if not is_admin(m.from_user.id): return
    try:
        parts = m.text.split()
        if len(parts) < 2:
            await m.answer("❗ <code>/reset [id]</code>"); return
        if reset_user_usage(int(parts[1])):
            await m.answer(f"✅ Tiklandi.")
        else: await m.answer("❌ Topilmadi.")
    except: await m.answer("❗ <code>/reset 512345678</code>")


@dp.message(Command("userinfo"))
async def userinfo_command(m: Message):
    if not is_admin(m.from_user.id): return
    try:
        parts = m.text.split()
        if len(parts) < 2:
            await m.answer("❗ <code>/userinfo [id]</code>"); return
        info = get_user_info(int(parts[1]))
        if not info:
            await m.answer("❌ Topilmadi."); return
        total = FREE_LIMIT + info["premium_limit"]
        rem = max(0, total - info["usage_count"])
        await m.answer(
            f"👤 ID: <code>{info['user_id']}</code>\n"
            f"📛 {info['full_name']}\n"
            f"🔗 @{info['username']}\n"
            f"📅 {info['joined_date']}\n"
            f"📊 Ishlatilgan: {info['usage_count']}\n"
            f"💎 Premium: {info['premium_limit']}\n"
            f"🔋 Qolgan: {rem}"
        )
    except: await m.answer("❗ <code>/userinfo 512345678</code>")


# ============================================================
# PROMPT NAMUNALAR BO'LIMI (ALOHIDA)
# ============================================================

@dp.message(F.text == "📝 Prompt Namunalar")
async def prompt_menu_handler(m: Message):
    await m.answer(
        "📝 <b>Prompt namunalar bo'limi</b>\n\n"
        "Quyidagi kategoriyalardan birini tanlang.\n"
        "Tayyor promptlarni copy qilib, o'zingizga moslab ishlatishingiz mumkin.",
        reply_markup=prompt_categories_menu()
    )


PROMPT_BUTTONS = list(PROMPT_SAMPLES.keys())

@dp.message(F.text.in_(PROMPT_BUTTONS))
async def show_prompt_samples(m: Message):
    text = PROMPT_SAMPLES.get(m.text, "Topilmadi.")
    await m.answer(text)


@dp.message(F.text == "🔙 Orqaga")
async def back_to_main(m: Message):
    await m.answer("🏠 Asosiy menyu", reply_markup=main_menu())


# ============================================================
# KATEGORIYALAR
# ============================================================

CATEGORIES = [
    "🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer",
    "🌄 Landscape", "🖥 UI/UX Web Dizayn", "🏢 3D Arxitektura",
    "💎 Brending", "🎮 Konsept Art", "🏢 Reklama Banneri", "🔤 Ism Logo",
]

@dp.message(F.text.in_(CATEGORIES))
async def category_handler(m: Message):
    user_category[m.from_user.id] = m.text

    if m.text == "🔤 Ism Logo":
        await m.answer(
            "🔤 <b>Ism Logo</b>\n\n"
            "Ism yoki brand nomi yozing.\n\n"
            "Bot sizga:\n"
            "📖 Ism ma'nosini\n"
            "💡 Logo g'oyasini\n"
            "🎨 Tayyor logoni\n"
            "yaratib beradi.\n\n"
            "✍️ Ismni yozing:"
        )
    else:
        await m.answer(
            f"✍️ <b>{m.text}</b> uchun tavsif yozing.\n\n"
            f"💡 O'zbekcha yoki inglizcha yozishingiz mumkin."
        )


# ============================================================
# GENERATSIYA
# ============================================================

@dp.message()
async def generate_handler(m: Message):
    user_id = m.from_user.id

    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang. /start bosing.")
        return

    user_text = m.text.strip()
    if not user_text:
        return

    # Limit
    if not is_admin(user_id) and not check_limit(user_id, FREE_LIMIT):
        await m.answer(
            "❌ <b>Limit tugadi!</b>\n\n"
            "💰 <b>Tariflar:</b>\n"
            "🎨 Start (30) — 19,000 so'm\n"
            "🚀 Pro (100) — 49,000 so'm\n"
            "👑 Biznes (cheksiz) — 99,000 so'm\n\n"
            "💳 <code>5614 6805 1876 1602</code>\n"
            "📱 @muhammad_amin07\n"
            f"🆔 <code>{user_id}</code>"
        )
        return

    category = user_category.pop(user_id)

    # === ISM LOGO ===
    if category == "🔤 Ism Logo":
        msg = await m.answer("⏳ Ism tahlil qilinmoqda va logo yaratilmoqda...")
        f = None
        try:
            info = await generate_name_logo_info(user_text)
            f, err = await generate_image(info["prompt"], "🎨 Logo")

            caption = (
                f"🔤 <b>Ism:</b> {user_text}\n\n"
                f"📖 <b>Ma'nosi:</b>\n{info['meaning']}\n\n"
                f"💡 <b>Logo g'oyasi:</b>\n{info['idea']}\n\n"
                f"🧠 <b>Prompt:</b>\n<code>{info['prompt']}</code>"
            )

            if f and os.path.exists(f):
                await m.answer_photo(FSInputFile(f), caption=caption)
            else:
                await m.answer(caption + f"\n\n❌ Logo yaratishda xato: {err}")
        except Exception as e:
            logger.error(f"Ism Logo generatsiyasida xatolik: {e}", exc_info=True)
            await m.answer(f"❌ Xato: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)

    # === RASM ===
    else:
        msg = await m.answer(
            f"⏳ <b>{category}</b> uchun rasm yaratilmoqda...\n"
            "O'zbekcha tarjima qilinmoqda va rasm chizilmoqda..."
        )
        f = None
        try:
            f, err = await generate_image(user_text, category)
            if f and os.path.exists(f):
                await m.answer_photo(
                    FSInputFile(f),
                    caption=f"🎨 <b>{category}</b>\n📝 {user_text}"
                )
            else:
                await m.answer(f"❌ Xatolik: {err}")
        except Exception as e:
            logger.error(f"Rasm generatsiyasida xatolik ({category}): {e}", exc_info=True)
            await m.answer(f"❌ Xato: {e}")
        finally:
            await safe_remove_file(f)
            await safe_delete(msg)


# ============================================================
# WEB SERVER
# ============================================================

async def run_web_server():
    app = web.Application()
    async def hp(r): return web.Response(text="OK")
    app.router.add_get("/", hp)
    app.router.add_get("/health", hp)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()


# ============================================================
# MAIN
# ============================================================

async def main():
    init_db()
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN yo'q!"); return

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Boshlash"),
        BotCommand(command="limit", description="📊 Limit"),
        BotCommand(command="help", description="ℹ️ Yordam"),
    ])

    logger.info("🤖 Bot ishga tushdi!")
    await asyncio.gather(run_web_server(), dp.start_polling(bot, skip_updates=True))


if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("Bot to'xtatildi.")
