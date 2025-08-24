import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

# ====== Constants ======
DAILY_FILE = 'daily_data.json'
BASE_XP = 50
BASE_COINS = 20

# ====== In-Memory XP & Coins Storage (demo version) ======
user_xp = {}
user_coins = {}

def add_xp(user_id, amount):
    user_xp[user_id] = user_xp.get(user_id, 0) + amount
    print(f"[XP] ➕ {amount} XP -> User {user_id} | Total: {user_xp[user_id]}")

def add_coins(user_id, amount):
    user_coins[user_id] = user_coins.get(user_id, 0) + amount
    print(f"[Coins] 💰 +{amount} -> User {user_id} | Total: {user_coins[user_id]}")
# ===========================================================

# ====== Load & Save Daily Data ======
def load_daily_data():
    if not os.path.exists(DAILY_FILE):
        return {}
    with open(DAILY_FILE, 'r') as f:
        raw = json.load(f)
        return {
            int(uid): {
                'last_claim': datetime.fromisoformat(data['last_claim']),
                'streak': data.get('streak', 0)
            }
            for uid, data in raw.items()
        }

def save_daily_data(data):
    with open(DAILY_FILE, 'w') as f:
        json.dump({
            str(uid): {
                'last_claim': info['last_claim'].isoformat(),
                'streak': info['streak']
            }
            for uid, info in data.items()
        }, f, indent=2)
# ====================================

# Load data once at the top
daily_data = load_daily_data()

# ====== Main Daily Command ======
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    now = datetime.now()

    user = daily_data.get(user_id, {
        'last_claim': now - timedelta(days=2),
        'streak': 0
    })

    # Check if already claimed today
    if now - user['last_claim'] < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - user['last_claim'])
        hours, minutes = divmod(int(remaining.total_seconds()) // 60, 60)
        await update.message.reply_text(
            f"⏳ {username}, you've already claimed your daily bonus.\n"
            f"⏰ Try again in {hours}h {minutes}m."
        )
        return

    # Update streak
    if now.date() == (user['last_claim'] + timedelta(days=1)).date():
        user['streak'] += 1
    else:
        user['streak'] = 1

    # Calculate rewards
    bonus_xp = BASE_XP + (user['streak'] - 1) * 10
    bonus_coins = BASE_COINS + (user['streak'] - 1) * 5

    # Apply rewards
    add_xp(user_id, bonus_xp)
    add_coins(user_id, bonus_coins)

    # Save updated data
    user['last_claim'] = now
    daily_data[user_id] = user
    save_daily_data(daily_data)

    # Send response
    await update.message.reply_text(
        f"🎉 Congrats, {username}!\n"
        f"🔥 Streak: {user['streak']} day(s)\n"
        f"➕ XP: {bonus_xp}\n"
        f"💰 Coins: {bonus_coins}\n"
        f"Come back tomorrow to keep your streak going!"
    )
# ==================================
