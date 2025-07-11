
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

daily_data = {}

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now()

    if user_id in daily_data and now - daily_data[user_id] < timedelta(hours=24):
        await update.message.reply_text("⏳ You already claimed your daily reward. Try again later.")
        return

    daily_data[user_id] = now
    await update.message.reply_text("🎁 You received your daily bonus: +50 XP!")
    try:
        from xp import add_xp
        add_xp(user_id, 50)
    except:
        pass
