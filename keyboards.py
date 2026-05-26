from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    keyboard = [
        [
            KeyboardButton(text="🎨 Logo"),
            KeyboardButton(text="🖼 Realistik"),
        ],
        [
            KeyboardButton(text="📱 Avatar"),
            KeyboardButton(text="🏠 Interyer"),
        ],
        [
            KeyboardButton(text="🌄 Landscape"),
            KeyboardButton(text="🖥 UI/UX Web Dizayn"),
        ],
        [
            KeyboardButton(text="🏢 3D Arxitektura"),
            KeyboardButton(text="💎 Brending"),
        ],
        [
            KeyboardButton(text="🎮 Konsept Art"),
            KeyboardButton(text="🏢 Reklama Banneri"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
