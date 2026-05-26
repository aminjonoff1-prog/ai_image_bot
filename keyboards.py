from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    # Tugmalarni qatorlarga ajratib chiqamiz
    kb = [
        [KeyboardButton(text="🎨 Logo"), KeyboardButton(text="🖼 Realistik")],
        [KeyboardButton(text="📱 Avatar"), KeyboardButton(text="🏠 Interyer")],
        [KeyboardButton(text="🌄 Landscape")],
        [KeyboardButton(text="🖥 UI/UX Web Dizayn"), KeyboardButton(text="🏢 3D Arxitektura")],
        [KeyboardButton(text="💎 Brending"), KeyboardButton(text="🎮 Konsept Art")],
        [KeyboardButton(text="🏢 Reklama Banneri"), KeyboardButton(text="📚 Kurs Ishi")]
    ]
    
    # resize_keyboard=True tugmalar ekranning yarmini egallab olmasligi uchun kerak
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
