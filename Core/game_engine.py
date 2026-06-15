# random —
# библиотека случайности
#
# нужна:
# для пузырей
# штрафов
# случайных событий
import random


# импортируем настройки и функции из config.py
from Core.config import (

    # список компаний игры
    COMPANIES,

    # процент штрафа
    # 0.1 = 10%
    PENALTY_RATE,

    # стартовые деньги игрока
    START_CASH,

    # сколько всего игровых дней
    TOTAL_DAYS,

    # длительность хода в секундах
    TURN_SECONDS,

    # считает влияние новости на компанию
    calc_real_delta,

    # ограничивает число
    clamp,

    # Python -> JSON строка
    # нужно для SQLite
    dump_json,

    # считает капитал игрока
    # деньги + акции
    get_player_capital,

    # делает красивый текст новости
    info_label,

    # JSON строка -> Python объект
    load_json,

    # создаёт стартовое состояние игры
    make_game_data,

    # создаёт стартовое состояние компаний
    make_company_state,

    # создаёт пустой портфель игрока
    make_holdings,

    # создаёт пустые заявки игрока
    make_orders,

    # текущее время в секундах
    now_seconds,
)

# получить комнату по id
# нужно чтобы получить данные комнаты
def get_room(conn, room_id):

    # execute
    # выполнить SQL запрос
    return conn.execute(

        # SELECT * —
        # взять все поля
        #
        # FROM rooms —
        # из таблицы rooms
        #
        # WHERE id = ? —
        # где id совпадает
        #
        # ? —
        # сюда подставится room_id
        "SELECT * FROM rooms WHERE id = ?",

        # room_id подставится вместо ?
        (room_id,),

    # fetchone()
    # взять одну строку
    # потому что id уникальный
    ).fetchone()


# получить всех игроков комнаты
# нужно для рейтинга, списка игроков, проверки завершения дня

def get_room_players(conn, room_id):
    return conn.execute(

        """
        -- берем данные игроков + username
        SELECT rp.*, u.username

        -- основная таблица игроков
        FROM room_players rp

        -- подключаем таблицу users
        JOIN users u

        -- связываем игрока и username
        ON u.id = rp.user_id

        -- только игроки нужной комнаты
        WHERE rp.room_id = ?

        -- сортировка по id
        ORDER BY rp.id
        """,

        # сюда подставится room_id
        (room_id,),

    # взять все найденные строки
    ).fetchall()


# получить одного игрока в комнате
# нужно чтобы получить состояние конкретного игрока
def get_player_row(conn, room_id, user_id):

    # делаем SQL запрос
    return conn.execute(

        """
        -- берем данные игрока + username
        SELECT rp.*, u.username

        -- основная таблица игроков
        FROM room_players rp

        -- подключаем users
        JOIN users u

        -- связываем игрока и username
        ON u.id = rp.user_id

        -- ищем нужную комнату и нужного пользователя
        WHERE rp.room_id = ? AND rp.user_id = ?
        """,

        # сюда подставятся room_id и user_id
        (room_id, user_id),

    # взять одну строку потому что такой игрок один
    ).fetchone()


# добавить событие одному игроку
# для модальных окон и уведомлений игрока
def push_event_for_player(conn, player_id, title, body, tone="warn"):

    # достаем events нужного игрока из БД
    row = conn.execute(

        # берем поле events у игрока с нужным id
        "SELECT events FROM room_players WHERE id = ?",

        # сюда подставится player_id
        (player_id,),
    ).fetchone()

    # JSON строка в Python список
    # [] если событий пока нет
    events = load_json(row["events"], [])

    # добавляем новое событие в список
    events.append({

        # заголовок окна
        "title": title,

        # текст события
        "body": body,

        # стиль окна warn/danger/success
        "tone": tone,
    })

    # сохраняем обновленный список обратно в SQLite
    conn.execute(

        # обновляем поле events у игрока
        "UPDATE room_players SET events = ? WHERE id = ?",

        # Python список в JSON строка
        (
            dump_json(events),
            player_id,
        ),
    )


