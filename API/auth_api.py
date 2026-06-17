from flask import jsonify, request, session

from Database.database import get_db


# получаем текущего пользователя
def require_user():
    return session.get("user_id")


# регистрируем маршруты авторизации
def register_auth_routes(app):

    # текущий пользователь
    @app.get("/api/me")
    def me():
        if not session.get("user_id"):
            return jsonify({
                "ok": False,
                "error": "Сначала войдите",
            }), 401

        return jsonify({
            "ok": True,
            "user": {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "current_room_id": session.get("room_id"),
            },
        })

    # выход
    @app.post("/api/logout")
    def logout():
        session.clear()

        return jsonify({
            "ok": True,
        })

    # регистрация
    @app.post("/api/register")
    def register():
        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username:
            return jsonify({
                "ok": False,
                "error": "Введите имя",
            }), 400

        if not password:
            return jsonify({
                "ok": False,
                "error": "Введите пароль",
            }), 400

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Такой пользователь уже есть",
            }), 400

        result = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password),
        )

        conn.commit()
        conn.close()

        session["user_id"] = result.lastrowid
        session["username"] = username

        return jsonify({
            "ok": True,
        })

    # вход
    @app.post("/api/login")
    def login():
        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        conn.close()

        if not user:
            return jsonify({
                "ok": False,
                "error": "Неверный логин или пароль",
            }), 401

        if user["password_hash"] != password:
            return jsonify({
                "ok": False,
                "error": "Неверный логин или пароль",
            }), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return jsonify({
            "ok": True,
        })
