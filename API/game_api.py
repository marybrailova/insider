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


def register_game_routes(app):

    # получение текущего состояния игры
    @app.get("/api/rooms/<int:room_id>/state")
    def room_state(room_id):

        user_id = require_user()

        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        conn = get_db()

        # собираем состояние комнаты для игрока
        state = build_state(conn, room_id, user_id)

        conn.close()

        if not state:
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        return jsonify(state)

    # покупка или продажа акций
    @app.post("/api/rooms/<int:room_id>/trade")
    def trade(room_id):

        user_id = require_user()

        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json() or {}

        company_id = data.get("company_id")
        action = data.get("action")
        qty = int(data.get("qty") or 0)
        current_day = int(data.get("current_day") or 0)

        # проверяем компанию
        if company_id not in ["tnv", "olc", "hgn"]:
            return jsonify({"ok": False, "error": "Неизвестная компания"}), 400

        # проверяем действие
        if action not in ["buy", "sell"]:
            return jsonify({"ok": False, "error": "Неизвестное действие"}), 400

        # количество должно быть положительным
        if qty <= 0:
            return jsonify({"ok": False, "error": "Количество должно быть больше нуля"}), 400

        conn = get_db()

        # если время хода вышло, сервер сам завершит день
        maybe_finish_by_time(conn, room_id)

        room = get_room(conn, room_id)
        player = get_player_row(conn, room_id, user_id)

        if not room or not player:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        if room["status"] != "playing":
            conn.close()
            return jsonify({"ok": False, "error": "Игра ещё не началась"}), 400

        # защита от действия в старом дне
        if int(room["current_day"]) != current_day:
            conn.close()
            return jsonify({"ok": False, "error": "День уже сменился, обновите игру"}), 409

        if player["finished_day"]:
            conn.close()
            return jsonify({"ok": False, "error": "Вы уже завершили день"}), 400

        game_data = load_json(room["game_data"], {})
        companies = game_data["companies"]

        # текущая цена акции
        price = companies[company_id]["price"]

        # данные игрока
        holdings = load_json(player["holdings"], make_holdings())
        day_orders = load_json(player["day_orders"], make_orders())
        day_actions = load_json(player["day_actions"], {})
        cash = float(player["cash"])

        # за день по одной компании можно сделать только одно действие
        if day_actions.get(company_id):
            conn.close()
            return jsonify({"ok": False, "error": "По этой компании действие уже выбрано"}), 400

        if action == "buy":

            # проверка денег
            if cash < price * qty:
                conn.close()
                return jsonify({"ok": False, "error": "Недостаточно денег"}), 400

            cash -= price * qty
            holdings[company_id] += qty
            day_orders[company_id] += qty

        else:

            # проверка акций
            if holdings[company_id] < qty:
                conn.close()
                return jsonify({"ok": False, "error": "Недостаточно акций"}), 400

            cash += price * qty
            holdings[company_id] -= qty
            day_orders[company_id] -= qty

        # запоминаем действие по компании
        day_actions[company_id] = action

        # обновляем игрока в базе
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
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json() or {}

        company_id = data.get("company_id")
        current_day = int(data.get("current_day") or 0)

        if company_id not in ["tnv", "olc", "hgn"]:
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

        if int(room["current_day"]) != current_day:
            conn.close()
            return jsonify({"ok": False, "error": "День уже сменился, обновите игру"}), 409

        if player["finished_day"]:
            conn.close()
            return jsonify({"ok": False, "error": "Вы уже завершили день"}), 400

        # в день можно купить только один инсайд
        if player["insider_used"]:
            conn.close()
            return jsonify({"ok": False, "error": "Сегодня инсайд уже куплен"}), 400

        cash = float(player["cash"])

        # проверка денег на инсайд
        if cash < INSIDER_COST:
            conn.close()
            return jsonify({"ok": False, "error": "Недостаточно денег"}), 400

        game_data = load_json(room["game_data"], {})

        # смотрим план движения компании
        plan = game_data["plans"][company_id].get(str(room["current_day"]))

        direction = "neutral"

        if plan and plan["real_delta"] > 0:
            direction = "up"

        if plan and plan["real_delta"] < 0:
            direction = "down"

        insider_hints = load_json(player["insider_hints"], {})
        insider_hints[company_id] = direction

        # увеличиваем риск на 10
        risk = int(player["risk"]) + INSIDER_RISK_ADD

        if risk > 100:
            risk = 100

        # списываем деньги и сохраняем инсайд
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

        # текст для модального окна
        if direction == "up":
            text = "⬆️ рост"
        elif direction == "down":
            text = "⬇️ падение"
        else:
            text = "➡️ нейтрально"

        # добавляем событие игроку
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

    # завершение дня игроком
    @app.post("/api/rooms/<int:room_id>/finish-day")
    def finish_day(room_id):

        user_id = require_user()

        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json() or {}

        current_day = int(data.get("current_day") or 0)

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

        if int(room["current_day"]) != current_day:
            conn.close()
            return jsonify({"ok": False, "error": "День уже сменился, обновите игру"}), 409

        if player["finished_day"]:
            conn.close()
            return jsonify({"ok": False, "error": "Вы уже завершили день"}), 400

        # отмечаем, что игрок закончил ход
        conn.execute(
            "UPDATE room_players SET finished_day = 1 WHERE id = ?",
            (player["id"],),
        )

        conn.commit()

        # если все игроки завершили день,
        # переходим к следующему дню
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
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        conn = get_db()

        player = get_player_row(conn, room_id, user_id)

        if not player:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        events = load_json(player["events"], [])

        # удаляем первое событие
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
