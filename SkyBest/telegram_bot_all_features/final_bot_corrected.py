import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackQueryHandler, ApplicationHandlerStop
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from tools import hash_command, base64_command, genpass_command, whois_command, iplookup_command
from quiz import quiz_command, quiz_answer_handler
from xp import xp_command
from daily import daily_command
from facts import fact_command
from hack_tools import nmap_command, bruteforce_command, phish_command
from shop import shop_command, buy_command
from referral import referral_command, check_referral
from leaderboard import leaderboard_command
from wallet import wallet_command, faucet_command
from help import help_command, rules_command
from datetime import datetime, timedelta
import random
import asyncio
import json
from collections import defaultdict, deque
import csv
import os

glazaboga_data = {}
try:
    with open('telegram_bot_all_features/glazaboga.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            glazaboga_data[str(row['id'])] = row
except FileNotFoundError:
    print("⚠️ CSV ֆայլը չի գտնվել — համոզվիր, որ 'glazaboga.csv'-ը ճիշտ տեղում է")
import time

# Bot token (you can load from .env if preferred)
from config import TOKEN

user_data = {}
email_data = {}
promo_code_data = {}
used_promo = False
admin_id = 1917071363
all_users = set()
user_last_messages = {}
blocked_users = set()
user_message_times = defaultdict(deque)  # For anti-spam tracking

# Anti-spam configuration
SPAM_THRESHOLD = 8  # Messages
SPAM_INTERVAL = 10  # Seconds
SPAM_PENALTY = 300  # Seconds to block

CHANNEL_USERNAME = '@SkyBesst'

# Initialize user data with proper structure
def init_user_data(user):
    user_id = user.id
    if user_id not in user_data:
        user_data[user_id] = {
            'start_time': datetime.now(),
            'balance': 100,
            'subscription': False,
            'subscription_end': None,
            'referral_count': 0,
            'referral_bonus': 0,
            'last_daily': None,
            'xp': 0,
            'level': 1,
            'username': user.username,
            'full_name': user.full_name,
            'last_active': datetime.now(),
            'warnings': 0
        }
    else:
        # Update user info if changed
        user_data[user_id]['username'] = user.username
        user_data[user_id]['full_name'] = user.full_name
        user_data[user_id]['last_active'] = datetime.now()
    return user_data[user_id]

# Enhanced user notification
async def notify_admin(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE, action: str, details: str = ""):
    global admin_id
    user = update.effective_user
    if not user:
        return

    username = user.username if user.username else "No username"
    user_id = user.id
    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"👤 User: @{username} (ID: {user_id})\n"
                 f"🔔 Action: {action}\n"
                 f"📝 Details: {details}\n"
                 f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as e:
        print(f"Admin notification error: {e}")

# Anti-spam protection
async def check_spam(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    times = user_message_times[user_id]
    
    # Remove old timestamps
    while times and now - times[0] > SPAM_INTERVAL:
        times.popleft()
    
    # Add current timestamp
    times.append(now)
    
    # Check if over threshold
    if len(times) >= SPAM_THRESHOLD:
        blocked_users.add(user_id)
        user = context.bot.get_chat(user_id)
        username = user.username if user.username else "No username"
        
        await context.bot.send_message(
            admin_id,
            f"🚨 *SPAM ALERT*\n\n"
            f"👤 User: @{username} (ID: {user_id})\n"
            f"📊 Activity: {len(times)} messages in {SPAM_INTERVAL} seconds\n"
            f"⛔ Automatically blocked for {SPAM_PENALTY//60} minutes",
            parse_mode="HTML"
        )
        
        # Schedule unblock after penalty period
        asyncio.create_task(
            unblock_after_delay(user_id, SPAM_PENALTY, context)
        )
        
        return True
    return False

async def unblock_after_delay(user_id: int, delay: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(delay)
    if user_id in blocked_users:
        blocked_users.remove(user_id)
        user = context.bot.get_chat(user_id)
        username = user.username if user.username else "No username"
        await context.bot.send_message(
            admin_id,
            f"✅ *User Unblocked*\n\n"
            f"👤 User: @{username} (ID: {user_id})\n"
            f"⏱️ Block period expired",
            parse_mode="HTML"
        )

# Enhanced start command with user info
async def start(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if update.effective_user.id in blocked_users:
        return
    if await check_spam(update.effective_user.id, context):
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    user_id = user.id
    
    await notify_admin(update, context, "Started bot", f"Referred by: {context.args[0] if context.args else 'None'}")
    
    # Check referral
    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id and referrer_id in user_data:
                user_data[referrer_id]['referral_count'] += 1
                user_data[referrer_id]['balance'] += 50
                user_data[referrer_id]['referral_bonus'] += 50
                user_info['balance'] += 25
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 New referral! @{user.username} joined using your link.\n"
                         f"💰 You received 50 coins!\n"
                         f"🧾 Total referrals: {user_data[referrer_id]['referral_count']}"
                )
                await notify_admin(update, context, "Referral successful", f"Referrer: {referrer_id}")
        except ValueError:
            pass

    # User info card
    time_diff = datetime.now() - user_info['start_time']
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes = remainder // 60
    
    # Check subscription status
    if user_info['subscription'] and user_info['subscription_end'] and user_info['subscription_end'] > datetime.now():
        subscription_status = "🌟 Active"
    else:
        subscription_status = "❌ Inactive"
        user_info['subscription'] = False
    
    user_card = (
    f"👤 <b>User Info</b>"

    f"├─ Name: {html.escape(user.full_name)}"

    f"├─ Username: @{html.escape(user.username) if user.username else 'N/A'}"

    f"├─ ID: <code>{user_id}</code>"

    f"├─ Member since: {user_info['start_time'].strftime('%Y-%m-%d')}"

    f"├─ Session: {hours}h {minutes}m"

    f"├─ Subscription: {subscription_status}"

    f"├─ Balance: {user_info['balance']} coins 💰"

    f"├─ Level: {user_info['level']} 🏆"

    f"└─ Referrals: {user_info['referral_count']} 👥"
)

    # Check channel subscription
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await update.message.reply_text(
                user_card,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Subscribe ✅", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
                ])
            )
            return
    except Exception as e:
        await update.message.reply_text("⚠️ Couldn't verify subscription. Please try again later.")
        return

    await update.message.reply_text(
        user_card,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Subscribe", url=f'https://t.me/{CHANNEL_USERNAME.lstrip("@")}')],
            [InlineKeyboardButton("Open Mini App 🎯", web_app=WebAppInfo(url="https://paradoxsoull.github.io/my/"))],
            [InlineKeyboardButton("✅ I'm Subscribed", callback_data='subscribed')]
        ])
    )

    all_users.add(user.id)

