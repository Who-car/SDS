import sqlite3
from datetime import datetime
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        INN TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL
    );
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS Tokens (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        thread_id TEXT
    );
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS Requests (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL,
        origin TEXT NOT NULL,
        request_time TEXT NOT NULL,
        status TEXT
    );
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS Responses (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        response TEXT NOT NULL
    );
    """
    )

    conn.commit()
    conn.close()


def add_new_user(fullname: str, INN: str, phone: str, password_hash: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Users (fullname, INN, phone, password_hash) VALUES (?, ?, ?, ?)",
            (fullname, INN, phone, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
    finally:
        conn.close()
    return user_id


def get_user_by_token_id(token: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM Tokens WHERE id = ?;",
        (token,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["user_id"]
    return None


def get_user_by_INN(INN: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password_hash FROM Users WHERE INN = ?;",
        (INN,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "password_hash": row["password_hash"]}
    return None


def get_token_by_user(user_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM Tokens WHERE user_id = ?;",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["id"]
    return None


def get_thread_by_user(user_id: int) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT thread_id FROM Tokens WHERE user_id = ? LIMIT 1;",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["thread_id"]
    return None


def update_thread_for_user(user_id: int, thread_id: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Tokens SET thread_id = ? WHERE user_id = ?;",
        (thread_id, user_id),
    )
    conn.commit()
    conn.close()


def add_token(user_id: int, token: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Tokens (id, user_id, thread_id) VALUES (?, ?, ?)",
        (token, user_id, None),
    )
    conn.commit()
    conn.close()


def add_request(request_id: str, user_id: int, token: str, origin: str) -> str:
    request_time = datetime.now().isoformat()
    status = "Новый"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Requests (id, user_id, token, origin, request_time, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (request_id, user_id, token, origin, request_time, status),
    )
    conn.commit()
    conn.close()
    return request_id


def add_response(request_id: str, user_id: int, response: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Responses (id, user_id, response) VALUES (?, ?, ?)",
        (request_id, user_id, response),
    )
    conn.commit()
    conn.close()
    return request_id
