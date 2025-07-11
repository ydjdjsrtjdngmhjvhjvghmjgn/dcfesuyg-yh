from telegram import Update
from telegram.ext import ContextTypes
from xp import user_xp

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard = sorted(user_xp.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    text = "🏆 Top Users:\n"
    for idx, (uid, data) in enumerate(leaderboard, 1):
        text += f"{idx}. User {uid} - XP: {data['xp']}\n"
    await update.message.reply_text(text)