# добавить событие всем игрокам комнаты
# чтобы отправлять общее событие сразу всей комнате
def push_event_for_room(conn, room_id, title, body, tone="warn"):

    # получаем id всех игроков комнаты
    players = conn.execute(

        # берем id игроков у которых room_id совпадает
        "SELECT id FROM room_players WHERE room_id = ?",

        # сюда подставится room_id
        (room_id,),

    # fetchall() взять все строки
    ).fetchall()

    # проходимся по всем игрокам
    for player in players:

        # каждому игроку добавляем событие
        push_event_for_player(

            # подключение к БД
            conn,

            # id игрока
            player["id"],

            # заголовок события
            title,

            # текст события
            body,

            # стиль окна
            tone,
        )


# посчитать количество игроков в комнате
# нужно чтобы понять, можно ли уже запускать игру
def get_players_count(conn, room_id):

    row = conn.execute(

        # COUNT(*) посчитать количество строк
        # AS cnt назвать результат cnt
        # WHERE room_id = ? только игроки нужной комнаты
        "SELECT COUNT(*) AS cnt FROM room_players WHERE room_id = ?",

        # сюда подставится room_id
        (room_id,),

    # fetchone() —
    # взять одну строку
    ).fetchone()

    # вернуть количество игроков
    return row["cnt"]


# запустить игру, если комната уже заполнена
# нужно в проекте чтобы игра автоматически стартовала когда зашло нужное количество игроков
def start_game_if_ready(conn, room_id):

    # получаем комнату
    room = get_room(conn, room_id)

    # если комнаты нет выходим из функции
    if not room:
        return

    # если игра уже идет или закончена ничего не делаем
    if room["status"] != "waiting":
        return

    # если игроков пока мало не запускаем игру
    if get_players_count(conn, room_id) < room["max_players"]:
        return

    # создаем стартовое состояние игры:
    game_data = make_game_data()

    # ставим новости/слухи для первого дня
    for company in COMPANIES:

        company_id = company["id"]

        # записываем info первого дня в текущее состояние компании
        game_data["companies"][company_id]["info"] = (
            game_data["plans"][company_id]["1"]["info"]
        )

    # обновляем комнату переводим игру в playing
    conn.execute(

        """
        -- UPDATE обновить строку
        UPDATE rooms

        -- SET изменить поля
        SET status = ?, current_day = ?, turn_ends_at = ?, game_data = ?

        -- нужная комната
        WHERE id = ?
        """,

        (
            # игра началась
            "playing",

            # стартуем с 1 дня
            1,

            # ставим таймер конца хода
            now_seconds() + TURN_SECONDS,

            # сохраняем game_data в SQLite
            dump_json(game_data),

            # id комнаты
            room_id,
        ),
    )

    # получаем всех игроков комнаты
    players = get_room_players(conn, room_id)

    # обнуляем состояние игроков
    # перед стартом игры
    for player in players:

        conn.execute(

            """
            UPDATE room_players

            -- сбрасываем параметры игрока
            SET cash = ?, risk = 0, holdings = ?, day_orders = ?,
                day_actions = ?, insider_used = 0,
                insider_hints = ?, finished_day = 0,
                events = '[]', capital_history = ?

            WHERE id = ?
            """,

            (
                # стартовые деньги
                START_CASH,

                # пустые акции
                dump_json(make_holdings()),

                # пустые заявки
                dump_json(make_orders()),

                # пустые действия
                dump_json({}),

                # пустые инсайды
                dump_json({}),

                # стартовая точка графика капитала
                dump_json([START_CASH]),

                # id игрока
                player["id"],
            ),
        )

    # сохраняем изменения в SQLite
    conn.commit()


