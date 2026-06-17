from flask import jsonify, request

from API.auth_api import require_user
from Core.config import (
    INSIDER_COST,
    INSIDER_RISK_ADD,
    dump_json,
    load_json,
    make_holdings,
    make_orders,
)
from Database.database import get_db
from Core.game_engine import (
    advance_day,
    all_players_finished,
    build_state,
    get_player_row,
    get_room,
    maybe_finish_by_time,
    push_event_for_player,
)


# регистрируем игровые маршруты
def register_game_routes(app):

    # состояние комнаты
    @app.get("/api/rooms/<int:room_id>/state")
    def room_state(room_id):
        user_id = require_user()

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Сначала войдите",
            }), 401

        conn = get_db()

        state = build_state(conn, room_id, user_id)

        conn.close()

        if not state:
            return jsonify({
                "ok": False,
                "error": "Комната не найдена",
            }), 404

        return jsonify(state)

    # покупка или продажа акций
    @app.post("/api/rooms/<int:room_id>/trade")
    def trade(room_id):
        user_id = require_user()

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Сначала войдите",
            }), 401

        data = request.get_json() or {}

        company_id = data.get("company_id")
        action = data.get("action")
        qty = int(data.get("qty") or 0)
        current_day = int(data.get("current_day") or 0)

        if company_id not in ["tnv", "olc", "hgn"]:
            return jsonify({
                "ok": False,
                "error": "Неизвестная компания",
            }), 400

        if action not in ["buy", "sell"]:
            return jsonify({
                "ok": False,
                "error": "Неизвестное действие",
            }), 400

        if qty <= 0:
            return jsonify({
                "ok": False,
                "error": "Количество должно быть больше нуля",
            }), 400

        conn = get_db()

        maybe_finish_by_time(conn, room_id)

        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Комната не найдена",
            }), 404

        if room["status"] != "playing":
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Игра ещё не началась",
            }), 400

        if int(room["current_day"]) != current_day:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "День уже сменился, обновите игру",
            }), 409

        if player["finished_day"]:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Вы уже завершили день",
            }), 400

        game_data = load_json(room["game_data"], {})
        companies = game_data["companies"]
        price = companies[company_id]["price"]

        holdings = load_json(
            player["holdings"],
            make_holdings(),
        )

        day_orders = load_json(
            player["day_orders"],
            make_orders(),
        )

        day_actions = load_json(
            player["day_actions"],
            {},
        )

        cash = float(player["cash"])

        if day_actions.get(company_id):
            conn.close()

            return jsonify({
                "ok": False,
                "error": "По этой компании действие уже выбрано",
            }), 400

        # покупка акций
        if action == "buy":
            if cash < price * qty:
                conn.close()

                return jsonify({
                    "ok": False,
                    "error": "Недостаточно денег",
                }), 400

            cash -= price * qty
            holdings[company_id] += qty
            day_orders[company_id] += qty

        # продажа акций
        else:
            if holdings[company_id] < qty:
                conn.close()

                return jsonify({
                    "ok": False,
                    "error": "Недостаточно акций",
                }), 400

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

    # покупка инсайда
    @app.post("/api/rooms/<int:room_id>/insider")
    def buy_insider(room_id):
        user_id = require_user()

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Сначала войдите",
            }), 401

        data = request.get_json() or {}

        company_id = data.get("company_id")
        current_day = int(data.get("current_day") or 0)

        if company_id not in ["tnv", "olc", "hgn"]:
            return jsonify({
                "ok": False,
                "error": "Неизвестная компания",
            }), 400

        conn = get_db()

        maybe_finish_by_time(conn, room_id)

        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Комната не найдена",
            }), 404

        if room["status"] != "playing":
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Игра ещё не началась",
            }), 400

        if int(room["current_day"]) != current_day:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "День уже сменился, обновите игру",
            }), 409

        if player["finished_day"]:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Вы уже завершили день",
            }), 400

        if player["insider_used"]:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Сегодня инсайд уже куплен",
            }), 400

        cash = float(player["cash"])

        if cash < INSIDER_COST:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Недостаточно денег",
            }), 400

        game_data = load_json(room["game_data"], {})

        plan = game_data["plans"][company_id].get(
            str(room["current_day"])
        )

        direction = "neutral"

        if plan and plan["real_delta"] > 0:
            direction = "up"

        if plan and plan["real_delta"] < 0:
            direction = "down"

        insider_hints = load_json(
            player["insider_hints"],
            {},
        )

        insider_hints[company_id] = direction

        risk = int(player["risk"]) + INSIDER_RISK_ADD

        if risk > 100:
            risk = 100

        conn.execute(
            """
            UPDATE room_players
            SET cash = ?, risk = ?, insider_used = 1, insider_hints = ?
            WHERE id = ?
            """,
            (
                cash - INSIDER_COST,
                risk,
                dump_json(insider_hints),
                player["id"],
            ),
        )

        # текст подсказки
        if direction == "up":
            text = "⬆️ рост"
        elif direction == "down":
            text = "⬇️ падение"
        else:
            text = "➡️ нейтрально"

        push_event_for_player(
            conn,
            player["id"],
            "Инсайдерская информация",
            text,
            "warn",
        )

        conn.commit()

        state = build_state(conn, room_id, user_id)

        conn.close()

        return jsonify(state)

    # завершение дня
    @app.post("/api/rooms/<int:room_id>/finish-day")
    def finish_day(room_id):
        user_id = require_user()

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Сначала войдите",
            }), 401

        data = request.get_json() or {}

        current_day = int(data.get("current_day") or 0)

        conn = get_db()

        maybe_finish_by_time(conn, room_id)

        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Комната не найдена",
            }), 404

        if room["status"] != "playing":
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Игра ещё не началась",
            }), 400

        if int(room["current_day"]) != current_day:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "День уже сменился, обновите игру",
            }), 409

        if player["finished_day"]:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Вы уже завершили день",
            }), 400

        conn.execute(
            "UPDATE room_players SET finished_day = 1 WHERE id = ?",
            (player["id"],),
        )

        conn.commit()

        # если все завершили день, переходим дальше
        if all_players_finished(conn, room_id):
            advance_day(conn, room_id)

        state = build_state(conn, room_id, user_id)

        conn.close()

        return jsonify(state)

    # подтверждение события
    @app.post("/api/rooms/<int:room_id>/events/ack")
    def ack_event(room_id):
        user_id = require_user()

        if not user_id:
            return jsonify({
                "ok": False,
                "error": "Сначала войдите",
            }), 401

        conn = get_db()

        player = get_player_row(conn, room_id, user_id)

        if not player:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Комната не найдена",
            }), 404

        events = load_json(
            player["events"],
            [],
        )

        if events:
            events.pop(0)

        conn.execute(
            "UPDATE room_players SET events = ? WHERE id = ?",
            (
                dump_json(events),
                player["id"],
            ),
        )

        conn.commit()

        state = build_state(conn, room_id, user_id)

        conn.close()

        return jsonify(state)
