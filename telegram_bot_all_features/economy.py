from datetime import datetime, timedelta

# User structure:
# {
#   "xp": int,
#   "balance": float,
#   "premium_until": datetime or None,
#   "last_daily": datetime or None
# }

user_data = {}

def get_user(user_id: int):
    if user_id not in user_data:
        user_data[user_id] = {
            "xp": 0,
            "balance": 0.0,
            "premium_until": None,
            "last_daily": None
        }
    return user_data[user_id]

# XP and Level
def add_xp(user_id: int, amount: int):
    user = get_user(user_id)
    user["xp"] += amount

def get_level(xp: int):
    level = 1
    required = 100
    total = 0
    while xp >= total + required:
        total += required
        required += 50
        level += 1
    return level

# Balance
def add_balance(user_id: int, amount: float):
    user = get_user(user_id)
    user["balance"] += round(amount, 2)

def get_balance(user_id: int):
    return round(get_user(user_id)["balance"], 2)

# Premium
def is_premium(user_id: int):
    user = get_user(user_id)
    return user["premium_until"] and user["premium_until"] > datetime.now()

def premium_time_left(user_id: int):
    user = get_user(user_id)
    if not user["premium_until"]:
        return None
    remaining = user["premium_until"] - datetime.now()
    if remaining.total_seconds() <= 0:
        return None
    return remaining

def try_upgrade_to_premium(user_id: int):
    user = get_user(user_id)
    cost = 1.5
    if user["balance"] >= cost:
        user["balance"] -= cost
        user["premium_until"] = datetime.now() + timedelta(days=1)
        return True
    return False

# Daily Reward
def claim_daily(user_id: int):
    user = get_user(user_id)
    now = datetime.now()
    if user["last_daily"] and (now - user["last_daily"]) < timedelta(hours=24):
        return False
    user["last_daily"] = now
    add_xp(user_id, 10)
    add_balance(user_id, 0.25)
    return True

def time_until_next_daily(user_id: int):
    user = get_user(user_id)
    if not user["last_daily"]:
        return None
    delta = datetime.now() - user["last_daily"]
    if delta >= timedelta(hours=24):
        return None
    remaining = timedelta(hours=24) - delta
    return remaining

# Optional: Get full user status (for /profile command)
def get_user_status(user_id: int):
    user = get_user(user_id)
    level = get_level(user["xp"])
    premium_left = premium_time_left(user_id)
    return {
        "xp": user["xp"],
        "level": level,
        "balance": round(user["balance"], 2),
        "is_premium": is_premium(user_id),
        "premium_left": premium_left,
        "next_daily_in": time_until_next_daily(user_id)
    }
