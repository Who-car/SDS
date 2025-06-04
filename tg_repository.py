import sqlite3
from config import TG_PATH

def init_db():
    conn = sqlite3.connect(TG_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            token TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_token(chat_id: int) -> str:
    conn = sqlite3.connect(TG_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT token FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def save_token(chat_id: int, token: str):
    conn = sqlite3.connect(TG_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (chat_id, token)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET token=excluded.token
        """,
        (chat_id, token),
    )
    conn.commit()
    conn.close()
