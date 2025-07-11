from telegram import Update
from telegram.ext import ContextTypes

shop_items = {
    "1": {"name": "Premium Access", "price": 100},
    "2": {"name": "Hacker Badge", "price": 50},
    "3": {"name": "Dark Web Pass", "price": 200}
}

user_points = {}

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    points = user_points.get(user_id, 0)
    text = f"🛒 Welcome to the Hacker Shop\nYour Points: {points}\n\nItems:\n"
    for code, item in shop_items.items():
        text += f"{code}. {item['name']} - {item['price']} XP\n"
    text += "\nBuy using /buy <item_number>"
    await update.message.reply_text(text)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /buy <item_number>")
        return
    item_code = args[0]
    if item_code not in shop_items:
        await update.message.reply_text("Invalid item code.")
        return
    item = shop_items[item_code]
    user_points.setdefault(user_id, 0)
    if user_points[user_id] < item["price"]:
        await update.message.reply_text("❌ Not enough points.")
        return
    user_points[user_id] -= item["price"]
    await update.message.reply_text(f"✅ You purchased: {item['name']}")

def add_points(user_id, amount):
    user_points[user_id] = user_points.get(user_id, 0) + amount