from flask import Flask, send_from_directory
from API.auth_api import register_auth_routes
from Database.database import DB_PATH, init_db
from API.game_api import register_game_routes
from API.rooms_api import register_room_routes


# создаём Flask приложение
app = Flask(__name__)


# secret_key нужен для session
# хранения id пользователя и комнаты
app.secret_key = "123"


# главная страница сайта
@app.route("/")
def index():

    # открываем welcome.html
    return send_from_directory("HTML", "welcome.html")


# маршрут для всех остальных файлов
# css / js / html
@app.route("/<path:path>")
def static_files(path):

    # отдаём файлы из соответствующих папок
    if path.endswith(".html"):
        return send_from_directory("HTML", path)

    if path.endswith(".css"):
        return send_from_directory("CSS", path)

    if path.endswith(".js"):
        return send_from_directory("JavaScript", path)

    return send_from_directory(".", path)


# подключаем api маршруты авторизации
register_auth_routes(app)

# подключаем api маршруты комнат
register_room_routes(app)

# подключаем api маршруты игры
register_game_routes(app)


# создаём таблицы базы данных
init_db()


# запуск Flask сервера
if __name__ == "__main__":

    # запуск сервера
    app.run(debug=True, port=5001)
