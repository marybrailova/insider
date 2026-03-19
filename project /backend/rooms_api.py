from flask import jsonify, request, session

from auth_api import require_user
from config import START_CASH, dump_json, make_holdings, make_orders, make_room_code, now_seconds
from database import get_db
from game_engine import get_player_row, get_players_count, get_room, start_game_if_ready


def register_room_routes(app):
    @app.get("/api/rooms")
    def get_rooms():
        conn = get_db()
        rows = conn.execute(
            """
            SELECT r.id, r.title, r.max_players, r.join_code, r.status, r.room_type, COUNT(rp.user_id) AS players_count
            FROM rooms r
            LEFT JOIN room_players rp ON rp.room_id = r.id
            WHERE r.status != 'finished'
            GROUP BY r.id
            ORDER BY r.id DESC
            """
        ).fetchall()
        conn.close()

        rooms = []
        for row in rows:
            rooms.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "max_players": row["max_players"],
                    "players_count": row["players_count"],
                    "code": row["join_code"],
                    "status": row["status"],
                    "room_type": row["room_type"],
                }
            )

        return jsonify({"ok": True, "rooms": rooms})

    @app.post("/api/rooms")
    def create_room():
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        max_players = int(data.get("max_players") or 3)
        room_type = (data.get("room_type") or "private").strip()

        if not title:
            return jsonify({"ok": False, "error": "Введите название игры"}), 400

        if max_players < 2:
            return jsonify({"ok": False, "error": "Нужно минимум 2 игрока"}), 400

        if room_type not in ["public", "private"]:
            return jsonify({"ok": False, "error": "Неизвестный формат комнаты"}), 400

        conn = get_db()
        room_code = make_room_code() if room_type == "private" else ""
        cur = conn.execute(
            """
            INSERT INTO rooms (title, max_players, host_user_id, status, current_day, turn_ends_at, game_data, join_code, created_at, room_type)
            VALUES (?, ?, ?, 'waiting', 0, 0, '{}', ?, ?, ?)
            """,
            (title, max_players, user_id, room_code, now_seconds(), room_type),
        )
        room_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO room_players (room_id, user_id, cash, risk, holdings, day_orders, day_actions, insider_used, insider_hints, finished_day, events)
            VALUES (?, ?, ?, 0, ?, ?, ?, 0, ?, 0, '[]')
            """,
            (
                room_id,
                user_id,
                START_CASH,
                dump_json(make_holdings()),
                dump_json(make_orders()),
                dump_json({}),
                dump_json({}),
            ),
        )
        conn.commit()
        conn.close()

        session["room_id"] = room_id
        return jsonify({"ok": True, "room_id": room_id, "code": room_code, "room_type": room_type})

    @app.post("/api/rooms/<int:room_id>/join")
    def join_room(room_id):
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        conn = get_db()
        room = get_room(conn, room_id)
        if not room:
            conn.close()
            return jsonify({"ok": False, "error": "Комната не найдена"}), 404

        if room["room_type"] != "public":
            conn.close()
            return jsonify({"ok": False, "error": "В эту комнату нужно входить по коду"}), 400

        if room["status"] == "finished":
            conn.close()
            return jsonify({"ok": False, "error": "Игра уже завершена"}), 400

        existing = get_player_row(conn, room_id, user_id)
        if not existing:
            players_count = get_players_count(conn, room_id)
            if players_count >= room["max_players"]:
                conn.close()
                return jsonify({"ok": False, "error": "Комната заполнена"}), 400

            conn.execute(
                """
                INSERT INTO room_players (room_id, user_id, cash, risk, holdings, day_orders, day_actions, insider_used, insider_hints, finished_day, events)
                VALUES (?, ?, ?, 0, ?, ?, ?, 0, ?, 0, '[]')
                """,
                (
                    room_id,
                    user_id,
                    START_CASH,
                    dump_json(make_holdings()),
                    dump_json(make_orders()),
                    dump_json({}),
                    dump_json({}),
                ),
            )
            conn.commit()

        start_game_if_ready(conn, room_id)
        conn.commit()
        conn.close()

        session["room_id"] = room_id
        return jsonify({"ok": True})

    @app.post("/api/rooms/join-by-code")
    def join_room_by_code():
        user_id = require_user()
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401

        data = request.get_json(silent=True) or {}
        code = (data.get("code") or "").strip().upper()

        if not code:
            return jsonify({"ok": False, "error": "Введите код комнаты"}), 400

        conn = get_db()
        room = conn.execute(
            "SELECT * FROM rooms WHERE join_code = ?",
            (code,),
        ).fetchone()
        if not room:
            conn.close()
            return jsonify({"ok": False, "error": "Комната с таким кодом не найдена"}), 404

        room_id = room["id"]

        if room["room_type"] != "private":
            conn.close()
            return jsonify({"ok": False, "error": "По коду можно войти только в частную комнату"}), 400

        if room["status"] == "finished":
            conn.close()
            return jsonify({"ok": False, "error": "Игра уже завершена"}), 400

        existing = get_player_row(conn, room_id, user_id)
        if not existing:
            players_count = get_players_count(conn, room_id)
            if players_count >= room["max_players"]:
                conn.close()
                return jsonify({"ok": False, "error": "Комната уже заполнена"}), 400

            conn.execute(
                """
                INSERT INTO room_players (room_id, user_id, cash, risk, holdings, day_orders, day_actions, insider_used, insider_hints, finished_day, events)
                VALUES (?, ?, ?, 0, ?, ?, ?, 0, ?, 0, '[]')
                """,
                (
                    room_id,
                    user_id,
                    START_CASH,
                    dump_json(make_holdings()),
                    dump_json(make_orders()),
                    dump_json({}),
                    dump_json({}),
                ),
            )
            conn.commit()

        start_game_if_ready(conn, room_id)
        conn.commit()
        conn.close()

        session["room_id"] = room_id
        return jsonify({"ok": True, "room_id": room_id})
