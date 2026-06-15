from flask import jsonify, request, session
from Database.database import get_db


# проверяем, вошёл ли пользователь
def require_user():

    # возвращаем id пользователя из session
    return session.get("user_id")


def register_auth_routes(app):

    # информация о текущем пользователе
    @app.get("/api/me")
    def me():

        # если пользователь не вошёл
        if not require_user():
            return jsonify({
                "ok": False,
                "error": "Сначала войдите"
            }), 401

        # отправляем данные пользователя
        return jsonify({
            "ok": True,
            "user": {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "current_room_id": session.get("room_id"),
            }
        })

    # регистрация
    @app.post("/api/register")
    def register():

        # получаем json с фронта
        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")

        # проверяем имя
        if not username:
            return jsonify({
                "ok": False,
                "error": "Введите имя"
            }), 400

        # проверяем пароль
        if not password:
            return jsonify({
                "ok": False,
                "error": "Введите пароль"
            }), 400

        conn = get_db()

        # ищем пользователя с таким именем
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        # если пользователь уже существует
        if user:
            conn.close()

            return jsonify({
                "ok": False,
                "error": "Такой пользователь уже есть"
            }), 400

        # создаём пользователя
        # password_hash используется как название поля,
        # но в проекте туда сохраняется обычный пароль
        result = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password)
        )

        conn.commit()
        conn.close()

        # сразу авторизуем пользователя
        session["user_id"] = result.lastrowid
        session["username"] = username

        return jsonify({
            "ok": True
        })

    # вход
    @app.post("/api/login")
    def login():

        # получаем json
        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")

        conn = get_db()

        # ищем пользователя
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        # если пользователь не найден
        if not user:
            return jsonify({
                "ok": False,
                "error": "Неверный логин или пароль"
            }), 401

        # проверяем пароль
        if user["password_hash"] != password:
            return jsonify({
                "ok": False,
                "error": "Неверный логин или пароль"
            }), 401

        # сохраняем пользователя в session
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return jsonify({
            "ok": True
        })
