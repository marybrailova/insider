from flask import jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db

def require_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return user_id

def register_auth_routes(app):
    @app.get("/api/me")
    def me():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Сначала войдите"}), 401
        return jsonify(
            {
                "ok": True,
                "user": {
                    "id": user_id,
                    "username": session.get("username"),
                    "current_room_id": session.get("room_id"),
                },
            }
        )
    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})
    @app.post("/api/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if len(username) < 3:
            return jsonify({"ok": False, "error": "Имя слишком короткое"}), 400
        if len(password) < 4:
            return jsonify({"ok": False, "error": "Пароль слишком короткий"}), 400
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            conn.commit()
        except Exception:
            conn.close()
            return jsonify({"ok": False, "error": "Такой пользователь уже есть"}), 409
        conn.close()
        return jsonify({"ok": True})
    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if not user:
            return jsonify({"ok": False, "error": "Неверный логин или пароль"}), 401
        if not check_password_hash(user["password_hash"], password):
            return jsonify({"ok": False, "error": "Неверный логин или пароль"}), 401
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"ok": True})
