import sqlite3
from datetime import datetime

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    used_today INTEGER DEFAULT 0,
    last_date TEXT
)
""")
conn.commit()


def check_limit(user_id, limit):
    today = datetime.now().date().isoformat()

    cursor.execute("SELECT used_today, last_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            "INSERT INTO users (user_id, used_today, last_date) VALUES (?, ?, ?)",
            (user_id, 1, today)
        )
        conn.commit()
        return True

    used, last_date = row

    if last_date != today:
        cursor.execute(
            "UPDATE users SET used_today=1, last_date=? WHERE user_id=?",
            (today, user_id)
        )
        conn.commit()
        return True

    if used >= limit:
        return False

    cursor.execute(
        "UPDATE users SET used_today=used_today+1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()
    return True