# проверить не закончился ли ход по таймеру
# нужно чтобы день автоматически переключался даже если игроки ничего не нажали
def maybe_finish_by_time(conn, room_id):

    # получаем комнату
    room = get_room(conn, room_id)

    # если комнаты нет выходим
    if not room:
        return

    # если игра не идет ничего не делаем
    if room["status"] != "playing":
        return

    # если текущее время уже больше таймера комнаты
    if room["turn_ends_at"] <= now_seconds():

        # переводим игру на следующий день
        advance_day(conn, room_id)


# проверка рыночного пузыря
# нужно в проекте чтобы цена не росла бесконечно и иногда резко обваливалась
def apply_bubble(company_state):

    # текущая цена акции
    price = company_state["price"]

    # реальная стоимость компании
    real_value = company_state["real_value"]

    # если цена не слишком высокая — пузыря нет
    # 1.5 значит цена выше реальной на 50%
    if price <= real_value * 1.5:

        # сбрасываем перегрев
        company_state["heat_days"] = 0

        # пузыря нет
        return False

    # если цена слишком высокая увеличиваем дни перегрева
    company_state["heat_days"] += 1

    # chance — шанс обвала пузыря день 0.3 0.4 0.5
    chance = 0.3 + (company_state["heat_days"] - 1) * 0.1

    # clamp ограничиваем шанс максимум до 0.8
    chance = clamp(chance, 0, 0.8)

    # random.random() —
    # случайное число от 0 до 1
    # если число меньше chance пузырь лопается
    if random.random() < chance:

        # резко возвращаем цену
        # ближе к реальной стоимости
        company_state["price"] = max(

            # цена не может быть ниже 5
            5,

            # real_value * случайное отклонение 5%
            real_value * (1 + random.uniform(-0.05, 0.05))
        )

        # сбрасываем перегрев
        company_state["heat_days"] = 0

        # пузырь лопнул
        return True

    # пузырь пока не лопнул
    return False


