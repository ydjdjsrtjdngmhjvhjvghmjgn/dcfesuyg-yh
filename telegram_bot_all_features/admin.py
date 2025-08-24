from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from shared_state import user_data, all_users, user_last_messages, blocked_users
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import sqlite3
import os
import time
import asyncio
import logging
from datetime import datetime
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(
    filename='admin_actions.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Admin ID (load from environment or use default)
admin_id = int(os.getenv("ADMIN_ID", "1917071363"))

# Track user messages for spam detection
user_message_log = defaultdict(deque)
spam_tracker = defaultdict(deque)

# Anti-spam settings
SPAM_THRESHOLD = 5
SPAM_INTERVAL = 10
SPAM_BLOCK_DURATION = 300

def is_admin(user_id):
    return user_id == admin_id

def log_admin_action(action, user_id=None, extra=None):
    message = f"ACTION: {action}"
    if user_id:
        message += f" | USER: {user_id}"
    if extra:
        message += f" | INFO: {extra}"
    logger.info(message)

def track_message(user_id: int, text: str):
    now = datetime.now().strftime("%H:%M:%S")
    user_message_log[user_id].append(f"[{now}] {text}")
    if len(user_message_log[user_id]) > 50:
        user_message_log[user_id].popleft()

# ========== ADMIN COMMANDS ==========

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return await update.message.reply_text("💌 @Figrev")

        if not context.args:
            return await update.message.reply_text("Usage: /admin <message>")

        message = " ".join(context.args)
        sent = 0
        failed = 0

        for user_id in all_users:
            if user_id in blocked_users:
                continue
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
                sent += 1
            except:
                failed += 1

        await update.message.reply_text(
            f"📢 Broadcast Results:\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )
        log_admin_action("Broadcast message", extra=f"Message: {message[:50]}...")

    except Exception as e:
        logger.error(f"admin_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    conn = sqlite3.connect("botdata.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users")
    users = [str(r[0]) for r in cur.fetchall()]
    conn.close()

    await update.message.reply_text(
        f"👥 Total Users: {len(users)}\n"
        f"📋 First 30 Users:\n" + "\n".join(users[:30])
    )

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        if len(context.args) < 2:
            return await update.message.reply_text("Usage: /reply <user_id> <message>")

        try:
            user_id = int(context.args[0])
            message = " ".join(context.args[1:])

            if user_id in blocked_users:
                return await update.message.reply_text("⚠️ This user is blocked.")

            await context.bot.send_message(
                chat_id=user_id,
                text=f"✉️ Admin Message:\n\n{message}"
            )
            await update.message.reply_text("✅ Message sent.")
            log_admin_action("Replied to user", user_id, f"Message: {message[:50]}...")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {str(e)}")

    except Exception as e:
        logger.error(f"reply_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        if not context.args:
            return await update.message.reply_text("Usage: /block <user_id>")

        try:
            user_id = int(context.args[0])
            blocked_users.add(user_id)
            await update.message.reply_text(f"🔒 Blocked user {user_id}.")
            log_admin_action("Blocked user", user_id)
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")

    except Exception as e:
        logger.error(f"block_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        if not context.args:
            return await update.message.reply_text("Usage: /unblock <user_id>")

        try:
            user_id = int(context.args[0])
            blocked_users.discard(user_id)
            await update.message.reply_text(f"✅ Unblocked user {user_id}.")
            log_admin_action("Unblocked user", user_id)
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")

    except Exception as e:
        logger.error(f"unblock_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        total_users = len(all_users)
        blocked_count = len(blocked_users)
        active_today = sum(1 for uid in all_users if (datetime.now() - user_data[uid]['last_active']).seconds < 86400)

        await update.message.reply_text(
            f"📊 Bot Statistics:\n"
            f"👥 Total Users: {total_users}\n"
            f"🔒 Blocked: {blocked_count}\n"
            f"📈 Active Today: {active_today}"
        )

    except Exception as e:
        logger.error(f"stats_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def broadcast_photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        if not update.message.photo:
            return await update.message.reply_text("⚠️ Send a photo with a caption.")

        photo_file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        sent = 0

        for user_id in all_users:
            if user_id in blocked_users:
                continue
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_file_id,
                    caption=caption
                )
                sent += 1
            except:
                pass

        await update.message.reply_text(f"📷 Sent to {sent} users.")
        log_admin_action("Broadcast photo", extra=f"Caption: {caption[:50]}...")

    except Exception as e:
        logger.error(f"broadcast_photo_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

# (շարունակությունը հաջորդ ուղարկվող հաղորդագրությունում)
async def list_blocked_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        if not blocked_users:
            return await update.message.reply_text("🔓 No blocked users.")

        blocked_list = "\n".join(str(uid) for uid in blocked_users)
        await update.message.reply_text(f"🔒 Blocked Users:\n{blocked_list}")

    except Exception as e:
        logger.error(f"list_blocked_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def delete_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        if not context.args:
            return await update.message.reply_text("Usage: /delete_user <user_id>")

        try:
            user_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid user ID.")

        user_data.pop(user_id, None)
        all_users.discard(user_id)
        blocked_users.discard(user_id)
        user_last_messages.pop(user_id, None)

        await update.message.reply_text(f"🗑️ User {user_id} deleted.")
        log_admin_action("Deleted user", user_id)

    except Exception as e:
        logger.error(f"delete_user_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        await update.message.reply_text("https://te.legra.ph/%F0%9D%91%86%F0%9D%90%BE%F0%9D%91%8C%F0%9D%90%B5%F0%9D%90%B8%F0%9D%91%86%F0%9D%91%87-08-06")
    except Exception as e:
        logger.error(f"ping_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

async def top_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return

        top_users = sorted(
            user_message_log.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]

        result = "\n".join(
            f"{i+1}. ID: {uid} – {len(msgs)} msgs"
            for i, (uid, msgs) in enumerate(top_users)
        )

        await update.message.reply_text(
            f"🏆 Top Active Users:\n{result or 'No activity yet.'}"
        )

    except Exception as e:
        logger.error(f"top_users_command error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

# ========== ANTI-SPAM SYSTEM ==========

async def check_spam(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    timestamps = spam_tracker[user_id]

    while timestamps and now - timestamps[0] > SPAM_INTERVAL:
        timestamps.popleft()

    timestamps.append(now)

    if len(timestamps) >= SPAM_THRESHOLD:
        blocked_users.add(user_id)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⛔ You are temporarily blocked for spam."
            )
        except:
            pass

        log_admin_action("Auto-blocked spammer", user_id)
        asyncio.create_task(unblock_after_delay(user_id, SPAM_BLOCK_DURATION, context))
        return True
    return False

async def unblock_after_delay(user_id: int, delay: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(delay)
    blocked_users.discard(user_id)
    log_admin_action("Auto-unblocked", user_id)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Your block has been lifted."
        )
    except:
        pass

# ========== ADMIN PANEL BUTTON UI ==========

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return await update.message.reply_text("⛔ Access Denied.")

        keyboard = [
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Broadcast Text", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🖼 Broadcast Photo", callback_data="admin_broadcast_photo")],
            [InlineKeyboardButton("🧑‍💬 Reply to User", callback_data="admin_reply")],
            [InlineKeyboardButton("🚫 Block", callback_data="admin_block")],
            [InlineKeyboardButton("✅ Unblock", callback_data="admin_unblock")],
            [InlineKeyboardButton("🗑 Delete User", callback_data="admin_delete")],
            [InlineKeyboardButton("🔓 List Blocked", callback_data="admin_blocked_list")],
            [InlineKeyboardButton("🏓 Ping", callback_data="admin_help")],
            [InlineKeyboardButton("🏆 Top Users", callback_data="admin_top")]
        ]

        await update.message.reply_text(
            "👮 Admin Panel — Choose an action:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"admin_panel error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

# ========== CALLBACK HANDLER ==========

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if not is_admin(user_id):
            return await query.message.reply_text("⛔ Access denied.")

        fake_update = Update(update.update_id, message=query.message)

        match query.data:
            case "admin_stats":
                await stats_command(fake_update, context)
            case "admin_broadcast":
                await admin_command(fake_update, context)
            case "admin_broadcast_photo":
                await broadcast_photo_command(fake_update, context)
            case "admin_reply":
                await reply_command(fake_update, context)
            case "admin_block":
                await block_command(fake_update, context)
            case "admin_unblock":
                await unblock_command(fake_update, context)
            case "admin_delete":
                await delete_user_command(fake_update, context)
            case "admin_blocked_list":
                await list_blocked_command(fake_update, context)
            case "admin_help":
                await help_command(fake_update, context)
            case "admin_top":
                await top_users_command(fake_update, context)
            case _:
                await query.message.reply_text("❌ Unknown admin command.")

    except Exception as e:
        logger.error(f"admin_callback_handler error: {e}")
        await update.message.reply_text('⚠️ An error occurred.')

# ========== REGISTER ADMIN COMMANDS ==========

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", admin_command))
    application.add_handler(CommandHandler("broadcast_photo", broadcast_photo_command))
    application.add_handler(CommandHandler("reply", reply_command))
    application.add_handler(CommandHandler("block", block_command))
    application.add_handler(CommandHandler("unblock", unblock_command))
    application.add_handler(CommandHandler("delete_user", delete_user_command))
    application.add_handler(CommandHandler("list_blocked", list_blocked_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("top_users", top_users_command))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))

    # Optional aliases
    application.add_handler(CommandHandler("broadcast_all", admin_command))
    application.add_handler(CommandHandler("broadcast_file", broadcast_photo_command))
    application.add_handler(CommandHandler("broadcast_video", broadcast_photo_command))
    application.add_handler(CommandHandler("block_all", block_command))
    application.add_handler(CommandHandler("unblock_all", unblock_command))
    application.add_handler(CommandHandler("blocked_count", list_blocked_command))
    application.add_handler(CommandHandler("userinfo", reply_command))
    application.add_handler(CommandHandler("search", reply_command))
    application.add_handler(CommandHandler("vip_add", top_users_command))
    application.add_handler(CommandHandler("vip_remove", top_users_command))
    application.add_handler(CommandHandler("purge", list_blocked_command))
    application.add_handler(CommandHandler("purge_blocked", list_blocked_command))
    application.add_handler(CommandHandler("export", stats_command))
    application.add_handler(CommandHandler("backup_users", stats_command))
    application.add_handler(CommandHandler("restore_users", stats_command))
    application.add_handler(CommandHandler("clean_user", delete_user_command))
