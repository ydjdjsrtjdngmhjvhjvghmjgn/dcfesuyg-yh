from telegram import Update
from telegram.ext import ContextTypes
import random

user_xp = {}

def add_xp(user_id, amount=10):
    if user_id not in user_xp:
        user_xp[user_id] = {"xp": 0, "level": 1}
    user_xp[user_id]["xp"] += amount
    xp = user_xp[user_id]["xp"]
    level = xp // 100 + 1
    user_xp[user_id]["level"] = level

async def xp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_xp(user_id)
    data = user_xp[user_id]
    await update.message.reply_text(f"🧬 Your Level: {data['level']}\n⚡ XP: {data['xp']}")