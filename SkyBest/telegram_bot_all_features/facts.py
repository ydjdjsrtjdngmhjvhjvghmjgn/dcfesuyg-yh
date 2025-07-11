
from telegram import Update
from telegram.ext import ContextTypes
import random

facts = [
    "Linux was created by Linus Torvalds in 1991.",
    "SHA256 is part of the SHA-2 cryptographic hash functions.",
    "Python is named after Monty Python, not the snake.",
    "Nmap is a powerful open-source network scanner.",
    "Cybersecurity is the practice of protecting systems, networks, and programs from attacks."
]

async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📚 Fact: {random.choice(facts)}")
