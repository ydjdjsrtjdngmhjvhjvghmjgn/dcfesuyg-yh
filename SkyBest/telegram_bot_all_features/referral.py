from telegram import Update
from telegram.ext import ContextTypes

referrals = {}

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    code = str(user.id)
    bot_username = context.bot.username
    await update.message.reply_text(
        f"📣 Invite friends using your referral link:\nhttps://t.me/{bot_username}?start={code}"
    )

async def check_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])
        if ref_id != update.effective_user.id:
            referrals.setdefault(ref_id, []).append(update.effective_user.id)
            try:
                from shop import add_points
                add_points(ref_id, 30)
            except:
                pass
