from flask import Flask, send_from_directory
from auth_api import register_auth_routes
from config import FRONT_DIR
from database import init_db
from game_api import register_game_routes
from rooms_api import register_room_routes

app = Flask(__name__)
app.secret_key = "dev-secret-key"

@app.route("/")
def index():
    return send_from_directory(FRONT_DIR, "welcome.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONT_DIR, filename)

register_auth_routes(app)

register_room_routes(app)

register_game_routes(app)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
