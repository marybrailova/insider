import random

from config import (
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


def get_room(conn, room_id):
    return conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()


def get_room_players(conn, room_id):
    return conn.execute(
        """
        SELECT rp.*, u.username
        FROM room_players rp
        JOIN users u ON u.id = rp.user_id
        WHERE rp.room_id = ?
        ORDER BY rp.id ASC
        """,
        (room_id,),
    ).fetchall()


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


def ensure_player_defaults(conn, row):
    holdings = load_json(row["holdings"], {})
    day_orders = load_json(row["day_orders"], {})
    day_actions = load_json(row["day_actions"], {})
    insider_hints = load_json(row["insider_hints"], {})
    changed = False

    for company in COMPANIES:
        company_id = company["id"]
        if company_id not in holdings:
            holdings[company_id] = 0
            changed = True
        if company_id not in day_orders:
            day_orders[company_id] = 0
            changed = True

    if changed:
        conn.execute(
            """
            UPDATE room_players
            SET holdings = ?, day_orders = ?, day_actions = ?, insider_hints = ?
            WHERE id = ?
            """,
            (
                dump_json(holdings),
                dump_json(day_orders),
                dump_json(day_actions),
                dump_json(insider_hints),
                row["id"],
            ),
        )


def push_event_for_player(conn, player_id, title, body, tone="warn"):
    row = conn.execute("SELECT events FROM room_players WHERE id = ?", (player_id,)).fetchone()
    events = load_json(row["events"], [])
    events.append({"title": title, "body": body, "tone": tone})
    conn.execute("UPDATE room_players SET events = ? WHERE id = ?", (dump_json(events), player_id))


def push_event_for_room(conn, room_id, title, body, tone="warn"):
    players = conn.execute("SELECT id FROM room_players WHERE room_id = ?", (room_id,)).fetchall()
    for player in players:
        push_event_for_player(conn, player["id"], title, body, tone)


def get_players_count(conn, room_id):
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM room_players WHERE room_id = ?",
        (room_id,),
    ).fetchone()
    return row["cnt"]


def start_game_if_ready(conn, room_id):
    room = get_room(conn, room_id)
    if not room:
        return
    if room["status"] != "waiting":
        return

    players_count = get_players_count(conn, room_id)
    if players_count < room["max_players"]:
        return

    game_data = make_game_data()
    current_day = 1

    for company in COMPANIES:
        company_id = company["id"]
        today_plan = game_data["plans"][company_id][str(current_day)]
        game_data["companies"][company_id]["info"] = today_plan["info"]

    conn.execute(
        """
        UPDATE rooms
        SET status = ?, current_day = ?, turn_ends_at = ?, game_data = ?
        WHERE id = ?
        """,
        (
            "playing",
            current_day,
            now_seconds() + TURN_SECONDS,
            dump_json(game_data),
            room_id,
        ),
    )

    players = get_room_players(conn, room_id)
    for player in players:
        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, risk = 0, holdings = ?, day_orders = ?, day_actions = ?,
                insider_used = 0, insider_hints = ?, finished_day = 0, events = '[]'
            WHERE id = ?
            """,
            (
                START_CASH,
                dump_json(make_holdings()),
                dump_json(make_orders()),
                dump_json({}),
                dump_json({}),
                player["id"],
            ),
        )

    conn.commit()


def maybe_finish_by_time(conn, room_id):
    room = get_room(conn, room_id)
    if not room:
        return
    if room["status"] != "playing":
        return
    if room["turn_ends_at"] > now_seconds():
        return

    advance_day(conn, room_id)


def apply_order_flow(price, net_orders):
    if net_orders > 0:
        return max(5, price * 1.05)
    if net_orders < 0:
        return max(5, price * 0.95)
    return price


def apply_bubble(company_state):
    price = company_state["price"]
    real_value = company_state["real_value"]

    if price <= real_value * 1.5:
        company_state["heat_days"] = 0
        return False

    company_state["heat_days"] += 1
    chance = 0.3 + (company_state["heat_days"] - 1) * 0.1
    chance = clamp(chance, 0.0, 0.8)

    if random.random() < chance:
        wiggle = random.uniform(-0.05, 0.05)
        company_state["price"] = max(5, real_value * (1 + wiggle))
        company_state["heat_days"] = 0
        return True

    return False


def advance_day(conn, room_id):
    room = get_room(conn, room_id)
    if not room or room["status"] != "playing":
        return

    game_data = load_json(room["game_data"], {})
    companies = game_data.get("companies", {})
    players = get_room_players(conn, room_id)
    totals = make_orders()
    parsed_players = []

    for player in players:
        holdings = load_json(player["holdings"], make_holdings())
        day_orders = load_json(player["day_orders"], make_orders())
        parsed_players.append(
            {
                "row": player,
                "holdings": holdings,
                "day_orders": day_orders,
            }
        )
        for company in COMPANIES:
            company_id = company["id"]
            totals[company_id] += int(day_orders.get(company_id, 0))

    for company in COMPANIES:
        company_id = company["id"]
        company_state = companies[company_id]
        info = company_state.get("info")
        real_delta = calc_real_delta(info)
        company_state["real_value"] = max(10, company_state["real_value"] * (1 + real_delta))
        company_state["price"] = max(5, company_state["price"] * (1 + real_delta))
        company_state["price"] = apply_order_flow(company_state["price"], totals[company_id])

        if apply_bubble(company_state):
            push_event_for_room(
                conn,
                room_id,
                "Пузырь лопнул",
                f"{company['name']} резко откатился к реальной цене",
                "warn",
            )

        company_state["history"].append(company_state["price"])

    for item in parsed_players:
        player = item["row"]
        holdings = item["holdings"]
        cash = float(player["cash"])
        capital = get_player_capital(cash, holdings, companies)

        if random.random() * 100 < int(player["risk"]):
            penalty = capital * PENALTY_RATE
            cash -= penalty
            push_event_for_player(
                conn,
                player["id"],
                "Вы были пойманы",
                f"Штраф -20% капитала (-{round(penalty)} монет)",
                "danger",
            )

        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, day_orders = ?, day_actions = ?, insider_used = 0,
                insider_hints = ?, finished_day = 0
            WHERE id = ?
            """,
            (
                cash,
                dump_json(make_orders()),
                dump_json({}),
                dump_json({}),
                player["id"],
            ),
        )

    next_day = room["current_day"] + 1
    if next_day > TOTAL_DAYS:
        conn.execute(
            "UPDATE rooms SET status = ?, game_data = ?, turn_ends_at = 0 WHERE id = ?",
            ("finished", dump_json(game_data), room_id),
        )
        conn.commit()
        return

    for company in COMPANIES:
        company_id = company["id"]
        next_plan = game_data["plans"][company_id][str(next_day)]
        companies[company_id]["info"] = next_plan["info"]

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


