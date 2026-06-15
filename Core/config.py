import json
import random
import string
import time

# колво игровых дней
TOTAL_DAYS = 10

# длительность одного дня в секундах
TURN_SECONDS = 60

# стартовый баланс игрока
START_CASH = 2000

# стартовая цена акции
START_PRICE = 100

# стартовая реальная стоимость компании
START_REAL = 100

# стоимость покупки инсайда
INSIDER_COST = 50

# насколько растёт риск после покупки инсайда
INSIDER_RISK_ADD = 10

# максимальный риск проверки
MAX_RISK = 100

# штраф при поимке 10% капитала
PENALTY_RATE = 0.1

# список компаний в игре, в словаре 
COMPANIES = [
    {"id": "tnv", "name": "TechNova", "ticker": "TNV", "sector": "технологии", "newsChance": 0.25, "rumorTruth": 0.60, "icon": "🖥️"},
    {"id": "olc", "name": "OilCore", "ticker": "OLC", "sector": "нефтянка", "newsChance": 0.45, "rumorTruth": 0.65, "icon": "💧"},
    {"id": "hgn", "name": "HealthGen", "ticker": "HGN", "sector": "фарма", "newsChance": 0.30, "rumorTruth": 0.55, "icon": "💊"},
]


# быстрый доступ к компании по id, в словаре 
COMPANY_BY_ID = {
    "tnv": COMPANIES[0],
    "olc": COMPANIES[1],
    "hgn": COMPANIES[2],
}


# безопасно превращаем JSON строку из базы данных обратно в Python объект
# если JSON сломан или пустой, возвращаем default_value {}
# чтобы сервер не упал с ошибкой
def load_json(text, default_value):
    try:
        return json.loads(text)
    except:
        return default_value


# превращаем Python объект в JSON строку для SQLite
# ensure_ascii=False нужен для нормального русского текста
def dump_json(value):
    return json.dumps(value, ensure_ascii=False)


# возвращаем текущее время в секундах
# используется для таймера и проверки окончания хода
def now_seconds():
    return int(time.time())


# создаём код комнаты из 5 символов
# string.ascii_uppercase все большие английские буквы A-Z
# string.digits все цифры 0-9
# random.choice — выбираем один случайный символ из этого набора

def make_room_code():
    code = ""

    for i in range(5):
        code += random.choice(string.ascii_uppercase + string.digits)

    return code


# ограничиваем число снизу и сверху
# эту штуку прописала на всякий случай, чтобы значение не выходило за допустимые
# пока она у меня не используется, но если менять правила, пригодится 
def clamp(value, min_value, max_value):
    if value < min_value:
        return min_value

    if value > max_value:
        return max_value

    return value


# начальное количество акций у игрока, в словаре 
def make_holdings():
    return {
        "tnv": 0,
        "olc": 0,
        "hgn": 0,
    }


# начальные заявки игрока за день, в словаре 
def make_orders():
    return {
        "tnv": 0,
        "olc": 0,
        "hgn": 0,
    }


# стартовое состояние компаний, в словаре 
def make_company_state():

    return {

        "tnv": {

            # текущая рыночная цена акции
            # START_PRICE = 100
            "price": START_PRICE,

            # настоящая внутренняя стоимость компании
            # START_REAL = 100
            "real_value": START_REAL,

            # history — история цен компании
            # [START_PRICE] означает
            # в начале история содержит только цену 100
            "history": [START_PRICE],

            # info — текущая новость или слух
            # None означает
            # сейчас информации нет
            "info": None,

            # heat_days — сколько дней компания перегрета
            # пока перегрева нет
            "heat_days": 0,
        },

        # OilCore
        "olc": {
            "price": START_PRICE,
            "real_value": START_REAL,
            "history": [START_PRICE],
            "info": None,
            "heat_days": 0,
        },

        # HealthGen
        "hgn": {
            "price": START_PRICE,
            "real_value": START_REAL,
            "history": [START_PRICE],
            "info": None,
            "heat_days": 0,
        },
    }

# случайное направление новости или слуха
def random_direction():

    # random.random() создаёт случайное число
    # от 0 до 1
    
    x = random.random()
    # вероятность 40%
    
    if x < 0.4:
        return "up"
    
    # тоже вероятность 40%
    if x < 0.8:
        return "down"
    
    # вероятность 20%
    return "neutral"


# создаём новость или слух для компании
def create_info(company):
    # random.random() создаёт случайное число от 0 до 1
    # с вероятностью newsChance появляется новость
    if random.random() < company["newsChance"]:
        return {
            # news = настоящая новость
            "type": "news",
            # random_direction() создаёт его случайно
            "direction": random_direction(),
            # настоящая новость всегда правдивая
            "truth": True,
        }

    # иначе появляется слух
    return {
        # rumor = слух
        "type": "rumor",
        # случайное направление слуха
        "direction": random_direction(),
        # правда ли слух
        "truth": random.random() < company["rumorTruth"],
    }


# считаем, как информация влияет на реальную стоимость
def calc_real_delta(info):

    # если информации нет
    if not info:
        return 0

    # нейтральная информация ничего не меняет
    if info["direction"] == "neutral":
        return 0

    # рост даёт +10%, падение даёт -10%
    if info["direction"] == "up":
        sign = 1
    else:
        sign = -1

    # новость всегда правдивая
    if info["type"] == "news":
        return 0.1 * sign

    # правдивый слух работает как указано
    if info["truth"]:
        return 0.1 * sign

    # ложный слух работает наоборот
    return -0.1 * sign


# заранее создаём план новостей и слухов на все дни
def make_plans():
    plans = {}
    # c — текущая компания
    for c in COMPANIES:
        plans[c["id"]] = {}

        for day in range(1, TOTAL_DAYS + 1):
            # создаёт случайную новость или слух
            info = create_info(c)
            # превращаем число в строку
            plans[c["id"]][str(day)] = {
                # сама новость или слух
                "info": info,
                # насколько изменится real_value
                "real_delta": calc_real_delta(info),
            }

    return plans


# создаём стартовые данные игры
def make_game_data():
    return {
        # companies — текущее состояние компаний
        "companies": make_company_state(),
        # plans — заранее созданный план
        "plans": make_plans(),
    }


# текстовое обозначение направления
def direction_text(direction):
    if direction == "up":
        return "⬆️ рост"

    if direction == "down":
        return "⬇️ падение"

    return "➡️ нейтрально"


# подпись новости или слуха для интерфейса
def info_label(info):
    if not info:
        return "—"

    if info["type"] == "news":
        return "Новость: " + direction_text(info["direction"])

    return "Слух: " + direction_text(info["direction"])


# считаем капитал игрока
# деньги + стоимость всех акций
def get_player_capital(cash, holdings, companies):
    # сначала капитал = просто деньги
    total = float(cash)
    # holdings.get("tnv", 0)

# берём количество акций TNV у игрока
# если ключа "tnv" нет — берём 0
# companies["tnv"]["price"]
# текущая цена акции TNV
    
    total += holdings.get("tnv", 0) * companies["tnv"]["price"]
    total += holdings.get("olc", 0) * companies["olc"]["price"]
    total += holdings.get("hgn", 0) * companies["hgn"]["price"]

    return total