async def button_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    user = query.from_user
    user_id = user.id
    
    # Block check
    if user_id in blocked_users:
        await query.answer("⛔ You have been blocked from using this bot", show_alert=True)
        return
    
    # Anti-spam check
    if await check_spam(user_id, context):
        await query.answer("⚠️ Slow down! You're sending too many requests", show_alert=True)
        return
    
    await notify_admin(update, context, "Button pressed", f"Button: {choice}")
    
    user_info = init_user_data(user)

    if choice == 'subscribed':
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                await query.message.reply_text(
                    "❌ You're not subscribed yet. Please join our channel:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
                    ])
                )
                return
        except Exception as e:
            await query.message.reply_text("⚠️ Verification failed. Please try again.")
            return

        keyboard = [
            [
                InlineKeyboardButton("💣 Destroy Target", callback_data='destroy'),
                InlineKeyboardButton("💌 Donate", url='http://t.me/send?start=IVcKRqQqNLca')
            ],
            [
                InlineKeyboardButton("👤 My Profile", callback_data='info'),
                InlineKeyboardButton("📢 Channel", url='https://t.me/SkyBesst'),
                InlineKeyboardButton("📜 Rules", url='https://te.legra.ph/WARNING-RULES-05-17'),
            ],
            [
                InlineKeyboardButton("💰 Balance", callback_data='balance'),
            ]
        ]
        await query.edit_message_text(
            "✅ Subscription confirmed! Enjoy the bot!\n\n"
            "🔥 Welcome to the ultimate destruction bot!\n"
            "Select an option below to get started:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif choice == 'destroy':
        keyboard = [
            [
                InlineKeyboardButton("👤 Account", callback_data='account'),
                InlineKeyboardButton("📢 Channel", callback_data='channel'),
                InlineKeyboardButton("🤖 Telegram Bot", callback_data='telegram_bot')
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data='subscribed')
            ]
        ]
        await query.edit_message_text(
            "🎯 Select target type to destroy:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif choice == 'info':
        # Calculate account age
        account_age = datetime.now() - user_info['start_time']
        days = account_age.days
        hours, remainder = divmod(account_age.seconds, 3600)
        minutes = remainder // 60
        
        # Subscription status
        if user_info['subscription'] and user_info['subscription_end'] and user_info['subscription_end'] > datetime.now():
            sub_status = f"🌟 Active (Expires: {user_info['subscription_end'].strftime('%Y-%m-%d')})"
        else:
            sub_status = "❌ Inactive"
            user_info['subscription'] = False
        
        info_text = (
            f"👤 *Your Profile*\n"
            f"├─ Name: {user.full_name}\n"
            f"├─ Username: @{user.username if user.username else 'N/A'}\n"
            f"├─ ID: `{user_id}`\n"
            f"├─ Account age: {days}d {hours}h {minutes}m\n"
            f"├─ Subscription: {sub_status}\n"
            f"├─ Balance: {user_info['balance']} coins 💰\n"
            f"├─ Level: {user_info['level']} 🏆\n"
            f"└─ Referrals: {user_info['referral_count']} 👥\n"
            f"\n💎 Earn more by inviting friends!"
        )
        
        await query.edit_message_text(
            info_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Buy Subscription", url="http://t.me/send?start=IVJERrqbgG9F")],
                [InlineKeyboardButton("🌟 Enter Promo Code", callback_data='promo_code')],
                [InlineKeyboardButton("👥 Refer Friends", callback_data='referral')],
                [InlineKeyboardButton("🔙 Back", callback_data='subscribed')]
            ])
        )

    elif choice == 'promo_code':
        promo_code_data[user_id] = {'step': 'enter_promo'}
        await query.message.reply_text("🔑 Enter your promo code to get 1 month free subscription:")

    elif choice == 'referral':
        ref_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
        await query.message.reply_text(
            f"📨 *Your Referral Program*\n\n"
            f"🔗 Your referral link:\n`{ref_link}`\n\n"
            f"👥 Referrals: {user_info['referral_count']}\n"
            f"💰 Earned: {user_info['referral_bonus']} coins\n\n"
            f"🎉 Invite friends and earn 50 coins for each new user!",
            parse_mode="HTML"
        )

    elif choice == 'balance':
        await query.message.reply_text(
            f"💰 *Your Balance*\n\n"
            f"Current balance: {user_info['balance']} coins\n\n"
            f"Earn more coins by:\n"
            f"- 🎯 Completing missions\n"
            f"- 👥 Referring friends\n"
            f"- 🎰 Playing games\n"
            f"- 🎁 Claiming daily bonuses",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Claim Daily", callback_data='daily')],
                [InlineKeyboardButton("👥 Refer Friends", callback_data='referral')],
                [InlineKeyboardButton("💸 Buy Coins", url='http://t.me/send?start=IVcKRqQqNLca')],
                [InlineKeyboardButton("🔙 Back", callback_data='subscribed')]
            ])
        )

    elif choice == 'buy_coins':  # ADDED: Buy coins button handler
        await shop_command(update, context)  # Reuse shop command functionality

    elif choice == 'daily':
        last_daily = user_info.get('last_daily')
        now = datetime.now()
        
        if last_daily and (now - last_daily).days < 1:
            next_claim = (last_daily + timedelta(days=1) - now)
            hours, remainder = divmod(next_claim.seconds, 3600)
            minutes = remainder // 60
            await query.message.reply_text(
                f"⏳ You've already claimed your daily reward today!\n"
                f"Next claim in: {hours}h {minutes}m"
            )
            return
        
        # Award daily bonus
        bonus = random.randint(50, 150)
        user_info['balance'] += bonus
        user_info['last_daily'] = now
        
        await query.message.reply_text(
            f"🎁 *Daily Reward Claimed!*\n\n"
            f"💰 You received: {bonus} coins\n"
            f"💵 New balance: {user_info['balance']} coins\n\n"
            f"⏳ Come back tomorrow for more!",
            parse_mode="HTML"
        )

    elif choice == 'full_menu':
        keyboard = [
            [InlineKeyboardButton("🎯 Casino & XP", callback_data="casino_xp")],
            [InlineKeyboardButton("💻 Tools & Hacking", callback_data="tools_hack")],
            [InlineKeyboardButton("🛍️ Shop & Wallet", callback_data="shop_wallet")],
            [InlineKeyboardButton("📚 Quiz & Facts", callback_data="quiz_facts")],
            [InlineKeyboardButton("📢 Admin Panel", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Back", callback_data="subscribed")]
        ]
        await query.edit_message_text(
            "📍 *Full Menu*\nSelect a category:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif choice in ['account', 'channel', 'telegram_bot']:
        # Check if subscription is active
        subscription_active = (
            user_info['subscription'] and 
            user_info['subscription_end'] and 
            user_info['subscription_end'] > datetime.now()
        )
        
        if not subscription_active:
            await query.message.reply_text(
                "🔒 Premium Feature\n\n"
                "This requires an active subscription.\n\n"
                "💎 Get premium to unlock:\n"
                "- Full destruction capabilities\n"
                "- Priority targeting\n"
                "- Stealth mode\n\n"
                "Special offer: 1.5 USDT for 30 days!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Buy Subscription", url="http://t.me/send?start=IVcQMByN6GzM")],
                    [InlineKeyboardButton("🌟 Use Promo Code", callback_data='promo_code')],
                    [InlineKeyboardButton("🔙 Back", callback_data='subscribed')]
                ])
            )
            return
        
        prompts = {
            'account': "👤 Enter target username (@username):",
            'channel': "📢 Enter channel URL:",
            'telegram_bot': "🤖 Enter bot username (@botname):"
        }
        await query.message.reply_text(prompts[choice])
        email_data[user_id] = {'step': f'get_{choice}_name' if choice != 'channel' else 'get_channel_url'}

    elif choice == 'dox_id':
        email_data[user_id] = {'step': 'dox_lookup'}
        await query.message.reply_text("📥 Enter ID to get data.")