def build_state(conn, room_id, user_id):
    maybe_finish_by_time(conn, room_id)
    start_game_if_ready(conn, room_id)

    room = get_room(conn, room_id)
    if not room:
        return None

    player = get_player_row(conn, room_id, user_id)
    if not player:
        return None

    ensure_player_defaults(conn, player)
    conn.commit()

    room = get_room(conn, room_id)
    player = get_player_row(conn, room_id, user_id)
    game_data = load_json(room["game_data"], {})
    companies_state = game_data.get("companies", {})

    if not companies_state:
        companies_state = make_company_state()

    for company in COMPANIES:
        company_id = company["id"]
        if company_id not in companies_state:
            companies_state[company_id] = {
                "price": 100,
                "real_value": 100,
                "history": [100],
                "info": None,
                "heat_days": 0,
            }

    players = get_room_players(conn, room_id)
    holdings = load_json(player["holdings"], make_holdings())
    day_actions = load_json(player["day_actions"], {})
    insider_hints = load_json(player["insider_hints"], {})
    events = load_json(player["events"], [])
    companies = []

    for company in COMPANIES:
        company_id = company["id"]
        state_company = companies_state[company_id]
        companies.append(
            {
                "id": company_id,
                "name": company["name"],
                "ticker": company["ticker"],
                "sector": company["sector"],
                "icon": company["icon"],
                "price": state_company["price"],
                "real_value": state_company["real_value"],
                "history": state_company["history"],
                "info": state_company.get("info"),
                "info_label": info_label(state_company.get("info")),
            }
        )

    ranking = []
    for row in players:
        row_holdings = load_json(row["holdings"], make_holdings())
        capital = get_player_capital(row["cash"], row_holdings, companies_state)
        ranking.append({"name": row["username"], "capital": round(capital)})
    ranking.sort(key=lambda item: item["capital"], reverse=True)

    turn_seconds_left = 0
    if room["status"] == "playing":
        turn_seconds_left = max(0, room["turn_ends_at"] - now_seconds())

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
            "capital": round(get_player_capital(player["cash"], holdings, companies_state)),
            "holdings": holdings,
            "day_actions": day_actions,
            "insider_hints": insider_hints,
            "insider_used": bool(player["insider_used"]),
            "finished_day": bool(player["finished_day"]),
        },
        "players": [
            {"name": row["username"], "finished_day": bool(row["finished_day"])}
            for row in players
        ],
        "companies": companies,
        "ranking": ranking,
        "event": events[0] if events else None,
    }
