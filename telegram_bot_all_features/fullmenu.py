from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from tools import hash_command, base64_command, genpass_command, whois_command, iplookup_command
from quiz import quiz_command, quiz_answer_handler
from xp import xp_command
from daily import daily_command
from facts import fact_command
from hack_tools import nmap_command, bruteforce_command, phish_command
from shop import shop_command, buy_command
from wallet import wallet_command, faucet_command
from help import help_command, rules_command
from leaderboard import leaderboard_command

async def fullmenu_button_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "full_menu" or data == "casino_xp":
        keyboard = [
            [InlineKeyboardButton("🎰 Slots", callback_data="slots_game")],
            [InlineKeyboardButton("🎲 Dice Roll", callback_data="dice_game")],
            [InlineKeyboardButton("📊 Leaderboard", callback_data="leaderboard")],
            [InlineKeyboardButton("📅 Daily Reward", callback_data="daily")],
            [InlineKeyboardButton("🏆 XP Level", callback_data="xp")],
            [InlineKeyboardButton("🔙 Back", callback_data="full_menu")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎯 *Casino & XP Menu*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "tools_hack":
        keyboard = [
            [InlineKeyboardButton("🔍 IP Lookup", callback_data="ip_tool")],
            [InlineKeyboardButton("🌐 WHOIS", callback_data="whois_tool")],
            [InlineKeyboardButton("🔑 Password Gen", callback_data="passgen_tool")],
            [InlineKeyboardButton("🔒 Hash Tool", callback_data="hash_tool")],
            [InlineKeyboardButton("📡 Port Scanner", callback_data="nmap_tool")],
            [InlineKeyboardButton("🔐 Bruteforce", callback_data="bruteforce_tool")],
            [InlineKeyboardButton("🎣 Phishing Sim", callback_data="phish_tool")],
            [InlineKeyboardButton("🔙 Back", callback_data="full_menu")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="💻 *Hacking Tools*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "shop_wallet":
        keyboard = [
            [InlineKeyboardButton("🛒 View Shop", callback_data="shop")],
            [InlineKeyboardButton("💰 Buy Coins", callback_data="buy_coins")],
            [InlineKeyboardButton("💼 My Wallet", callback_data="wallet")],
            [InlineKeyboardButton("🚰 Crypto Faucet", callback_data="faucet")],
            [InlineKeyboardButton("🔙 Back", callback_data="full_menu")]
        ]
        await context.bot.send_message
        chat_id=chat_id,
        text="🛍️ *Shop & Wallet*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    
    elif data == "quiz_facts":
        keyboard = [
            [InlineKeyboardButton("❓ Tech Quiz", callback_data="quiz")],
            [InlineKeyboardButton("💡 Random Fact", callback_data="fact")],
            [InlineKeyboardButton("📖 Rules", callback_data="rules")],
            [InlineKeyboardButton("❓ Help", callback_data="help")],
            [InlineKeyboardButton("🔙 Back", callback_data="full_menu")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="📚 *Learning Center*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "admin_panel":
        if query.from_user.id != 1917071363:
            await query.answer("@Figrev", show_alert=True)
            return
            
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 View Users", callback_data="admin_users")],
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="full_menu")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text="🛠 *Admin Panel*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )