import random

from Core.config import (
    COMPANIES,
    PENALTY_RATE,
    START_CASH,
    TOTAL_DAYS,
    TURN_SECONDS,
    calc_real_delta,
    clamp,
    dump_json,
    get_player_capital,
    info_label,
    load_json,
    make_company_state,
    make_game_data,
    make_holdings,
    make_orders,
    now_seconds,
)


# получаем комнату
def get_room(conn, room_id):
    return conn.execute(
        "SELECT * FROM rooms WHERE id = ?",
        (room_id,),
    ).fetchone()


# получаем игроков комнаты
def get_room_players(conn, room_id):
    return conn.execute(
        """
        SELECT rp.*, u.username
        FROM room_players rp
        JOIN users u ON u.id = rp.user_id
        WHERE rp.room_id = ?
        ORDER BY rp.id
        """,
        (room_id,),
    ).fetchall()


# получаем игрока
def get_player_row(conn, room_id, user_id):
    return conn.execute(
        """
        SELECT rp.*, u.username
        FROM room_players rp
        JOIN users u ON u.id = rp.user_id
        WHERE rp.room_id = ? AND rp.user_id = ?
        """,
        (room_id, user_id),
    ).fetchone()


# добавляем событие игроку
def push_event_for_player(conn, player_id, title, body, tone="warn"):
    row = conn.execute(
        "SELECT events FROM room_players WHERE id = ?",
        (player_id,),
    ).fetchone()

    events = load_json(row["events"], [])

    events.append({
        "title": title,
        "body": body,
        "tone": tone,
    })

    conn.execute(
        "UPDATE room_players SET events = ? WHERE id = ?",
        (dump_json(events), player_id),
    )


# добавляем событие всем игрокам комнаты
def push_event_for_room(conn, room_id, title, body, tone="warn"):
    players = conn.execute(
        "SELECT id FROM room_players WHERE room_id = ?",
        (room_id,),
    ).fetchall()

    for player in players:
        push_event_for_player(
            conn,
            player["id"],
            title,
            body,
            tone,
        )


# считаем игроков комнаты
def get_players_count(conn, room_id):
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM room_players WHERE room_id = ?",
        (room_id,),
    ).fetchone()

    return row["cnt"]


# запускаем игру, если комната заполнена
def start_game_if_ready(conn, room_id):
    room = get_room(conn, room_id)

    if not room:
        return

    if room["status"] != "waiting":
        return

    if get_players_count(conn, room_id) < room["max_players"]:
        return

    game_data = make_game_data()

    # ставим информацию первого дня
    for company in COMPANIES:
        company_id = company["id"]

        game_data["companies"][company_id]["info"] = (
            game_data["plans"][company_id]["1"]["info"]
        )

    conn.execute(
        """
        UPDATE rooms
        SET status = ?, current_day = ?, turn_ends_at = ?, game_data = ?
        WHERE id = ?
        """,
        (
            "playing",
            1,
            now_seconds() + TURN_SECONDS,
            dump_json(game_data),
            room_id,
        ),
    )

    players = get_room_players(conn, room_id)

    # сбрасываем игроков перед стартом
    for player in players:
        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, risk = 0, holdings = ?, day_orders = ?,
                day_actions = ?, insider_used = 0,
                insider_hints = ?, finished_day = 0,
                events = '[]', capital_history = ?
            WHERE id = ?
            """,
            (
                START_CASH,
                dump_json(make_holdings()),
                dump_json(make_orders()),
                dump_json({}),
                dump_json({}),
                dump_json([START_CASH]),
                player["id"],
            ),
        )

    conn.commit()


# завершаем день по времени
def maybe_finish_by_time(conn, room_id):
    room = get_room(conn, room_id)

    if not room:
        return

    if room["status"] != "playing":
        return

    if room["turn_ends_at"] <= now_seconds():
        advance_day(conn, room_id)


# проверяем пузырь
def apply_bubble(company_state):
    price = company_state["price"]
    real_value = company_state["real_value"]

    if price <= real_value * 1.5:
        company_state["heat_days"] = 0
        return False

    company_state["heat_days"] += 1

    chance = 0.3 + (company_state["heat_days"] - 1) * 0.1
    chance = clamp(chance, 0, 0.8)

    if random.random() < chance:
        company_state["price"] = max(
            5,
            real_value * (1 + random.uniform(-0.05, 0.05)),
        )

        company_state["heat_days"] = 0

        return True

    return False


# переход к следующему дню
def advance_day(conn, room_id):
    room = get_room(conn, room_id)

    if not room:
        return

    if room["status"] != "playing":
        return

    game_data = load_json(room["game_data"], {})
    companies = game_data["companies"]

    players = get_room_players(conn, room_id)

    totals = make_orders()

    # считаем общий спрос по компаниям
    for player in players:
        day_orders = load_json(
            player["day_orders"],
            make_orders(),
        )

        for company in COMPANIES:
            company_id = company["id"]

            totals[company_id] += int(
                day_orders.get(company_id, 0)
            )

    # обновляем компании
    for company in COMPANIES:
        company_id = company["id"]

        company_state = companies[company_id]

        delta = calc_real_delta(
            company_state.get("info")
        )

        company_state["real_value"] = max(
            10,
            company_state["real_value"] * (1 + delta),
        )

        company_state["price"] = max(
            5,
            company_state["price"] * (1 + delta),
        )

        if totals[company_id] > 0:
            company_state["price"] *= 1.05

        if totals[company_id] < 0:
            company_state["price"] *= 0.95

        if apply_bubble(company_state):
            push_event_for_room(
                conn,
                room_id,
                "Пузырь лопнул",
                company["name"] + " резко откатился к реальной цене",
                "warn",
            )

        company_state["history"].append(
            company_state["price"]
        )

    # обновляем игроков
    for player in players:
        holdings = load_json(
            player["holdings"],
            make_holdings(),
        )

        cash = float(player["cash"])

        capital = get_player_capital(
            cash,
            holdings,
            companies,
        )

        # проверяем риск проверки
        if random.random() * 100 < int(player["risk"]):
            penalty = capital * PENALTY_RATE

            cash -= penalty

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

        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, day_orders = ?, day_actions = ?,
                insider_used = 0, insider_hints = ?,
                finished_day = 0, capital_history = ?
            WHERE id = ?
            """,
            (
                cash,
                dump_json(make_orders()),
                dump_json({}),
                dump_json({}),
                dump_json(capital_history),
                player["id"],
            ),
        )

    next_day = room["current_day"] + 1

    # завершаем игру после последнего дня
    if next_day > TOTAL_DAYS:
        conn.execute(
            """
            UPDATE rooms
            SET status = ?, game_data = ?, turn_ends_at = 0
            WHERE id = ?
            """,
            (
                "finished",
                dump_json(game_data),
                room_id,
            ),
        )

        conn.commit()

        return

    # ставим информацию следующего дня
    for company in COMPANIES:
        company_id = company["id"]

        companies[company_id]["info"] = (
            game_data["plans"][company_id][str(next_day)]["info"]
        )

    conn.execute(
        """
        UPDATE rooms
        SET current_day = ?, turn_ends_at = ?, game_data = ?
        WHERE id = ?
        """,
        (
            next_day,
            now_seconds() + TURN_SECONDS,
            dump_json(game_data),
            room_id,
        ),
    )

    conn.commit()


