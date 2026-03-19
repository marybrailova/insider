import sqlite3
from config import DB_PATH, START_CASH, now_seconds, make_room_code

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_column_if_missing(conn, table_name, column_name, column_sql):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    names = []
    for row in rows:
        names.append(row["name"])
    if column_name not in names:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            max_players INTEGER NOT NULL,
            host_user_id INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS room_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(room_id, user_id)
        )
        """
    )
    add_column_if_missing(conn, "rooms", "status", "TEXT NOT NULL DEFAULT 'waiting'")
    add_column_if_missing(conn, "rooms", "current_day", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "rooms", "turn_ends_at", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "rooms", "game_data", "TEXT NOT NULL DEFAULT '{}' ")
    add_column_if_missing(conn, "rooms", "join_code", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(conn, "rooms", "created_at", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "rooms", "room_type", "TEXT NOT NULL DEFAULT 'private'")
    add_column_if_missing(conn, "room_players", "cash", f"REAL NOT NULL DEFAULT {START_CASH}")
    add_column_if_missing(conn, "room_players", "risk", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "room_players", "holdings", "TEXT NOT NULL DEFAULT '{}'")
    add_column_if_missing(conn, "room_players", "day_orders", "TEXT NOT NULL DEFAULT '{}'")
    add_column_if_missing(conn, "room_players", "day_actions", "TEXT NOT NULL DEFAULT '{}'")
    add_column_if_missing(conn, "room_players", "insider_used", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "room_players", "insider_hints", "TEXT NOT NULL DEFAULT '{}'")
    add_column_if_missing(conn, "room_players", "finished_day", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "room_players", "events", "TEXT NOT NULL DEFAULT '[]'")
    conn.execute("UPDATE rooms SET created_at = ? WHERE created_at = 0", (now_seconds(),))
    conn.execute("UPDATE rooms SET game_data = '{}' WHERE game_data IS NULL OR game_data = ''")
    conn.execute("UPDATE room_players SET holdings = '{}' WHERE holdings IS NULL OR holdings = ''")
    conn.execute("UPDATE room_players SET day_orders = '{}' WHERE day_orders IS NULL OR day_orders = ''")
    conn.execute("UPDATE room_players SET day_actions = '{}' WHERE day_actions IS NULL OR day_actions = ''")
    conn.execute("UPDATE room_players SET insider_hints = '{}' WHERE insider_hints IS NULL OR insider_hints = ''")
    conn.execute("UPDATE room_players SET events = '[]' WHERE events IS NULL OR events = ''")
    empty_codes = conn.execute(
        "SELECT id FROM rooms WHERE join_code = '' AND room_type = 'private'"
    ).fetchall()
    for row in empty_codes:
        conn.execute(
            "UPDATE rooms SET join_code = ? WHERE id = ?",
            (make_room_code(), row["id"]),
        )
    conn.commit()
    conn.close()
