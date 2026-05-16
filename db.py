import sqlite3
import os
from datetime import datetime

# config.py dan DB_NAME import qilish xavfsizroq
try:
    from config import DB_NAME
except ImportError:
    DB_NAME = "users.db"

def init_db():
    # Baza faylini yaratish va jadvalni shakllantirish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Baza jadvalining asosiy strukturasini yaratish (IF NOT EXISTS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,  # Bu ustun bo'lishi shart
            usage_count INTEGER DEFAULT 0,
            joined_date TEXT
        )
    ''')

    # --- RENDER BAZASINI AVTOMAT YANGILASH (MIGRATSIYA) ---
    try:
        # Jadval ustunlari ro'yxatini olamiz
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # O'zgarishlarni kiritish uchun tranzaksiyani boshlaymiz
        conn.commit()
        
        # Agar 'full_name' ustuni jadvalda mavjud bo'lmasa, uni qo'shamiz
        if 'full_name' not in columns:
            print("INFO: 'full_name' ustuni topilmadi, bazaga qo'shish boshlanmoqda...")
            cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            print("✅ INFO: 'full_name' ustuni bazaga muvaffaqiyatli qo'shildi.")
        
        # Boshqa ustunlarni ham tekshirish (username, usage_count va joined_date har doim bo'lishi kerak)
        if 'username' not in columns:
            print("INFO: 'username' ustuni topilmadi, qo'shilmoqda...")
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            print("✅ INFO: 'username' ustuni qo'shildi.")

        if 'usage_count' not in columns:
            print("INFO: 'usage_count' ustuni topilmadi, qo'shilmoqda...")
            cursor.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER DEFAULT 0")
            print("✅ INFO: 'usage_count' ustuni qo'shildi.")

        if 'joined_date' not in columns:
            print("INFO: 'joined_date' ustuni topilmadi, qo'shilmoqda...")
            cursor.execute("ALTER TABLE users ADD COLUMN joined_date TEXT")
            print("✅ INFO: 'joined_date' ustuni qo'shildi.")

    except sqlite3.OperationalError as e:
        # Baza qulflangan yoki boshqa muammo bo'lsa
        print(f"⚠️ DIQQAT: Baza ustunlarini tekshirishda xatolik: {e}")
        # Agar baza qulflangan bo'lsa, davom etamiz, chunki bazada ma'lumot bo'lishi mumkin
    except Exception as e:
        print(f"❌ XATO: Kutilmagan xatolik yuz berdi: {e}")

    # Yakuniy saqlash va yopish
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
        
        # Xatolikni tutib olish uchun try-except ishlatamiz
        try:
            cursor.execute(
                "INSERT INTO users (user_id, username, full_name, usage_count, joined_date) VALUES (?, ?, ?, ?, ?)",
                (user_id, safe_username, safe_fullname, 0, now)
            )
            conn.commit()
            print(f"✅ Foydalanuvchi qo'shildi: {user_id}")
        except sqlite3.OperationalError as e:
            print(f"❌ XATO: Foydalanuvchini qo'shishda xatolik yuz berdi. Baza yangilanmagan ko'rinadi: {e}")
        except Exception as e:
            print(f"❌ XATO: Kutilmagan xatolik yuz berdi: {e}")
            
    conn.close()

def check_limit(user_id, free_limit):
    # Foydalanuvchining limitini tekshirish va bittaga oshirish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
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
    except sqlite3.OperationalError as e:
        print(f"❌ XATO: Limitni tekshirishda xatolik (baza muammosi): {e}")
        conn.close()
        return False

# --- ADMIN PANEL UCHUN QO'SHIMCHA FUNKSIYALAR ---

def get_stats():
    # Jami foydalanuvchilar va jami ishlatilgan limitlarni hisoblash
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(user_id), SUM(usage_count) FROM users")
        result = cursor.fetchone()
        conn.close()
        # Agar baza bo'sh bo'lsa None qaytmasligi uchun 0 yozamiz
        return result[0] or 0, result[1] or 0
    except Exception as e:
        print(f"❌ XATO: Statistikani olishda xatolik: {e}")
        conn.close()
        return 0, 0

def get_all_users():
    # Xabar tarqatish uchun barcha ID larni olish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        # Faqat ID lardan iborat toza ro'yxat qaytarish
        return [user[0] for user in users]
    except Exception as e:
        print(f"❌ XATO: Foydalanuvchilarni olishda xatolik: {e}")
        conn.close()
        return []

def add_premium_limit(user_id, amount):
    # Foydalanuvchiga admin tomonidan limit qo'shish
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
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
    except sqlite3.OperationalError as e:
        print(f"❌ XATO: Premium limit berishda xatolik: {e}")
        conn.close()
        return False
