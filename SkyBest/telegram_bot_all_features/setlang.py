
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from db import set_lang
from lang import get_text

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("Հայերեն", callback_data="lang_hy")],
        [InlineKeyboardButton("Français", callback_data="lang_fr")]
    ]
    await update.message.reply_text(get_text(update.effective_user.id, "choose_lang"),
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def lang_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang_code = query.data.replace("lang_", "")
    set_lang(user_id, lang_code)
    from lang import langs
    await query.answer()
    await query.edit_message_text(langs[lang_code]["set_lang_success"])
