# admin.py
from telegram import Update
from telegram.ext import ContextTypes
from economy import get_user
import sqlite3
import os

admin_id = int(os.getenv("ADMIN_ID", "1917071363"))
blocked_users = set()

def is_admin(user_id):
    return user_id == admin_id

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ You are not admin.")
    if not context.args:
        return await update.message.reply_text("Usage: /admin <message>")

    message = " ".join(context.args)
    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER)")
    cur.execute("SELECT id FROM users")
    rows = cur.fetchall()
    conn.close()

    sent = 0
    for (uid,) in rows:
        if uid in blocked_users:
            continue
        try:
            await context.bot.send_message(chat_id=uid, text=message)
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Sent to {sent} users.")

async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users")
    users = [str(r[0]) for r in cur.fetchall()]
    conn.close()
    await update.message.reply_text(f"👥 Total Users: {len(users)}\n" + "\n".join(users[:30]))

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /reply <user_id> <message>")

    user_id = int(context.args[0])
    msg = " ".join(context.args[1:])
    try:
        await context.bot.send_message(chat_id=user_id, text=f"✉️ Admin: {msg}")
        await update.message.reply_text("✅ Sent.")
    except:
        await update.message.reply_text("❌ Failed to send.")

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /block <user_id>")
    user_id = int(context.args[0])
    blocked_users.add(user_id)
    await update.message.reply_text(f"🔒 Blocked user {user_id}.")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /unblock <user_id>")
    user_id = int(context.args[0])
    blocked_users.discard(user_id)
    await update.message.reply_text(f"✅ Unblocked user {user_id}.")
