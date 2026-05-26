import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
else:
    import sqlite3
    try:
        from config import DB_NAME
    except ImportError:
        DB_NAME = "users.db"


def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    return sqlite3.connect(DB_NAME, timeout=30)


def execute_query(query, params=None, fetch=False, fetchone=False):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        if USE_POSTGRES:
            query = query.replace("?", "%s")

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        result = None
        if fetchone:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()

        conn.commit()
        return result
    except Exception as e:
        print(f"❌ DB xatosi: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        cursor.close()
        conn.close()


def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    try:
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    usage_count INTEGER DEFAULT 0,
                    premium_limit INTEGER DEFAULT 0,
                    joined_date TEXT
                )
            """)
        else:
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
    except Exception as e:
        print(f"❌ init_db xatosi: {e}")
    finally:
        cursor.close()
        conn.close()

    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
    print(f"✅ Baza init tugadi ({db_type})")


def add_user(user_id, username, full_name):
    safe_username = username if username else "Mavjud emas"
    safe_fullname = full_name if full_name else "Foydalanuvchi"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = execute_query(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,), fetchone=True
    )

    if result:
        execute_query(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (safe_username, safe_fullname, user_id)
        )
        return False

    execute_query(
        """INSERT INTO users (user_id, username, full_name, usage_count, premium_limit, joined_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, safe_username, safe_fullname, 0, 0, now)
    )
    return True


def check_limit(user_id, free_limit):
    result = execute_query(
        "SELECT usage_count, COALESCE(premium_limit, 0) FROM users WHERE user_id = ?",
        (user_id,), fetchone=True
    )
    if not result:
        return False

    usage_count, premium_limit = result
    total_limit = int(free_limit) + int(premium_limit)

    if usage_count < total_limit:
        execute_query(
            "UPDATE users SET usage_count = usage_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        return True
    return False


def add_premium_limit(user_id, amount):
    if amount <= 0:
        return False
    result = execute_query(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,), fetchone=True
    )
    if not result:
        return False
    execute_query(
        "UPDATE users SET premium_limit = COALESCE(premium_limit, 0) + ? WHERE user_id = ?",
        (amount, user_id)
    )
    return True


def get_limit_info(user_id, free_limit):
    result = execute_query(
        "SELECT usage_count, COALESCE(premium_limit, 0) FROM users WHERE user_id = ?",
        (user_id,), fetchone=True
    )
    if not result:
        return None

    usage_count, premium_limit = result
    total_limit = int(free_limit) + int(premium_limit)
    remaining = max(0, total_limit - usage_count)

    return {
        "usage_count": usage_count,
        "premium_limit": premium_limit,
        "total_limit": total_limit,
        "remaining": remaining
    }


def reset_user_usage(user_id):
    result = execute_query(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,), fetchone=True
    )
    if not result:
        return False
    execute_query(
        "UPDATE users SET usage_count = 0 WHERE user_id = ?",
        (user_id,)
    )
    return True


def get_stats():
    result = execute_query(
        "SELECT COUNT(user_id), COALESCE(SUM(usage_count), 0) FROM users",
        fetchone=True
    )
    if result:
        return result[0] or 0, result[1] or 0
    return 0, 0


def get_all_users():
    result = execute_query(
        "SELECT user_id FROM users", fetch=True
    )
    if result:
        return [row[0] for row in result]
    return []


def get_user_info(user_id):
    result = execute_query(
        """SELECT user_id, username, full_name, usage_count,
                  COALESCE(premium_limit, 0), joined_date
           FROM users WHERE user_id = ?""",
        (user_id,), fetchone=True
    )
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


def get_recent_users(limit=20):
    result = execute_query(
        """SELECT user_id, username, full_name, usage_count,
                  COALESCE(premium_limit, 0), joined_date
           FROM users ORDER BY joined_date DESC LIMIT ?""",
        (limit,), fetch=True
    )
    if not result:
        return []
    users = []
    for row in result:
        users.append({
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "usage_count": row[3],
            "premium_limit": row[4],
            "joined_date": row[5]
        })
    return users