# проверяем, все ли завершили день
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


# собираем состояние игры
def build_state(conn, room_id, user_id):
    maybe_finish_by_time(conn, room_id)

    start_game_if_ready(conn, room_id)

    room = get_room(conn, room_id)

    if not room:
        return None

    player = get_player_row(conn, room_id, user_id)

    if not player:
        return None

    game_data = load_json(room["game_data"], {})

    companies_state = game_data.get("companies") or make_company_state()

    players = get_room_players(conn, room_id)

    holdings = load_json(
        player["holdings"],
        make_holdings(),
    )

    day_actions = load_json(
        player["day_actions"],
        {},
    )

    insider_hints = load_json(
        player["insider_hints"],
        {},
    )

    events = load_json(
        player["events"],
        [],
    )

    companies = []

    # собираем компании для фронта
    for company in COMPANIES:
        company_id = company["id"]

        state = companies_state[company_id]

        companies.append({
            "id": company_id,
            "name": company["name"],
            "ticker": company["ticker"],
            "sector": company["sector"],
            "icon": company["icon"],
            "price": state["price"],
            "real_value": state["real_value"],
            "history": state["history"],
            "info": state["info"],
            "info_label": info_label(state["info"]),
        })

    ranking = []

    # собираем рейтинг
    for row in players:
        row_holdings = load_json(
            row["holdings"],
            make_holdings(),
        )

        capital = get_player_capital(
            row["cash"],
            row_holdings,
            companies_state,
        )

        ranking.append({
            "name": row["username"],
            "capital": round(capital),
            "capital_history": load_json(
                row["capital_history"],
                [START_CASH],
            ),
        })

    ranking.sort(
        key=lambda x: x["capital"],
        reverse=True,
    )

    turn_seconds_left = 0

    if room["status"] == "playing":
        turn_seconds_left = max(
            0,
            room["turn_ends_at"] - now_seconds(),
        )

    players_data = []

    # собираем игроков комнаты
    for row in players:
        players_data.append({
            "name": row["username"],
            "finished_day": bool(row["finished_day"]),
        })

    return {
        "ok": True,

        "room": {
            "id": room["id"],
            "title": room["title"],
            "code": room["join_code"],
            "room_type": room["room_type"],
            "status": room["status"],
            "current_day": room["current_day"],
            "total_days": TOTAL_DAYS,
            "max_players": room["max_players"],
            "players_count": len(players),
            "turn_seconds_left": turn_seconds_left,
        },

        "me": {
            "id": player["user_id"],
            "username": player["username"],
            "cash": round(player["cash"]),
            "risk": int(player["risk"]),
            "capital": round(
                get_player_capital(
                    player["cash"],
                    holdings,
                    companies_state,
                )
            ),
            "holdings": holdings,
            "day_actions": day_actions,
            "insider_hints": insider_hints,
            "insider_used": bool(player["insider_used"]),
            "finished_day": bool(player["finished_day"]),
        },

        "players": players_data,
        "companies": companies,
        "ranking": ranking,
        "event": events[0] if events else None,
    }