# переход к следующему дню
# нужно чтобы обновлять рынок
def advance_day(conn, room_id):

    # получаем комнату
    room = get_room(conn, room_id)

    # если комнаты нет выходим
    if not room:
        return

    # если игра не идет ничего не делаем
    if room["status"] != "playing":
        return

    # JSON строка в Python dict
    game_data = load_json(room["game_data"], {})

    # текущее состояние компаний
    companies = game_data["companies"]

    # получаем игроков комнаты
    players = get_room_players(conn, room_id)

    # totals суммарные покупки/продажи
    totals = make_orders()

    # проходим по игрокам
    for player in players:

        # заявки игрока за день
        day_orders = load_json(
            player["day_orders"],
            make_orders(),
        )

        # проходим по компаниям
        for company in COMPANIES:

            company_id = company["id"]

            # суммируем заявки всех игроков
            totals[company_id] += int(
                day_orders.get(company_id, 0)
            )

    # обновляем компании
    for company in COMPANIES:

        # id компании
        company_id = company["id"]

        # текущее состояние компании
        company_state = companies[company_id]

        # считаем влияние новости/слуха
        delta = calc_real_delta(
            company_state.get("info")
        )

        # меняем real_value
        # real_value не может быть ниже 10
        company_state["real_value"] = max(
            10,
            company_state["real_value"] * (1 + delta)
        )

        # меняем рыночную цену
        # цена не может быть ниже 5
        company_state["price"] = max(
            5,
            company_state["price"] * (1 + delta)
        )

        # если покупок больше цена растет еще на 5%
        if totals[company_id] > 0:
            company_state["price"] *= 1.05

        # если продаж больше цена падает еще на 5%
        if totals[company_id] < 0:
            company_state["price"] *= 0.95

        # проверяем пузырь
        if apply_bubble(company_state):

            # отправляем событие всей комнате
            push_event_for_room(
                conn,
                room_id,
                "Пузырь лопнул",
                company["name"] + " резко откатился к реальной цене",
                "warn",
            )

        # добавляем цену в history
        company_state["history"].append(
            company_state["price"]
        )

    # проверяем штрафы за инсайд
    for player in players:

        # акции игрока
        holdings = load_json(
            player["holdings"],
            make_holdings(),
        )

        # деньги игрока
        cash = float(player["cash"])

        # считаем капитал деньги + акции
        capital = get_player_capital(
            cash,
            holdings,
            companies,
        )

        # проверка риска
        if random.random() * 100 < int(player["risk"]):

            # размер штрафа
            penalty = capital * PENALTY_RATE

            # списываем деньги
            cash -= penalty

            # отправляем событие игроку
            push_event_for_player(
                conn,
                player["id"],
                "Вы были пойманы",
                "Штраф -10% капитала (-" +
                str(round(penalty)) +
                " монет)",
                "danger",
            )

        capital_history = load_json(
            player["capital_history"],
            [START_CASH],
        )

        capital_history.append(
            round(
                get_player_capital(
                    cash,
                    holdings,
                    companies,
                )
            )
        )

        # сбрасываем действия игрока
        # перед новым днем
        conn.execute(

            """
            UPDATE room_players

            SET cash = ?, day_orders = ?, day_actions = ?,
                insider_used = 0, insider_hints = ?,
                finished_day = 0, capital_history = ?

            WHERE id = ?
            """,

            (
                # обновленные деньги
                cash,

                # пустые заявки
                dump_json(make_orders()),

                # пустые действия
                dump_json({}),

                # очищаем инсайды
                dump_json({}),

                # история капитала для итогового графика
                dump_json(capital_history),

                # id игрока
                player["id"],
            ),
        )

    # следующий день
    next_day = room["current_day"] + 1

    # если дни закончились завершаем игру
    if next_day > TOTAL_DAYS:

        conn.execute(

            """
            UPDATE rooms

            SET status = ?, game_data = ?, turn_ends_at = 0

            WHERE id = ?
            """,

            (
                # игра закончена
                "finished",

                # сохраняем рынок
                dump_json(game_data),

                # id комнаты
                room_id,
            ),
        )

        # сохраняем изменения
        conn.commit()

        return

    # ставим новости следующего дня
    for company in COMPANIES:

        company_id = company["id"]

        # берем info из plans[next_day]
        companies[company_id]["info"] = (
            game_data["plans"][company_id][str(next_day)]["info"]
        )

    # обновляем комнату
    conn.execute(

        """
        UPDATE rooms

        SET current_day = ?, turn_ends_at = ?, game_data = ?

        WHERE id = ?
        """,

        (
            # новый день
            next_day,

            # новый таймер
            now_seconds() + TURN_SECONDS,

            # сохраняем game_data
            dump_json(game_data),

            # id комнаты
            room_id,
        ),
    )

    # сохраняем изменения в SQLite
    conn.commit()


# проверяем, все ли игроки завершили текущий день
def all_players_finished(conn, room_id):
    rows = conn.execute(
        "SELECT finished_day FROM room_players WHERE room_id = ?",
        (room_id,),
    ).fetchall()

    if not rows:
        return False

    for row in rows:
        if row["finished_day"] != 1:
            return False

    return True


