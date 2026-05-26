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
        [
            KeyboardButton(text="🔤 Ism Logo"),
            KeyboardButton(text="📝 Prompt Namunalar"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def prompt_categories_menu():
    keyboard = [
        [
            KeyboardButton(text="📝 Logo Promptlar"),
            KeyboardButton(text="📝 Realistik Promptlar"),
        ],
        [
            KeyboardButton(text="📝 Avatar Promptlar"),
            KeyboardButton(text="📝 Interyer Promptlar"),
        ],
        [
            KeyboardButton(text="📝 Landscape Promptlar"),
            KeyboardButton(text="📝 UI/UX Promptlar"),
        ],
        [
            KeyboardButton(text="📝 3D Promptlar"),
            KeyboardButton(text="📝 Brending Promptlar"),
        ],
        [
            KeyboardButton(text="📝 Konsept Promptlar"),
            KeyboardButton(text="📝 Banner Promptlar"),
        ],
        [
            KeyboardButton(text="🔙 Orqaga"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
