from flask import Flask, send_from_directory

from API.auth_api import register_auth_routes
from API.game_api import register_game_routes
from API.rooms_api import register_room_routes
from Database.database import init_db


app = Flask(__name__)
app.secret_key = "123"


@app.route("/")
def index():
    return send_from_directory("HTML", "welcome.html")


@app.route("/<path:path>")
def static_files(path):
    if path.endswith(".html"):
        return send_from_directory("HTML", path)

    if path.endswith(".css"):
        return send_from_directory("CSS", path)

    if path.endswith(".js"):
        return send_from_directory("JavaScript", path)

    return send_from_directory(".", path)


register_auth_routes(app)
register_room_routes(app)
register_game_routes(app)

init_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
