from telegram import Update
from telegram.ext import ContextTypes
import random

wallets = {}

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallets.setdefault(user_id, {"BTC": 0.001, "ETH": 0.02, "USDT": 15})
    wallet = wallets[user_id]
    text = "👛 Your Crypto Wallet:\n"
    for coin, amt in wallet.items():
        text += f"{coin}: {amt}\n"
    await update.message.reply_text(text)

async def faucet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallets.setdefault(user_id, {"BTC": 0.001, "ETH": 0.02, "USDT": 15})
    coin = random.choice(["BTC", "ETH", "USDT"])
    amount = round(random.uniform(0.001, 1), 3)
    wallets[user_id][coin] += amount
    await update.message.reply_text(f"💸 Faucet Drop: You received {amount} {coin}!")
