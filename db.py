import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
POSTGRES_SSLMODE = os.environ.get("POSTGRES_SSLMODE", "require").strip() or "require"

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
    except ImportError as e:
        raise RuntimeError(
            "psycopg2 topilmadi. requirements.txt ga psycopg2-binary qo'shing."
        ) from e
else:
    try:
        from config import DB_NAME
    except ImportError:
        DB_NAME = "users.db"


def _debug_log(msg: str):
    # Kerak bo'lsa o'chirish/yoqish uchun:
    # Render env ga DB_DEBUG=1 qo'ying
    if os.environ.get("DB_DEBUG", "").strip() in ("1", "true", "TRUE", "yes"):
        print("[DB_DEBUG]", msg)


def get_conn():
    if USE_POSTGRES:
        # DATABASE_URL odatda: postgresql://user:pass@host:port/db
        _debug_log("Connecting to PostgreSQL...")
        return psycopg2.connect(DATABASE_URL, sslmode=POSTGRES_SSLMODE)
    else:
        _debug_log("Connecting to SQLite...")
        return sqlite3.connect(DB_NAME, timeout=30)


def execute_query(query, params=None, fetch=False, fetchone=False):
    """
    PostgreSQL uchun querydagi '?' ni avtomatik '%s' ga aylantiradi.
    """
    conn = get_conn()
    cursor = conn.cursor()
    try:
        if USE_POSTGRES:
            query = query.replace("?", "%s")

        if params is None:
            cursor.execute(query)
        else:
            cursor.execute(query, params)

        result = None
        if fetchone:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()

        conn.commit()
        return result

    except Exception as e:
        conn.rollback()
        print(f"❌ DB xatosi: {e}")
        return None

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _sqlite_has_column(table: str, column: str) -> bool:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cursor.fetchall()]
        return column in cols
    finally:
        try:
            conn.close()
        except Exception:
            pass


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
            conn.commit()
            _debug_log("✅ PostgreSQL init complete")
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

            # eski bazada bo'lishi mumkin bo'lgan ustunlar migration
            if not _sqlite_has_column("users", "premium_limit"):
                cursor.execute("ALTER TABLE users ADD COLUMN premium_limit INTEGER DEFAULT 0")
            if not _sqlite_has_column("users", "full_name"):
                cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            if not _sqlite_has_column("users", "username"):
                cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            if not _sqlite_has_column("users", "usage_count"):
                cursor.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER DEFAULT 0")
            if not _sqlite_has_column("users", "joined_date"):
                cursor.execute("ALTER TABLE users ADD COLUMN joined_date TEXT")

            conn.commit()
            _debug_log("✅ SQLite init/migration complete")

    except Exception as e:
        print(f"❌ init_db xatosi: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    if USE_POSTGRES:
        try:
            host = urlparse(DATABASE_URL).hostname
        except Exception:
            host = "unknown"
        print(f"✅ Baza init tugadi (PostgreSQL) host={host}")
    else:
        print("✅ Baza init tugadi (SQLite)")


def add_user(user_id, username, full_name) -> bool:
    """Yangi foydalanuvchi bo'lsa True, bo'lmasa False qaytaradi."""
    safe_username = username if username else "Mavjud emas"
    safe_fullname = full_name if full_name else "Foydalanuvchi"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    exists = execute_query(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,),
        fetchone=True
    )

    if exists:
        execute_query(
            "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
            (safe_username, safe_fullname, user_id)
        )
        return False

    execute_query(
        """INSERT INTO users (user_id, username, full_name, usage_count, premium_limit, joined_date)
           VALUES (?, ?, ?, 0, 0, ?)""",
        (user_id, safe_username, safe_fullname, now)
    )
    return True


def check_limit(user_id, free_limit) -> bool:
    row = execute_query(
        "SELECT usage_count, COALESCE(premium_limit, 0) FROM users WHERE user_id = ?",
        (user_id,),
        fetchone=True
    )
    if not row:
        return False

    usage_count, premium_limit = row
    total_limit = int(free_limit) + int(premium_limit)

    if usage_count < total_limit:
        execute_query(
            "UPDATE users SET usage_count = usage_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        return True

    return False


def add_premium_limit(user_id, amount) -> bool:
    if amount <= 0:
        return False

    exists = execute_query(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,),
        fetchone=True
    )
    if not exists:
        return False

    execute_query(
        "UPDATE users SET premium_limit = COALESCE(premium_limit, 0) + ? WHERE user_id = ?",
        (amount, user_id)
    )
    return True


def get_limit_info(user_id, free_limit):
    row = execute_query(
        "SELECT usage_count, COALESCE(premium_limit, 0) FROM users WHERE user_id = ?",
        (user_id,),
        fetchone=True
    )
    if not row:
        return None

    usage_count, premium_limit = row
    total_limit = int(free_limit) + int(premium_limit)
    remaining = max(0, total_limit - usage_count)

    return {
        "usage_count": int(usage_count),
        "premium_limit": int(premium_limit),
        "total_limit": int(total_limit),
        "remaining": int(remaining),
    }


def reset_user_usage(user_id) -> bool:
    exists = execute_query(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,),
        fetchone=True
    )
    if not exists:
        return False

    execute_query(
        "UPDATE users SET usage_count = 0 WHERE user_id = ?",
        (user_id,)
    )
    return True


def get_stats():
    row = execute_query(
        "SELECT COUNT(user_id), COALESCE(SUM(usage_count), 0) FROM users",
        fetchone=True
    )
    if not row:
        return 0, 0
    return int(row[0] or 0), int(row[1] or 0)


def get_all_users():
    rows = execute_query(
        "SELECT user_id FROM users",
        fetch=True
    )
    if not rows:
        return []
    return [r[0] for r in rows]


def get_user_info(user_id):
    row = execute_query(
        """SELECT user_id, username, full_name, usage_count,
                  COALESCE(premium_limit, 0), joined_date
           FROM users WHERE user_id = ?""",
        (user_id,),
        fetchone=True
    )
    if not row:
        return None

    return {
        "user_id": row[0],
        "username": row[1],
        "full_name": row[2],
        "usage_count": int(row[3] or 0),
        "premium_limit": int(row[4] or 0),
        "joined_date": row[5],
    }


def get_recent_users(limit=20):
    rows = execute_query(
        """SELECT user_id, username, full_name, usage_count,
                  COALESCE(premium_limit, 0), joined_date
           FROM users
           ORDER BY joined_date DESC
           LIMIT ?""",
        (limit,),
        fetch=True
    )
    if not rows:
        return []

    out = []
    for r in rows:
        out.append({
            "user_id": r[0],
            "username": r[1],
            "full_name": r[2],
            "usage_count": int(r[3] or 0),
            "premium_limit": int(r[4] or 0),
            "joined_date": r[5],
        })
    return out
