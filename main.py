import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command

from config import BOT_TOKEN, FREE_LIMIT
from db import check_limit
from keyboards import main_menu
from image_gen import generate_image

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

bot = Bot(
    token=BOT_TOKEN.strip(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

user_category = {}


@dp.message(Command("start"))
async def start(m: Message):
    await m.answer(
        "👋 Salom!\n\nKategoriya tanlang va tavsif yozing.",
        reply_markup=main_menu()
    )


@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(
        "📌 Qanday ishlaydi:\n\n"
        "1. Kategoriya tanlang\n"
        "2. Tavsif yozing\n"
        "3. Rasm tayyor bo‘ladi"
    )


@dp.message(F.text.in_(["🎨 Logo", "🖼 Realistik", "📱 Avatar", "🏠 Interyer", "🌄 Landscape"]))
async def category(m: Message):
    user_category[m.from_user.id] = m.text
    await m.answer("✍️ Endi tasvirni yozing")


@dp.message()
async def generate(m: Message):
    user_id = m.from_user.id

    if user_id not in user_category:
        await m.answer("❗ Avval kategoriya tanlang")
        return

    if not check_limit(user_id, FREE_LIMIT):
        await m.answer("❌ Bugungi limit tugadi (5 ta)")
        return

    msg = await m.answer("⏳ Rasm yaratilmoqda...")

    file, error = await generate_image(m.text, user_category[user_id])

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
