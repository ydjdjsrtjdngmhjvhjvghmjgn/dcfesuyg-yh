
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import html

admin_id = 1917071363  # Փոխիր քո ադմինի user ID-ով

async def notify_admin_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    username = user.username or "No username"
    full_name = user.full_name or "No name"
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if update.message:
        if update.message.text:
            text = update.message.text
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"📩 <b>Message from</b> <code>{user_id}</code>"
                     f"👤 <b>Name:</b> {html.escape(full_name)}"
                     f"🔗 <b>Username:</b> @{html.escape(username)}"
                     f"🕒 <b>Time:</b> {time}"
                     f"📝 <b>Text:</b> {html.escape(text)}",
                parse_mode="HTML"
            )
        elif update.message.photo:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🖼 <b>Photo received from</b> @{username} ({user_id})",
                parse_mode="HTML"
            )
            await context.bot.copy_message(chat_id=admin_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        elif update.message.document:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"📁 <b>Document received from</b> @{username} ({user_id})",
                parse_mode="HTML"
            )
            await context.bot.copy_message(chat_id=admin_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        elif update.message.voice:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🎤 <b>Voice message from</b> @{username} ({user_id})",
                parse_mode="HTML"
            )
            await context.bot.copy_message(chat_id=admin_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
