import sqlite3
from datetime import datetime

DB_NAME = "users.db"

def init_db():
    # Baza faylini yaratish va jadvalni shakllantirish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            usage_count INTEGER DEFAULT 0,
            joined_date TEXT
        )
    ''')
    
    # --- RENDER XATOSINI TARTIBGA SOLISH ---
    # Agar eski bazada 'username' ustuni yo'q bo'lsa, uni kod o'zi avtomatik qo'shib qo'yadi
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'username' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        print("Baza yangilandi: 'username' ustuni qo'shildi.")
    # --------------------------------------

    conn.commit()
    conn.close()

def add_user(user_id, username, full_name):
    # Yangi foydalanuvchini bazaga qo'shish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Avval bu odam bazada bor-yo'qligini tekshiramiz
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Agar username yo'q bo'lsa, "Mavjud emas" deb yozamiz
        safe_username = username if username else "Mavjud emas"
        safe_fullname = full_name if full_name else "Foydalanuvchi"
        
        cursor.execute(
            "INSERT INTO users (user_id, username, full_name, usage_count, joined_date) VALUES (?, ?, ?, ?, ?)",
            (user_id, safe_username, safe_fullname, 0, now)
        )
        conn.commit()
    conn.close()

def check_limit(user_id, free_limit):
    # Foydalanuvchining limitini tekshirish va bittaga oshirish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT usage_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        count = result[0]
        if count < free_limit:
            # Agar limitdan o'tmagan bo'lsa, hisobni 1 taga oshiramiz va True qaytaramiz
            cursor.execute("UPDATE users SET usage_count = usage_count + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return True
        else:
            # Limit tugagan bo'lsa
            conn.close()
            return False
    else:
        # Baza xatosi yoki botni start bosmasdan ishlatmoqchi bo'lsa
        conn.close()
        return False

# --- ADMIN PANEL UCHUN QO'SHIMCHA FUNKSIYALAR ---

def get_stats():
    # Jami foydalanuvchilar va jami ishlatilgan limitlarni hisoblash
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(user_id), SUM(usage_count) FROM users")
    result = cursor.fetchone()
    conn.close()
    # Agar baza bo'sh bo'lsa None qaytmasligi uchun 0 yozamiz
    return result[0] or 0, result[1] or 0

def get_all_users():
    # Xabar tarqatish uchun barcha ID larni olish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    # Faqat ID lardan iborat toza ro'yxat qaytarish
    return [user[0] for user in users]

def add_premium_limit(user_id, amount):
    # Foydalanuvchiga admin tomonidan limit qo'shish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Avval foydalanuvchi bazada borligini tekshiramiz
    cursor.execute("SELECT usage_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        # Hozirgi ishlatgan hisobini kamaytiramiz (yoki limitini ko'paytiramiz)
        # Bizning tizimda usage_count < FREE_LIMIT ishlagani uchun, count ni minus qilsak limit ko'payadi
        cursor.execute("UPDATE users SET usage_count = usage_count - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False
