import sqlite3
from pathlib import Path

# из файла config.py импортируем переменную START_CASH
# START_CASH — стартовый баланс игрока
# START_CASH = 2000

from config import START_CASH

DB_PATH = Path(__file__).resolve().parent / "app.db"


def get_db():

    # conn — переменная, в которой будет лежать подключение к базе
    # sqlite3.connect — открыть SQLite базу данных
    # DB_PATH — путь к файлу app.db
    # если app.db нет, SQLite может создать этот файл
    conn = sqlite3.connect(DB_PATH)

    # row_factory — настройка того, как SQLite будет отдавать строки
    # sqlite3.Row — специальный формат строки
    # с ним можно обращаться к данным по имени колонки
    # row["id"], row["username"]
    conn.row_factory = sqlite3.Row

    return conn


# init_db — функция инициализации базы данных
# она создаёт таблицы, если их ещё нет
def init_db():

    # вызываем get_db()
    # получаем подключение к базе
    # сохраняем его в переменную conn
    conn = get_db()

    # conn.execute — выполнить SQL-команду в базе данных
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            -- id — уникальный номер пользователя
            -- INTEGER — целое число
            -- PRIMARY KEY — главный уникальный ключ строки
            -- AUTOINCREMENT — SQLite сам выдаёт id 1, 2, 3
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- username — имя пользователя
            -- TEXT — текстовая строка
            -- NOT NULL — значение обязательно, пустым быть не может
            -- UNIQUE — имена пользователей не должны повторяться
            username TEXT NOT NULL UNIQUE,

            -- password_hash — хэш пароля
            -- TEXT — строка
            -- NOT NULL — обязательно должно быть значение
            password_hash TEXT NOT NULL
        )
    """)

    # создаём таблицу rooms
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS rooms (

            -- id — уникальный номер комнаты
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- title — название комнаты
            title TEXT NOT NULL,

            -- max_players — максимальное количество игроков
            -- INTEGER — целое число
            max_players INTEGER NOT NULL,

            -- host_user_id — id пользователя, который создал комнату
            host_user_id INTEGER NOT NULL,

            -- status — статус комнаты
            -- TEXT — строка
            -- DEFAULT 'waiting' — если статус не указали, будет waiting
            -- waiting — ждём игроков
            -- playing — игра идёт
            -- finished — игра закончилась
            status TEXT DEFAULT 'waiting',

            -- current_day — текущий игровой день
            -- DEFAULT 0 — до старта игры день равен 0
            current_day INTEGER DEFAULT 0,

            -- turn_ends_at — время окончания текущего хода
            -- хранится числом, обычно в секундах
            turn_ends_at INTEGER DEFAULT 0,

            -- game_data — основное состояние игры
            -- TEXT — строка
            -- внутри хранится JSON
            -- цены компаний, история, новости, планы
            game_data TEXT DEFAULT '{{}}',

            -- join_code — код приватной комнаты
            -- DEFAULT '' — по умолчанию пустая строка
            join_code TEXT DEFAULT '',

            -- created_at — время создания комнаты
            created_at INTEGER DEFAULT 0,

            -- room_type — тип комнаты
            -- private — приватная
            -- public — публичная
            room_type TEXT DEFAULT 'private'
        )
    """)

    # создаём таблицу room_players
    # она хранит не просто пользователей, а игроков внутри конкретных комнат
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS room_players (

            -- id — уникальный номер записи
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- room_id — id комнаты, в которой находится игрок
            room_id INTEGER NOT NULL,

            -- user_id — id пользователя
            user_id INTEGER NOT NULL,

            -- cash — баланс игрока
            -- REAL — число, можно дробное
            -- DEFAULT {START_CASH} — стартовое значение из config.py
            -- если START_CASH = 2000, новый игрок начнёт с 2000
            cash REAL DEFAULT {START_CASH},

            -- risk — риск проверки за инсайд
            -- INTEGER — целое число
            -- DEFAULT 0 — сначала риск равен 0
            risk INTEGER DEFAULT 0,

            -- holdings — акции игрока
            -- TEXT — строка
            -- внутри хранится JSON
            -- {{"tnv": 2, "olc": 1, "hgn": 0}}
            holdings TEXT DEFAULT '{{}}',

            -- day_orders — заявки игрока за текущий день
            -- хранится JSON-строкой
            -- {{"tnv": 2, "olc": -1}}
            day_orders TEXT DEFAULT '{{}}',

            -- day_actions — действия игрока за день
            -- {{"buy": true, "sell": true}} 
            day_actions TEXT DEFAULT '{{}}',

            -- insider_used — использовал ли игрок инсайд
            -- 0 — нет
            -- 1 — да
            insider_used INTEGER DEFAULT 0,

            -- insider_hints — подсказки инсайда
            -- хранится JSON-строкой
            -- {{"tnv":"завтра рост"}} 
            insider_hints TEXT DEFAULT '{{}}',

            -- finished_day — завершил ли игрок текущий день
            -- 0 — нет
            -- 1 — да
            finished_day INTEGER DEFAULT 0,

            -- events — игровые события игрока
            -- TEXT — строка
            -- DEFAULT '[]' — пустой JSON-массив
            -- пример: ["Вы купили TNV", "Вас оштрафовали"]
            events TEXT DEFAULT '[]',

            -- capital_history — капитал игрока по дням
            -- нужен для графика результатов после игры
            capital_history TEXT DEFAULT '[]',

            -- UNIQUE(room_id, user_id)
            -- ограничение уникальности
            -- один и тот же пользователь не может дважды быть добавлен
            -- в одну и ту же комнату
            UNIQUE(room_id, user_id)
        )
    """)

    columns = conn.execute(
        "PRAGMA table_info(room_players)"
    ).fetchall()

    column_names = []

    for column in columns:
        column_names.append(column["name"])

    if "capital_history" not in column_names:
        conn.execute(
            "ALTER TABLE room_players ADD COLUMN capital_history TEXT DEFAULT '[]'"
        )

    # commit() — сохранить изменения в базе app.db
    conn.commit()

    # close() — закрыть соединение с базой
    conn.close()
