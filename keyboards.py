from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Logo"), KeyboardButton(text="🖼 Realistik")],
            [KeyboardButton(text="📱 Avatar"), KeyboardButton(text="🏠 Interyer")],
            [KeyboardButton(text="🌄 Landscape")]
        ],
        resize_keyboard=True
    )