# собрать состояние игры для frontend
# нужно в проекте:
# чтобы frontend получил ВСЮ информацию
# для отрисовки игры
def build_state(conn, room_id, user_id):

    # проверяем:
    # не закончился ли ход
    # и не пора ли стартовать игру
    maybe_finish_by_time(conn, room_id)
    start_game_if_ready(conn, room_id)

    # получаем комнату
    room = get_room(conn, room_id)

    # если комнаты нет —
    # возвращаем None
    if not room:
        return None

    # получаем игрока
    player = get_player_row(conn, room_id, user_id)

    # если игрока нет —
    # возвращаем None
    if not player:
        return None

    # JSON строка -> Python dict
    game_data = load_json(room["game_data"], {})

    # состояние компаний
    #
    # если companies нет —
    # создаем стартовое состояние
    companies_state = game_data.get("companies") or make_company_state()

    # все игроки комнаты
    players = get_room_players(conn, room_id)

    # акции игрока
    holdings = load_json(player["holdings"], make_holdings())

    # действия игрока за день
    day_actions = load_json(player["day_actions"], {})

    # подсказки инсайда
    insider_hints = load_json(player["insider_hints"], {})

    # события игрока
    events = load_json(player["events"], [])

    # список компаний для frontend
    companies = []

    # собираем карточки компаний
    for company in COMPANIES:

        # tnv / olc / hgn
        company_id = company["id"]

        # текущее состояние компании
        state = companies_state[company_id]

        # добавляем данные компании
        companies.append({

            # id компании
            "id": company_id,

            # название
            "name": company["name"],

            # тикер
            "ticker": company["ticker"],

            # сектор
            "sector": company["sector"],

            # emoji
            "icon": company["icon"],

            # рыночная цена
            "price": state["price"],

            # реальная стоимость
            "real_value": state["real_value"],

            # график цены
            "history": state["history"],

            # info компании
            "info": state["info"],

            # красивый текст для frontend
            "info_label": info_label(state["info"]),
        })

    # рейтинг игроков
    ranking = []

    # считаем капитал игроков
    for row in players:

        # акции игрока
        row_holdings = load_json(
            row["holdings"],
            make_holdings(),
        )

        # капитал:
        # деньги + акции
        capital = get_player_capital(
            row["cash"],
            row_holdings,
            companies_state,
        )

        # добавляем игрока в рейтинг
        ranking.append({

            # username
            "name": row["username"],

            # капитал
            "capital": round(capital),

            # история капитала по дням
            "capital_history": load_json(
                row["capital_history"],
                [START_CASH],
            ),
        })

    # сортируем рейтинг:
    # самый богатый сверху
    ranking.sort(

        # сортировка по capital
        key=lambda x: x["capital"],

        # reverse=True —
        # по убыванию
        reverse=True,
    )

    # сколько осталось секунд хода
    turn_seconds_left = 0

    # если игра идет —
    # считаем таймер
    if room["status"] == "playing":

        turn_seconds_left = max(

            # минимум 0
            0,

            # конец таймера - текущее время
            room["turn_ends_at"] - now_seconds()
        )

    # список игроков для frontend
    players_data = []

    # собираем игроков
    for row in players:

        players_data.append({

            # username
            "name": row["username"],

            # закончил ли день
            "finished_day": bool(row["finished_day"]),
        })

    # главный ответ для frontend
    return {

        # ok —
        # запрос успешный
        "ok": True,

        # данные комнаты
        "room": {

            "id": room["id"],
            "title": room["title"],
            "code": room["join_code"],
            "room_type": room["room_type"],
            "status": room["status"],
            "current_day": room["current_day"],
            "total_days": TOTAL_DAYS,
            "max_players": room["max_players"],

            # количество игроков
            "players_count": len(players),

            # таймер
            "turn_seconds_left": turn_seconds_left,
        },

        # данные текущего игрока
        "me": {

            "id": player["user_id"],
            "username": player["username"],

            # деньги
            "cash": round(player["cash"]),

            # риск штрафа
            "risk": int(player["risk"]),

            # капитал игрока
            "capital": round(
                get_player_capital(
                    player["cash"],
                    holdings,
                    companies_state,
                )
            ),

            # акции
            "holdings": holdings,

            # действия за день
            "day_actions": day_actions,

            # инсайды
            "insider_hints": insider_hints,

            # покупал ли инсайд
            "insider_used": bool(player["insider_used"]),

            # закончил ли день
            "finished_day": bool(player["finished_day"]),
        },

        # список игроков
        "players": players_data,

        # компании
        "companies": companies,

        # рейтинг
        "ranking": ranking,

        # первое событие игрока
        #
        # если событий нет —
        # None
        "event": events[0] if events else None,
    }
