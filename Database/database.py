import sqlite3
from pathlib import Path
from Core.config import START_CASH

DB_PATH = Path(__file__).resolve().parent / "app.db"


def get_db():
    # подключаемся к базе
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


# создаём таблицы базы
def init_db():
    conn = get_db()

    # таблица пользователей
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    # таблица комнат
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            max_players INTEGER NOT NULL,
            host_user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'waiting',
            current_day INTEGER DEFAULT 0,
            turn_ends_at INTEGER DEFAULT 0,
            game_data TEXT DEFAULT '{}',
            join_code TEXT DEFAULT '',
            created_at INTEGER DEFAULT 0,
            room_type TEXT DEFAULT 'private'
        )
    """)

    # таблица игроков в комнатах
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS room_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            cash REAL DEFAULT {START_CASH},
            risk INTEGER DEFAULT 0,
            holdings TEXT DEFAULT '{{}}',
            day_orders TEXT DEFAULT '{{}}',
            day_actions TEXT DEFAULT '{{}}',
            insider_used INTEGER DEFAULT 0,
            insider_hints TEXT DEFAULT '{{}}',
            finished_day INTEGER DEFAULT 0,
            events TEXT DEFAULT '[]',
            capital_history TEXT DEFAULT '[]',
            UNIQUE(room_id, user_id)
        )
    """)

    columns = conn.execute(
        "PRAGMA table_info(room_players)"
    ).fetchall()

    column_names = []

    for column in columns:
        column_names.append(column["name"])

    # добавляем историю капитала в старую базу
    if "capital_history" not in column_names:
        conn.execute(
            "ALTER TABLE room_players "
            "ADD COLUMN capital_history TEXT DEFAULT '[]'"
        )

    conn.commit()
    conn.close()
