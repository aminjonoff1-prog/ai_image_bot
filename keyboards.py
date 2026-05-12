from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Logo"), KeyboardButton(text="🖼 Realistik")],
            [KeyboardButton(text="📱 Avatar"), KeyboardButton(text="🏠 Interyer")],
            [KeyboardButton(text="🌄 Landscape"), KeyboardButton(text="📊 Prezentatsiya")]
        ],
        resize_keyboard=True
    )
