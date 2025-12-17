import sqlite3
import json
from config import DB_PATH



def init_db():
    """Инициализация базы данных и создание таблицы tickets."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                category TEXT NOT NULL,  -- 'tech' или 'sales'
                message TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
        
        conn.commit()



def save_ticket(user_id, username, full_name, category, message):
    """
    Сохраняет новое обращение в БД.
    Возвращает ID созданной записи.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tickets 
            (user_id, username, full_name, category, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, username, full_name, category, message)
        )
        ticket_id = cur.lastrowid
        conn.commit()
    return ticket_id



def get_open_tickets(category=None):
    """
    Возвращает список открытых обращений.
    Если указан category — фильтрует по категории ('tech'/'sales').
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        if category:
            cur.execute(
                """
                SELECT id, user_id, message
                FROM tickets
                WHERE status = 'open' AND category = ?
                """,
                (category,)
            )
        else:
            cur.execute(
                """
                SELECT id, user_id, message
                FROM tickets
                WHERE status = 'open'
                """
            )
        rows = cur.fetchall()
    return rows
