# economy.py
from datetime import datetime, timedelta

# Պահպանում ենք օգտատերերի XP, բալանս և պրեմիում կարգավիճակ
user_data = {}  # Format: { user_id: { "xp": 0, "balance": 0.0, "premium_until": None, "last_daily": None } }

def get_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "xp": 0,
            "balance": 0.0,
            "premium_until": None,
            "last_daily": None
        }
    return user_data[user_id]

def add_xp(user_id, amount):
    user = get_user(user_id)
    user["xp"] += amount

def add_balance(user_id, amount):
    user = get_user(user_id)
    user["balance"] += round(amount, 2)

def get_balance(user_id):
    return get_user(user_id)["balance"]

def is_premium(user_id):
    user = get_user(user_id)
    until = user.get("premium_until")
    if until and until > datetime.now():
        return True
    return False

def try_upgrade_to_premium(user_id):
    user = get_user(user_id)
    if user["balance"] >= 1.5:
        user["balance"] -= 1.5
        user["premium_until"] = datetime.now() + timedelta(days=1)
        return True
    return False

def claim_daily(user_id):
    user = get_user(user_id)
    now = datetime.now()
    if user["last_daily"] and (now - user["last_daily"]).days < 1:
        return False
    user["last_daily"] = now
    user["xp"] += 10
    user["balance"] += 0.25
    return True
