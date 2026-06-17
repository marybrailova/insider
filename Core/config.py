import json
import random
import string
import time


# настройки игры
TOTAL_DAYS = 10
TURN_SECONDS = 60

START_CASH = 2000
START_PRICE = 100
START_REAL = 100

INSIDER_COST = 50
INSIDER_RISK_ADD = 10
MAX_RISK = 100
PENALTY_RATE = 0.1


# компании
COMPANIES = [
    {
        "id": "tnv",
        "name": "TechNova",
        "ticker": "TNV",
        "sector": "технологии",
        "newsChance": 0.25,
        "rumorTruth": 0.60,
        "icon": "🖥️",
    },
    {
        "id": "olc",
        "name": "OilCore",
        "ticker": "OLC",
        "sector": "нефтянка",
        "newsChance": 0.45,
        "rumorTruth": 0.65,
        "icon": "💧",
    },
    {
        "id": "hgn",
        "name": "HealthGen",
        "ticker": "HGN",
        "sector": "фарма",
        "newsChance": 0.30,
        "rumorTruth": 0.55,
        "icon": "💊",
    },
]


COMPANY_BY_ID = {
    "tnv": COMPANIES[0],
    "olc": COMPANIES[1],
    "hgn": COMPANIES[2],
}


# читаем json
def load_json(text, default_value):
    try:
        return json.loads(text)
    except:
        return default_value


# сохраняем json
def dump_json(value):
    return json.dumps(value, ensure_ascii=False)


# текущее время
def now_seconds():
    return int(time.time())


# код комнаты
def make_room_code():
    code = ""

    for i in range(5):
        code += random.choice(string.ascii_uppercase + string.digits)

    return code


# ограничиваем значение
def clamp(value, min_value, max_value):
    if value < min_value:
        return min_value

    if value > max_value:
        return max_value

    return value


# стартовые акции
def make_holdings():
    return {
        "tnv": 0,
        "olc": 0,
        "hgn": 0,
    }


# заявки за день
def make_orders():
    return {
        "tnv": 0,
        "olc": 0,
        "hgn": 0,
    }


# состояние компаний
def make_company_state():
    return {
        "tnv": {
            "price": START_PRICE,
            "real_value": START_REAL,
            "history": [START_PRICE],
            "info": None,
            "heat_days": 0,
        },
        "olc": {
            "price": START_PRICE,
            "real_value": START_REAL,
            "history": [START_PRICE],
            "info": None,
            "heat_days": 0,
        },
        "hgn": {
            "price": START_PRICE,
            "real_value": START_REAL,
            "history": [START_PRICE],
            "info": None,
            "heat_days": 0,
        },
    }


# случайное направление новости
def random_direction():
    x = random.random()

    if x < 0.4:
        return "up"

    if x < 0.8:
        return "down"

    return "neutral"


# создаём новость или слух
def create_info(company):
    if random.random() < company["newsChance"]:
        return {
            "type": "news",
            "direction": random_direction(),
            "truth": True,
        }

    return {
        "type": "rumor",
        "direction": random_direction(),
        "truth": random.random() < company["rumorTruth"],
    }


# реальное изменение цены
def calc_real_delta(info):
    if not info:
        return 0

    if info["direction"] == "neutral":
        return 0

    if info["direction"] == "up":
        sign = 1
    else:
        sign = -1

    if info["type"] == "news":
        return 0.1 * sign

    if info["truth"]:
        return 0.1 * sign

    return -0.1 * sign


# планы новостей на игру
def make_plans():
    plans = {}

    for c in COMPANIES:
        plans[c["id"]] = {}

        for day in range(1, TOTAL_DAYS + 1):
            info = create_info(c)

            plans[c["id"]][str(day)] = {
                "info": info,
                "real_delta": calc_real_delta(info),
            }

    return plans


# данные новой игры
def make_game_data():
    return {
        "companies": make_company_state(),
        "plans": make_plans(),
    }


# текст направления
def direction_text(direction):
    if direction == "up":
        return "⬆️ рост"

    if direction == "down":
        return "⬇️ падение"

    return "➡️ нейтрально"


# подпись новости
def info_label(info):
    if not info:
        return "—"

    if info["type"] == "news":
        return "Новость: " + direction_text(info["direction"])

    return "Слух: " + direction_text(info["direction"])


# считаем капитал игрока
def get_player_capital(cash, holdings, companies):
    total = float(cash)

    total += holdings.get("tnv", 0) * companies["tnv"]["price"]
    total += holdings.get("olc", 0) * companies["olc"]["price"]
    total += holdings.get("hgn", 0) * companies["hgn"]["price"]

    return total