
from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Commands & Features*"


        "🧠 /quiz - Answer cybersecurity and programming questions"

        "🧬 /xp - View your XP and level"

        "🎁 /daily - Claim your daily XP bonus"

        "📚 /fact - Get random tech facts"

        "💻 /hash - Generate hashes (MD5, SHA1, SHA256)"

        "🔐 /genpass - Generate a secure password"

     "🔎 /whois <domain> - Simulated WHOIS lookup"

        "🌍 /iplookup <ip> - Simulated IP geolocation"

        "🛠 /nmap <ip> - Simulated Nmap port scan"

        "🧨 /bruteforce - Simulated brute force attack"

        "🎣 /phish - Fake phishing simulation"

        "🏪 /shop - Hacker shop for XP items"

        "💳 /buy <item> - Purchase an item with XP"

        "📣 /referral - Get your referral link"

        "🏆 /leaderboard - View the top XP users"

        "👛 /wallet - View your crypto balance"

        "💸 /faucet - Simulated crypto drop"

        "📜 /rules - View bot usage rules"

        "\n*Note: All hacking tools are educational simulations.*",
        parse_mode="Markdown"
    )

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 *Bot Rules & Disclaimer*"


        "1. All features in this bot are fictional/simulated."

        "2. No real hacking, brute-force, or phishing is performed."

        "3. Use this bot for entertainment, education, and fun."

        "4. Do not use this bot to impersonate real threats."
        "\n*Stay safe, stay ethical.*",
        parse_mode="Markdown"
    )