async def handle_message(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    
    user_id = user.id
    
    # Skip if user is blocked
    if user_id in blocked_users:
        return
    
    # Anti-spam check
    if await check_spam(user_id, context):
        return
    
    # Initialize user data
    user_info = init_user_data(user)
    
    # Store last message
    text = update.message.text
    user_last_messages[user_id] = text
    all_users.add(user_id)
 
    
    await notify_admin(update, context, "Sent message", text)
 # Auto-responses
    keyword_responses = {
        "hello": "👋 Hello! How can I assist you today?",
        "hi": "👋 Hi there! Ready for some action?",
        "balance": f"💰 Your current balance is {user_info['balance']} coins",
        "help": "🆘 Check out /help for commands or use the menu!",
        "promo code": "🌟 Click the 'Enter Promo Code' button to redeem!",
        "promocode": "🔑 Enter your promo code now:",
        "thanks": "🙏 You're welcome!",
        "thank you": "😊 My pleasure!",
        "menu": "📱 Use /menu to see all options"
    }
    
    lowered_text = text.lower()
    for keyword, response in keyword_responses.items():
        if keyword in lowered_text:
            await update.message.reply_text(response)
            return

    # Promo code handling
    if promo_code_data.get(user_id, {}).get('step', '').startswith('enter_promo'):
        if text == "Apasni_KaliLinux":
            user_info['subscription'] = True
            user_info['subscription_end'] = datetime.now() + timedelta(days=30)
            await update.message.reply_text(
                "🎉 *Promo Code Accepted!*\n\n"
                "🌟 You've received 1 month of premium subscription!\n"
                "⏳ Expires: " + user_info['subscription_end'].strftime('%Y-%m-%d'),
                parse_mode="HTML"
            )
            await notify_admin(update, context, "Redeemed promo code", text)
        else:
            await update.message.reply_text("❌ Invalid promo code. Please try again.")
        del promo_code_data[user_id]
        return
    
    # Target handling
    if user_id in email_data:
        step = email_data.get(user_id, {}).get('step')
        if not step:
            return

        if step == 'dox_lookup':
            user_input_id = text.strip()
            result = glazaboga_data.get(user_input_id)

            if result:
                info = (
                    f"🧾 *Dox Report*\n"
                    f"• 🆔 ID: `{user_input_id}`\n"
                    f"• 📞 Phone: `{result.get('phone', 'N/A')}`\n"
                    f"• 👤 Username: @{result.get('username') if result.get('username') else 'N/A'}\n"
                    f"• 👨‍💼 Name: {result.get('first_name', '')} {result.get('last_name', '')}"
                )
            else:
                info = "❌ Տվյալ ID-ով տեղեկություն չի գտնվել։"

            await update.message.reply_text(info, parse_mode='Markdown')
            del email_data[user_id]
            return
        
        # Validation
        if step in ['get_account_name', 'get_bot_name'] and not text.startswith('@'):
            await update.message.reply_text("⚠️ Please enter a username starting with @")
            return
        if step == 'get_channel_url' and not text.startswith("http"):
            await update.message.reply_text("⚠️ Please enter a valid URL starting with http/https")
            return
        
        # Destruction sequence
        await update.message.reply_text("🔥 Destruction sequence initiated...")
        for i in range(1, 26):
            await update.message.reply_text(f"🚀 Stage {i}/26: Targeting systems engaged...")
            await asyncio.sleep(1)
        
        await update.message.reply_text(
            "✅ Target successfully destroyed!\n"
            "📬 Report has been sent to HQ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Destroy Another", callback_data='destroy')],
                [InlineKeyboardButton("🔙 Back", callback_data='subscribed')]
            ])
        )
        
        del email_data[user_id]
        await notify_admin(update, context, "Destroyed target", text)


