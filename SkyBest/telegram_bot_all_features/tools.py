
import hashlib
import base64
import random
import string
from telegram import Update
from telegram.ext import ContextTypes

async def hash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /hash <text>")
        return
    text = ' '.join(context.args)
    md5 = hashlib.md5(text.encode()).hexdigest()
    sha1 = hashlib.sha1(text.encode()).hexdigest()
    sha256 = hashlib.sha256(text.encode()).hexdigest()
    await update.message.reply_text(
        f"MD5: `{md5}`\nSHA1: `{sha1}`\nSHA256: `{sha256}`",
        parse_mode="Markdown"
    )

async def base64_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /base64 <encode|decode> <text>")
        return
    mode = context.args[0].lower()
    text = ' '.join(context.args[1:])
    try:
        if mode == "encode":
            result = base64.b64encode(text.encode()).decode()
        elif mode == "decode":
            result = base64.b64decode(text).decode()
        else:
            raise ValueError
        await update.message.reply_text(f"Result: `{result}`", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("Error: Invalid usage or base64 input.")

async def genpass_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    length = int(context.args[0]) if context.args and context.args[0].isdigit() else 12
    password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=length))
    await update.message.reply_text(f"🔐 Generated Password:\n`{password}`", parse_mode="Markdown")

async def whois_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /whois <domain>")
        return
    domain = context.args[0]
    await update.message.reply_text(
        f"📡 WHOIS lookup for `{domain}` (simulated):\n"
        f"Registrar: NameCheap, Inc.\n"
        f"Created: 2019-03-01\n"
        f"Expires: 2029-03-01\n"
        f"Status: Active\n",
        parse_mode="Markdown"
    )

async def iplookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /iplookup <ip>")
        return
    ip = context.args[0]
    await update.message.reply_text(
        f"🌍 IP Lookup for `{ip}` (simulated):\n"
        f"Country: Netherlands\n"
        f"City: Amsterdam\n"
        f"ISP: FakeISP BV\n"
        f"Organization: CyberDefense Sim",
        parse_mode="Markdown"
    )
