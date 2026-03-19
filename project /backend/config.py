from pathlib import Path
import json
import random
import string
import time

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
FRONT_DIR = BASE_DIR.parent / "frontend"
TOTAL_DAYS = 10
TURN_SECONDS = 60
START_CASH = 2000
START_PRICE = 100
START_REAL = 100
INSIDER_COST = 50
INSIDER_RISK_ADD = 10
MAX_RISK = 100
PENALTY_RATE = 0.2
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
COMPANY_BY_ID = {company["id"]: company for company in COMPANIES}

def load_json(text, default_value):
    if not text:
        return default_value
    try:
        return json.loads(text)
    except Exception:
        return default_value

def dump_json(value):
    return json.dumps(value, ensure_ascii=False)

def now_seconds():
    return int(time.time())

def make_room_code():
    letters = string.ascii_uppercase + string.digits
    return "".join(random.choice(letters) for _ in range(5))

def clamp(value, min_value, max_value):
    return min(max(value, min_value), max_value)

def make_holdings():
    data = {}
    for company in COMPANIES:
        data[company["id"]] = 0
    return data

def make_orders():
    data = {}
    for company in COMPANIES:
        data[company["id"]] = 0
    return data

def make_company_state():
    data = {}
    for company in COMPANIES:
        data[company["id"]] = {
            "price": START_PRICE,
            "real_value": START_REAL,
            "history": [START_PRICE],
            "info": None,
            "heat_days": 0,
        }
    return data

def random_direction():
    roll = random.random()
    if roll < 0.4:
        return "up"
    if roll < 0.8:
        return "down"
    return "neutral"

def create_info(company):
    is_news = random.random() < company["newsChance"]
    direction = random_direction()
    if is_news:
        return {
            "type": "news",
            "direction": direction,
            "truth": True,
        }
    truth = random.random() < company["rumorTruth"]
    return {
        "type": "rumor",
        "direction": direction,
        "truth": truth,
    }

def calc_real_delta(info):
    if not info or info["direction"] == "neutral":
        return 0
    sign = 1 if info["direction"] == "up" else -1
    if info["type"] == "news":
        return 0.1 * sign
    if info["truth"]:
        return 0.1 * sign
    return -0.1 * sign

def make_plans():
    plans = {}
    for company in COMPANIES:
        plans[company["id"]] = {}
        for day in range(1, TOTAL_DAYS + 1):
            info = create_info(company)
            plans[company["id"]][str(day)] = {
                "info": info,
                "real_delta": calc_real_delta(info),
            }
    return plans

def make_game_data():
    return {
        "companies": make_company_state(),
        "plans": make_plans(),
    }

def direction_text(direction):
    if direction == "up":
        return "⬆️ рост"
    if direction == "down":
        return "⬇️ падение"
    return "➡️ нейтрально"

def info_label(info):
    if not info:
        return "—"
    start = "Новость" if info["type"] == "news" else "Слух"
    return f"{start}: {direction_text(info['direction'])}"

def get_player_capital(cash, holdings, companies):
    total = float(cash)
    for company in COMPANIES:
        company_id = company["id"]
        total += holdings.get(company_id, 0) * companies[company_id]["price"]
    return total