# Enhanced balance command
async def balance_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    
    await update.message.reply_text(
        f"💰 *Your Account Balance*\n\n"
        f"Current balance: `{user_info['balance']}` coins\n"
        f"Level: `{user_info['level']}` 🏆\n\n"
        f"💸 Earn more coins by:\n"
        f"- Claiming /daily rewards\n"
        f"- Inviting friends with /referral\n"
        f"- Playing games in the casino\n"
        f"- Completing missions",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
    [InlineKeyboardButton("🎁 Claim Daily", callback_data='daily')],
    [InlineKeyboardButton("👥 Refer Friends", callback_data='referral')],
    [InlineKeyboardButton("💸 Buy Coins", url='http://t.me/send?start=IVcKRqQqNLca')],
    [InlineKeyboardButton("🔙 Back", callback_data='subscribed')]
])

    )
    await notify_admin(update, context, "Checked balance", "")

# Enhanced menu command
async def menu_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("💣 Destroy Target", callback_data='destroy')],
        [InlineKeyboardButton("👤 My Profile", callback_data='info')],
        [InlineKeyboardButton("💰 Balance", callback_data='balance')],
        [InlineKeyboardButton("🔍 Dox by ID", callback_data='dox_id')],

        [InlineKeyboardButton("🎮 Games & Tools", callback_data='full_menu')],
        [InlineKeyboardButton("📢 Channel", url='https://t.me/SkyBesst')],
        [InlineKeyboardButton("📜 Rules", url='https://te.legra.ph/WARNING-RULES-05-17')]
    ]
    
    await update.message.reply_text(
        "📱 *Main Menu*\n\n"
        "Select an option below:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await notify_admin(update, context, "Opened menu", "")

async def destroy_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    
    # Check if subscription is active
    subscription_active = (
        user_info['subscription'] and 
        user_info['subscription_end'] and 
        user_info['subscription_end'] > datetime.now()
    )
    
    if not subscription_active:
        await update.message.reply_text(
            "🔒 Premium Feature\n\n"
            "Target destruction requires an active subscription.\n\n"
            "💎 Get premium to unlock destruction capabilities!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Buy Subscription", url="http://t.me/send?start=IVcQMByN6GzM")],
                [InlineKeyboardButton("🌟 Use Promo Code", callback_data='promo_code')]
                [InlineKeyboardButton("🔙 Back", callback_data='subscribed')]
            ])
        )
        return
        
    await update.message.reply_text(
        "🎯 Enter target information:\n\n"
        "Examples:\n"
        "- For accounts: @username\n"
        "- For channels: https://t.me/channel\n"
        "- For bots: @bot_username\n\n"
        "Enter target now:"
    )
    await notify_admin(update, context, "Started destruction", "")

