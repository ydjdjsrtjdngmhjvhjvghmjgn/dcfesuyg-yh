from telegram import Update
from telegram.ext import ContextTypes
import asyncio

async def nmap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = ' '.join(context.args) if context.args else '127.0.0.1'
    await update.message.reply_text(f"🔍 Scanning {target} with Nmap...")
    await asyncio.sleep(2)
    await update.message.reply_text("Open ports:\n22/tcp (SSH)\n80/tcp (HTTP)\n443/tcp (HTTPS)")

async def bruteforce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧨 Simulating brute force attack on dummy login...")
    for i in range(1, 6):
        await asyncio.sleep(1)
        await update.message.reply_text(f"Trying password {i * '123'}...")
    await update.message.reply_text("❌ Access denied. Brute force failed (as expected).")

async def phish_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎣 Creating fake phishing page (simulation)...")
    await asyncio.sleep(2)
    await update.message.reply_text("URL: http://fake-login-page.com (do NOT use for real phishing!)")