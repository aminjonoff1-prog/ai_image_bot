import sqlite3
from datetime import datetime

try:
    from config import DB_NAME
except ImportError:
    DB_NAME = "users.db"


def get_conn():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            usage_count INTEGER DEFAULT 0,
            premium_limit INTEGER DEFAULT 0,
            joined_date TEXT
        )
    """)

    conn.commit()

    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if "username" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")

        if "full_name" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")

        if "usage_count" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER DEFAULT 0")

        if "premium_limit" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN premium_limit INTEGER DEFAULT 0")

        if "joined_date" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN joined_date TEXT")

        conn.commit()

        # Eski tizimda usage_count manfiy bo'lib qolgan bo'lsa,
        # uni premium_limitga o'tkazamiz
        cursor.execute("""
            UPDATE users
            SET premium_limit = COALESCE(premium_limit, 0) + ABS(usage_count),
                usage_count = 0
            WHERE usage_count < 0
        """)

        conn.commit()

    except Exception as e:
        print(f"❌ DB migratsiya xatosi: {e}")

    conn.close()
    print("✅ Baza init tugadi.")


def add_user(user_id, username, full_name):
    """Yangi foydalanuvchini qo'shadi. Yangi bo'lsa True qaytaradi."""
    conn = get_conn()
    cursor = conn.cursor()

    safe_username = username if username else "Mavjud emas"
    safe_fullname = full_name if full_name else "Foydalanuvchi"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result:
            # Eski user — ma'lumotlarni yangilash
            cursor.execute("""
                UPDATE users SET username = ?, full_name = ? WHERE user_id = ?
            """, (safe_username, safe_fullname, user_id))
            conn.commit()
            conn.close()
            return False  # Yangi emas

        # Yangi user
        cursor.execute("""
            INSERT INTO users (user_id, username, full_name, usage_count, premium_limit, joined_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, safe_username, safe_fullname, 0, 0, now))
        conn.commit()
        conn.close()
        return True  # Yangi user

    except Exception as e:
        print(f"❌ add_user xatosi: {e}")
        conn.close()
        return False


def check_limit(user_id, free_limit):
    """
    Limit tekshiradi.

    Umumiy limit = FREE_LIMIT + premium_limit

    Masalan:
    FREE_LIMIT = 5
    premium_limit = 30
    user jami 35 marta ishlata oladi.
    """

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT usage_count, COALESCE(premium_limit, 0)
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return False

        usage_count, premium_limit = result

        total_limit = int(free_limit) + int(premium_limit)

        if usage_count < total_limit:
            cursor.execute("""
                UPDATE users
                SET usage_count = usage_count + 1
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False

    except Exception as e:
        print(f"❌ Limit tekshirishda xatolik: {e}")
        conn.close()
        return False


def add_premium_limit(user_id, amount):
    """
    Admin foydalanuvchiga pullik limit qo'shadi.

    Misol:
    /give 123456789 30

    premium_limit = premium_limit + 30
    """

    if amount <= 0:
        return False

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return False

        cursor.execute("""
            UPDATE users
            SET premium_limit = COALESCE(premium_limit, 0) + ?
            WHERE user_id = ?
        """, (amount, user_id))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Premium limit qo'shishda xatolik: {e}")
        conn.close()
        return False


def get_stats():
    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                COUNT(user_id),
                COALESCE(SUM(usage_count), 0)
            FROM users
        """)

        result = cursor.fetchone()
        conn.close()

        return result[0] or 0, result[1] or 0

    except Exception as e:
        print(f"❌ Statistikani olishda xatolik: {e}")
        conn.close()
        return 0, 0


def get_all_users():
    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        return [user[0] for user in users]

    except Exception as e:
        print(f"❌ Foydalanuvchilarni olishda xatolik: {e}")
        conn.close()
        return []


def get_limit_info(user_id, free_limit):
    """
    Foydalanuvchining limit ma'lumotlarini qaytaradi.
    Bu funksiya majburiy emas, lekin /limit komandasi uchun foydali.
    """

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT usage_count, COALESCE(premium_limit, 0)
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return None

        usage_count, premium_limit = result
        total_limit = int(free_limit) + int(premium_limit)
        remaining = max(0, total_limit - usage_count)

        conn.close()

        return {
            "usage_count": usage_count,
            "premium_limit": premium_limit,
            "total_limit": total_limit,
            "remaining": remaining
        }

    except Exception as e:
        print(f"❌ Limit info olishda xatolik: {e}")
        conn.close()
        return None
def reset_user_usage(user_id):
    """Foydalanuvchining ishlatgan limitini 0 ga tushiradi"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        cursor.execute("UPDATE users SET usage_count = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Reset xatosi: {e}")
        conn.close()
        return False


def get_user_info(user_id):
    """Foydalanuvchi haqida to'liq ma'lumot"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT user_id, username, full_name, usage_count, 
                   COALESCE(premium_limit, 0), joined_date
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            "user_id": result[0],
            "username": result[1],
            "full_name": result[2],
            "usage_count": result[3],
            "premium_limit": result[4],
            "joined_date": result[5]
        }
        
    except Exception as e:
        print(f"❌ User info xatosi: {e}")
        conn.close()
        return None