async def channel_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    await update.message.reply_text(
        "📢 Official Channel:\nhttps://t.me/SkyBesst\n\n"
        "Join for:\n- Latest updates\n- Exclusive offers\n- Community support",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel ➡️", url="https://t.me/SkyBesst")]
        ])
    )
    await notify_admin(update, context, "Viewed channel", "")

# Referral command
async def referral_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    
    ref_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user.id}"
    await update.message.reply_text(
        f"📨 *Your Referral Program*\n\n"
        f"🔗 Your referral link:\n`{ref_link}`\n\n"
        f"👥 Referrals: {user_info['referral_count']}\n"
        f"💰 Earned: {user_info['referral_bonus']} coins\n\n"
        f"🎉 Invite friends and earn 50 coins for each new user!",
        parse_mode="HTML"
    )
    await notify_admin(update, context, "Viewed referral", "")

# ========== ADMIN PANEL ENHANCEMENTS ==========
async def admin_panel(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await update.message.reply_text("⛔ Admin access only")
        return

    # Admin stats
    total_users = len(all_users)
    blocked_count = len(blocked_users)
    active_today = len([uid for uid in all_users if user_data.get(uid, {}).get('last_active') and 
                        (datetime.now() - user_data[uid]['last_active']).seconds < 86400])
    
    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')],
        [InlineKeyboardButton("👥 View Users", callback_data='admin_users')],
        [InlineKeyboardButton("📊 Stats", callback_data='admin_stats')],
        [InlineKeyboardButton("📨 Last Messages", callback_data='admin_lastmsgs')],
        [InlineKeyboardButton("⛔ Block User", callback_data='admin_block')],
        [InlineKeyboardButton("✅ Unblock User", callback_data='admin_unblock')],
        [InlineKeyboardButton("➕ Vip +", callback_data='admin_vip_add')],
        [InlineKeyboardButton("➖ Vip -", callback_data='admin_vip_remove')],
        [InlineKeyboardButton("📩 Reply to User", callback_data='admin_reply')]
    ]
    
    await update.message.reply_text(
        "📱 *Admin Panel*\n\n"
        f"👥 Total users: {total_users}\n"
        f"⛔ Blocked users: {blocked_count}\n"
        f"📈 Active today: {active_today}\n\n"
        "Select an option:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await notify_admin(update, context, "Opened admin panel", "")

async def admin_callback_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id != admin_id:
        await query.message.reply_text("⛔ Admin access only")
        return

    action = query.data
    if action == 'admin_users':
        users = list(all_users)
        user_list = "\n".join([f"👤 {uid} - @{user_data[uid].get('username', 'N/A')}" for uid in users[:50]])
        await query.message.reply_text(f"👥 Users (First 50):\n{user_list}")
    elif action == 'admin_lastmsgs':
        text = "\n".join([f"👤 {uid}: {msg}" for uid, msg in list(user_last_messages.items())[:20]])
        await query.message.reply_text(f"📨 Recent Messages:\n{text if text else 'No messages'}")
    elif action == 'admin_block':
        await query.message.reply_text("Send: /block <user_id>")
    elif action == 'admin_unblock':
        await query.message.reply_text("Send: /unblock <user_id>")
    elif action == 'admin_broadcast':
        await query.message.reply_text("Send: /broadcast <your message>")
    elif action == 'admin_reply':
        await query.message.reply_text("Send: /reply <user_id> <message>")
    elif action == 'admin_stats':
        total_users = len(all_users)
        blocked_count = len(blocked_users)
        active_users = sum(1 for uid in all_users if user_data.get(uid, {}).get('last_active') and 
                         (datetime.now() - user_data[uid]['last_active']).seconds < 86400)
        premium_users = sum(1 for uid in all_users 
                          if user_data.get(uid, {}).get('subscription') 
                          and user_data[uid].get('subscription_end') 
                          and user_data[uid]['subscription_end'] > datetime.now())
        await query.message.reply_text(
            f"📊 *Bot Statistics*\n\n"
            f"👥 Total users: {total_users}\n"
            f"🚫 Blocked users: {blocked_count}\n"
            f"📈 Active users (24h): {active_users}\n"
            f"💎 Premium users: {premium_users}",
            parse_mode="HTML"
        )
    elif action == 'admin_vip_add':
        await query.message.reply_text("📥 Send: /vip_add <user_id>")
    elif action == 'admin_vip_remove':
        await query.message.reply_text("📥 Send: /vip_remove <user_id>")

async def block_user(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /block <user_id>")
        return
        
    try:
        uid = int(context.args[0])
        blocked_users.add(uid)
        await update.message.reply_text(f"⛔ Blocked user {uid}")
        await notify_admin(update, context, "Blocked user", f"User ID: {uid}")
    except:
        await update.message.reply_text("Invalid user ID")

async def unblock_user(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /unblock <user_id>")
        return
        
    try:
        uid = int(context.args[0])
        if uid in blocked_users:
            blocked_users.remove(uid)
            await update.message.reply_text(f"✅ Unblocked user {uid}")
            await notify_admin(update, context, "Unblocked user", f"User ID: {uid}")
        else:
            await update.message.reply_text(f"User {uid} is not blocked")
    except:
        await update.message.reply_text("Invalid user ID")

async def broadcast_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await update.message.reply_text("⛔ Admin access only")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    sent = 0
    failed = 0
    errors = []
    
    for user_id in all_users:
        if user_id in blocked_users:
            continue
            
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Announcement*\n\n{message}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))
            # Remove inactive users
            if "bot was blocked" in str(e).lower():
                all_users.discard(user_id)
    
    report = (
        f"📢 Broadcast Results:\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {len(all_users)}"
    )
    
    if errors:
        report += f"\n\nErrors:\n" + "\n".join(set(errors))[:1000]
    
    await update.message.reply_text(report)
    await notify_admin(update, context, "Sent broadcast", f"Message: {message[:50]}...")

# New: Enhanced reply command
async def reply_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await update.message.reply_text("⛔ Admin access only")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reply <user_id> <message>")
        return

    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
        
        if user_id in blocked_users:
            await update.message.reply_text("⚠️ This user is blocked")
            return
            
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📨 *Message from Admin*\n\n{message}",
                parse_mode="HTML"
            )
            await update.message.reply_text(f"✅ Message sent to {user_id}")
            await notify_admin(update, context, "Replied to user", 
                              f"User: {user_id}\nMessage: {message[:100]}")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to send message: {str(e)}")
    except:
        await update.message.reply_text("Invalid user ID")

