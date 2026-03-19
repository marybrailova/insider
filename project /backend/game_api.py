from flask import jsonify, request

from auth_api import require_user
from config import (
    COMPANY_BY_ID,
    INSIDER_COST,
    INSIDER_RISK_ADD,
    MAX_RISK,
    TOTAL_DAYS,
    clamp,
    direction_text,
    dump_json,
    load_json,
    make_holdings,
    make_orders,
)
from database import get_db
from game_engine import (
    advance_day,
    all_players_finished,
    build_state,
    get_player_row,
    get_room,
    maybe_finish_by_time,
    push_event_for_player,
)


def register_game_routes(app):
    @app.get("/api/rooms/<int:room_id>/state")
    def room_state(room_id):
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        conn = get_db()
        state = build_state(conn, room_id, user_id)
        conn.close()

        if not state:
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        return jsonify(state)

    @app.post("/api/rooms/<int:room_id>/trade")
    def trade(room_id):
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json(silent=True) or {}
        company_id = data.get("company_id")
        action = data.get("action")
        qty = int(data.get("qty") or 0)

        if company_id not in COMPANY_BY_ID:
            return jsonify({"ok": False, "error": "Неизвестная компания"}), 400

        if action not in ["buy", "sell"]:
            return jsonify({"ok": False, "error": "Неизвестное действие"}), 400

        if qty <= 0:
            return jsonify({"ok": False, "error": "Количество должно быть больше нуля"}), 400

        conn = get_db()
        maybe_finish_by_time(conn, room_id)
        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        if room["status"] != "playing":
            conn.close()
            return jsonify({"ok": False, "error": "Игра ещё не началась"}), 400

        if player["finished_day"]:
            conn.close()
            return jsonify({"ok": False, "error": "Вы уже завершили день"}), 400

        game_data = load_json(room["game_data"], {})
        companies = game_data.get("companies", {})
        company_state = companies[company_id]
        price = company_state["price"]

        holdings = load_json(player["holdings"], make_holdings())
        day_orders = load_json(player["day_orders"], make_orders())
        day_actions = load_json(player["day_actions"], {})
        cash = float(player["cash"])

        if day_actions.get(company_id):
            conn.close()
            return jsonify({"ok": False, "error": "По этой компании действие уже выбрано"}), 400

        if action == "buy":
            total = price * qty
            if cash < total:
                conn.close()
                return jsonify({"ok": False, "error": "Недостаточно денег"}), 400
            cash -= total
            holdings[company_id] += qty
            day_orders[company_id] += qty

        if action == "sell":
            if holdings[company_id] < qty:
                conn.close()
                return jsonify({"ok": False, "error": "Недостаточно акций"}), 400
            cash += price * qty
            holdings[company_id] -= qty
            day_orders[company_id] -= qty

        day_actions[company_id] = action

        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, holdings = ?, day_orders = ?, day_actions = ?
            WHERE id = ?
            """,
            (
                cash,
                dump_json(holdings),
                dump_json(day_orders),
                dump_json(day_actions),
                player["id"],
            ),
        )
        conn.commit()

        state = build_state(conn, room_id, user_id)
        conn.close()
        return jsonify(state)

    @app.post("/api/rooms/<int:room_id>/insider")
    def buy_insider(room_id):
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json(silent=True) or {}
        company_id = data.get("company_id")

        if company_id not in COMPANY_BY_ID:
            return jsonify({"ok": False, "error": "Неизвестная компания"}), 400

        conn = get_db()
        maybe_finish_by_time(conn, room_id)
        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        if room["status"] != "playing":
            conn.close()
            return jsonify({"ok": False, "error": "Игра ещё не началась"}), 400

        if player["finished_day"]:
            conn.close()
            return jsonify({"ok": False, "error": "Вы уже завершили день"}), 400

        if player["insider_used"]:
            conn.close()
            return jsonify({"ok": False, "error": "Сегодня инсайд уже куплен"}), 400

        cash = float(player["cash"])
        if cash < INSIDER_COST:
            conn.close()
            return jsonify({"ok": False, "error": "Недостаточно денег"}), 400

        room_day = int(room["current_day"])
        game_data = load_json(room["game_data"], {})
        tomorrow_plan = None

        if room_day < TOTAL_DAYS:
            tomorrow_plan = game_data["plans"][company_id].get(str(room_day + 1))

        direction = "neutral"
        if tomorrow_plan:
            delta = tomorrow_plan["real_delta"]
            if delta > 0:
                direction = "up"
            elif delta < 0:
                direction = "down"

        insider_hints = load_json(player["insider_hints"], {})
        insider_hints[company_id] = direction

        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, risk = ?, insider_used = 1, insider_hints = ?
            WHERE id = ?
            """,
            (
                cash - INSIDER_COST,
                clamp(int(player["risk"]) + INSIDER_RISK_ADD, 0, MAX_RISK),
                dump_json(insider_hints),
                player["id"],
            ),
        )
        push_event_for_player(
            conn,
            player["id"],
            "Инсайдерская информация",
            f"{COMPANY_BY_ID[company_id]['name']}: завтра {direction_text(direction)}",
            "warn",
        )
        conn.commit()

        state = build_state(conn, room_id, user_id)
        conn.close()
        return jsonify(state)

    @app.post("/api/rooms/<int:room_id>/finish-day")
    def finish_day(room_id):
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        conn = get_db()
        maybe_finish_by_time(conn, room_id)
        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        if room["status"] != "playing":
            conn.close()
            return jsonify({"ok": False, "error": "Игра ещё не началась"}), 400

        conn.execute(
            "UPDATE room_players SET finished_day = 1 WHERE id = ?",
            (player["id"],),
        )
        conn.commit()

        if all_players_finished(conn, room_id):
            advance_day(conn, room_id)

        state = build_state(conn, room_id, user_id)
        conn.close()
        return jsonify(state)

    @app.post("/api/rooms/<int:room_id>/events/ack")
    def ack_event(room_id):
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        conn = get_db()
        player = get_player_row(conn, room_id, user_id)
        if not player:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        events = load_json(player["events"], [])
        if events:
            events.pop(0)
            conn.execute(
                "UPDATE room_players SET events = ? WHERE id = ?",
                (dump_json(events), player["id"]),
            )
            conn.commit()

        state = build_state(conn, room_id, user_id)
        conn.close()
        return jsonify(state)
