# menu.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from economy import is_premium

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎰 Casino & XP", callback_data="menu_casino")],
        [InlineKeyboardButton("🧰 Tools & Hack", callback_data="menu_tools")],
        [InlineKeyboardButton("📚 Quiz & Learning", callback_data="menu_quiz")],
        [InlineKeyboardButton("💰 Wallet & Premium", callback_data="menu_wallet")],
        [InlineKeyboardButton("📢 Admin Panel", callback_data="menu_admin")],
        [InlineKeyboardButton("📖 Help / Rules", callback_data="menu_help")]
    ]
    await update.message.reply_text("📍 *Choose a category:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    section = query.data
    if section == "menu_casino":
        text = (
            "🎰 *Casino & XP Commands:*\n"
            "/xp – Show XP & level\n"
            "/daily – Claim XP\n"
            "/leaderboard – Top users"
        )
    elif section == "menu_tools":
        text = (
            "🧰 *Hacking & Tools:*\n"
            "/nmap <ip>\n"
            "/phish\n"
            "/bruteforce\n"
            "/whois <domain>\n"
            "/iplookup <ip>\n"
            "/hash <txt>, /base64 <txt>"
        )
    elif section == "menu_quiz":
        text = (
            "📚 *Quiz & Knowledge:*\n"
            "/quiz – Answer cybersecurity/programming questions\n"
            "/fact – Get a tech fact"
        )
    elif section == "menu_wallet":
        premium = is_premium(user_id)
        status = "✅ Premium Active" if premium else "❌ Not Premium"
        text = (
            f"💰 *Wallet & Premium:*\n/status – Check balance\n/premium – Buy 1 day premium ($1.5)\n\nStatus: *{status}*"
        )
    elif section == "menu_admin":
        text = (
            "📢 *Admin Tools (admin only):*\n"
            "/admin <text> – Broadcast\n"
            "/reply <id> <msg>\n"
            "/block <id> /unblock <id>\n"
            "/admin_users"
        )
    elif section == "menu_help":
        text = (
            "📖 *Help & Disclaimer:*\n"
            "This bot is for fun and learning only.\nNo real hacking is performed. Enjoy simulated tools."
        )
    else:
        text = "❌ Invalid selection."

    await query.edit_message_text(text, parse_mode="Markdown")