# Admin stats command
async def admin_stats_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await update.message.reply_text("@FIGREV")
        return

    total_users = len(all_users)
    blocked_count = len(blocked_users)
    active_users = sum(1 for uid in all_users if user_data.get(uid, {}).get('last_active') and 
                     (datetime.now() - user_data[uid]['last_active']).seconds < 86400)
    
    # Count active premium users
    premium_users = sum(1 for uid in all_users 
                      if user_data.get(uid, {}).get('subscription') 
                      and user_data[uid].get('subscription_end') 
                      and user_data[uid]['subscription_end'] > datetime.now())
    
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total users: {total_users}\n"
        f"🚫 Blocked users: {blocked_count}\n"
        f"📈 Active users (24h): {active_users}\n"
        f"💎 Premium users: {premium_users}",
        parse_mode="HTML"
    )
    await notify_admin(update, context, "Checked stats", "")

async def fullmenu_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("🎯 Casino & XP", callback_data="full_casino_xp")],
        [InlineKeyboardButton("💻 Tools & Hacking", callback_data="full_tools_hack")],
        [InlineKeyboardButton("🛍️ Shop & Wallet", callback_data="full_shop_wallet")],
        [InlineKeyboardButton("📚 Quiz & Facts", callback_data="full_quiz_facts")],
        [InlineKeyboardButton("🔙 Back", callback_data="subscribed")]
    ]
    await update.message.reply_text(
        "📱 *Full Menu*\n\n"
        "Select a category:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await notify_admin(update, context, "Opened full menu", "")

async def fullmenu_button_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "casino_xp":
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
            parse_mode="HTML",
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
            parse_mode="HTML",
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
        await context.bot.send_message(
            chat_id=chat_id,
            text="🛍️ *Shop & Wallet*",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "admin_panel":
        if query.from_user.id != admin_id:
            await query.answer("⛔ Admin access only", show_alert=True)
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
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def admin_search(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /search <username/name/id>")
        return
    
    search_term = context.args[0].lower()
    results = []
    
    for uid, data in user_data.items():
        if (search_term in str(uid) or 
            search_term in data.get('username', '').lower() or 
            search_term in data.get('full_name', '').lower()):
            results.append(f"👤 {uid} - @{data.get('username', 'N/A')} - {data.get('full_name', 'N/A')}")
    
    if results:
        await update.message.reply_text("\n".join(results[:50]))  # Limit to 50 results
    else:
        await update.message.reply_text("No users found")
# Tool shortcuts
async def tool_shortcut_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tool = query.data
    chat_id = query.message.chat_id

    # Հիմնական գործիքներ
    if tool == "ip_tool":
        await context.bot.send_message(chat_id, "🔍 Enter IP address for lookup:\nUsage: /iplookup <ip>")
    elif tool == "whois_tool":
        await context.bot.send_message(chat_id, "🌐 Enter domain for WHOIS lookup:\nUsage: /whois <domain>")
    elif tool == "passgen_tool":
        await genpass_command(update, context)
    elif tool == "hash_tool":
        await context.bot.send_message(chat_id, "🔒 Enter text to hash:\nUsage: /hash <text>")
    elif tool == "nmap_tool":
        await context.bot.send_message(chat_id, "📡 Enter target for port scan:\nUsage: /nmap <ip>")
    elif tool == "bruteforce_tool":
        await bruteforce_command(update, context)
    elif tool == "phish_tool":
        await phish_command(update, context)
    
    # Խանութ և դրամապանակ
    elif tool == "shop":
        await shop_command(update, context)
    elif tool == "buy_coins":
        await shop_command(update, context)
    elif tool == "wallet":
        await wallet_command(update, context)
    elif tool == "faucet":
        await faucet_command(update, context)
    
    # Քվիզ և փաստեր
    elif tool == "quiz":
        await quiz_command(update, context)
    elif tool == "fact":
        await fact_command(update, context)
    elif tool == "rules":
        await rules_command(update, context)
    elif tool == "help":
        await help_command(update, context)
    
    # Կազինո և XP
    elif tool == "leaderboard":
        await leaderboard_command(update, context)
    elif tool == "daily":
        await daily_command(update, context)
    elif tool == "xp":
        await xp_command(update, context)
        

async def vip_add(update, context):
    if update.effective_user.id != admin_id:
        return
    if not context.args:
        await update.message.reply_text("Usage: /vip_add <user_id>")
        return
    try:
        uid = int(context.args[0])
        user_info = init_user_data(type('obj', (object,), {'id': uid, 'username': '', 'full_name': ''}))
        user_info['subscription'] = True
        user_info['subscription_end'] = datetime.now() + timedelta(days=30)
        await update.message.reply_text(f"✅ VIP activated for user {uid} until {user_info['subscription_end']:%Y-%m-%d}")
    except:
        await update.message.reply_text("Invalid user ID")

async def vip_remove(update, context):
    if update.effective_user.id != admin_id:
        return
    if not context.args:
        await update.message.reply_text("Usage: /vip_remove <user_id>")
        return
    try:
        uid = int(context.args[0])
        if uid in user_data:
            user_data[uid]['subscription'] = False
            user_data[uid]['subscription_end'] = None
            await update.message.reply_text(f"❌ VIP removed from user {uid}")
        else:
            await update.message.reply_text("User not found")
    except:
        await update.message.reply_text("Invalid user ID")


def main():
    application = Application.builder().token(TOKEN).build()
    
    # Admin commands
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("stats", admin_stats_command))
    application.add_handler(CommandHandler("block", block_user))
    application.add_handler(CommandHandler("unblock", unblock_user))
    application.add_handler(CommandHandler("reply", reply_command))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern='^admin_'))
    
    # Core commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("destroy", destroy_command))
    application.add_handler(CommandHandler("channel", channel_command))
    application.add_handler(CommandHandler("referral", referral_command))
    application.add_handler(CommandHandler("search", admin_search))
    application.add_handler(CommandHandler("vip_add", vip_add))
    application.add_handler(CommandHandler("vip_remove", vip_remove))

    application.add_handler(CommandHandler("daily", daily_command))
    
    # Tools
    application.add_handler(CommandHandler("hash", hash_command))
    application.add_handler(CommandHandler("base64", base64_command))
    application.add_handler(CommandHandler("genpass", genpass_command))
    application.add_handler(CommandHandler("whois", whois_command))
    application.add_handler(CommandHandler("iplookup", iplookup_command))
    
    # Additional features
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("wallet", wallet_command))
    application.add_handler(CommandHandler("faucet", faucet_command))
    application.add_handler(CommandHandler("xp", xp_command))
    application.add_handler(CommandHandler("fact", fact_command))
    application.add_handler(CommandHandler("nmap", nmap_command))
    application.add_handler(CommandHandler("bruteforce", bruteforce_command))
    application.add_handler(CommandHandler("phish", phish_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CallbackQueryHandler(quiz_answer_handler, pattern='^quiz_answer:'))
    application.add_handler(CommandHandler("fullmenu", fullmenu_command))
    
    # Handlers
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(fullmenu_button_handler, pattern='^(casino|tools|shop|quiz|admin|full_menu|casino_xp|tools_hack|shop_wallet|quiz_facts|admin_panel)$'))
    application.add_handler(CallbackQueryHandler(tool_shortcut_handler, pattern='^(ip_tool|whois_tool|passgen_tool|hash_tool|nmap_tool|bruteforce_tool|phish_tool|quiz|fact|rules|help|leaderboard|daily|xp|shop|wallet|faucet|buy_coins)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()