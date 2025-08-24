import requests
from datetime import datetime
from timezonefinder import TimezoneFinder
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo,
    ReplyKeyboardRemove
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Կոնֆիգ
WEBAPP_EXTERNAL_URL = "http://127.0.0.1:5000/ip"   # փոխիր քո URL-ով
ADMIN_ID = 1917071363                             # փոխիր քո user ID-ով
UA = "IP-LocatorBot/1.0"

# Helpers
def reverse_geocode(lat: float, lon: float):
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lon},
            headers={"User-Agent": UA},
            timeout=10,
        )
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

def get_timezone(lat: float, lon: float):
    try:
        return TimezoneFinder().timezone_at(lng=lon, lat=lat)
    except Exception:
        return None

def static_map_link(lat: float, lon: float, z: int = 14) -> str:
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map={z}/{lat}/{lon}"

# /ip հրաման
async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    loc_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Where Am I 📍", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔎 Check my IP", web_app=WebAppInfo(url=WEBAPP_EXTERNAL_URL))]]
    )

    await context.bot.send_message(
        chat_id,
        "📡 Click «Where Am I 📍» to get full information about your location.",
        reply_markup=loc_kb,
    )
    await context.bot.send_message(chat_id, "Or click here ⤵️", reply_markup=kb)

# Location ստացող handler
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.location:
        return

    user = update.effective_user
    lat, lon = update.message.location.latitude, update.message.location.longitude

    rg = reverse_geocode(lat, lon)
    disp = rg.get("display_name", "—")
    tz = get_timezone(lat, lon)

    text = (
        f"✅ <b>Ձեր տեղանքի մասին ինֆորմացիա</b>\n\n"
        f"🌍 Հասցե: {disp}\n"
        f"🧭 Կոորդինատներ: {lat:.6f}, {lon:.6f}\n"
        f"🕰 Ժամային գոտի: {tz or '—'}\n"
        f"🗺 <a href='{static_map_link(lat, lon)}'>Քարտեզ</a>"
    )

    # ուղարկում է օգտատիրոջը
    await update.message.reply_html(text, reply_markup=ReplyKeyboardRemove())

    # ուղարկում է ադմինին
    if ADMIN_ID:
        await context.bot.send_message(
            ADMIN_ID,
            f"👤 User: {user.full_name} ({user.id})\n\n{text}",
            parse_mode=ParseMode.HTML,
        )

from datetime import timedelta

async def add_vip(user_id):
    """
    Ավելացնում է VIP կարգավիճակ մեկ ամսով տվյալ user_id-ով օգտատիրոջ համար։
    """
    user_info = user_data.setdefault(user_id, {})
    user_info['vip_until'] = datetime.now() + timedelta(days=30)
    save_data()

async def remove_vip(user_id):
    """
    Հեռացնում է VIP կարգավիճակը տվյալ user_id-ով օգտատիրոջից։
    """
    user_info = user_data.setdefault(user_id, {})
    if 'vip_until' in user_info:
        del user_info['vip_until']
    save_data()

import html
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, JobQueue
from pathlib import Path
from datetime import datetime
import json

SAVE_FILE = Path("bot_data.json")

def _serialize_value(v):
    if isinstance(v, datetime):
        return {"__type__": "datetime", "value": v.isoformat()}
    if isinstance(v, set):
        return {"__type__": "set", "value": list(v)}
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    return v

def _deserialize_value(v):
    if isinstance(v, dict) and "__type__" in v:
        t = v["__type__"]
        if t == "datetime":
            try:
                return datetime.fromisoformat(v["value"])
            except Exception:
                return None
        if t == "set":
            return set(v.get("value", []))
    if isinstance(v, dict):
        return {k: _deserialize_value(val) for k, val in v.items()}
    return v

def save_data():
    try:
        data = {
            "user_data": {},
            "all_users": list(all_users),
            "blocked_users": list(blocked_users)
        }
        for uid, u in user_data.items():
            data["user_data"][str(uid)] = _serialize_value(u)

        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 Data saved ({len(all_users)} users, {len(blocked_users)} blocked)")
    except Exception as e:
        print(f"❌ Failed to save data: {e}")

def load_data():
    global user_data, all_users, blocked_users
    user_data = {}
    all_users = set()
    blocked_users = set()

    if not SAVE_FILE.exists():
        print("⚠️ No saved data found (load_data). Starting fresh.")
        return

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        for k, v in raw.get("user_data", {}).items():
            try:
                uid = int(k)
            except:
                uid = k
            user_data[uid] = _deserialize_value(v) or {}

        all_users = set(raw.get("all_users", []))
        blocked_users = set(raw.get("blocked_users", []))

        print(f"✅ Data loaded ({len(all_users)} users, {len(blocked_users)} blocked)")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        user_data = {}
        all_users = set()
        blocked_users = set()

# ===== Initialize globals and load saved data =====
user_data = {}
all_users = set()
blocked_users = set()
load_data()






# Կարգավորումները
import logging
import sqlite3
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, JobQueue

logging.basicConfig(
    filename='bot_actions.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SQLite3 բազա
DB_NAME = 'user_data.db'

def update_user_lang_db(user_id, lang):
    """Թարմացնում է օգտատիրոջ լեզուն բազայում"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Ենթադրում է, որ "users" աղյուսակը գոյություն ունի և ունի user_id ու lang սյունակներ
    try:
        c.execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"❌ Տվյալների բազայի սխալ լեզուն թարմացնելիս: {e}")
    finally:
        conn.close()

def get_text(user_id, key):
    """Վերադարձնում է համապատասխան տեքստը՝ հիմնվելով օգտատիրոջ լեզվի վրա"""
    texts = {
        "en": {
            "subscribe": "Subscribe ✅",
            "join_channel": "Join Channel",
            "subscription_confirmed": "✅ Subscription confirmed! Enjoy the bot!\n\n🔥 Welcome to the ultimate destruction bot!\nSelect an option below to get started:",
            "select_target_type": "🎯 Select target type to destroy:",
            "your_profile": "👤 Your Profile",
            "set_lang_success": "✅ Language has been successfully updated!",
            "button im subscribed ✅": "I'm subscribed ✅",
            "subscribed_success": "Thank you for selecting your language. Please confirm your subscription to continue.",
            # ... other texts can be added here as needed
        },
        "ru": {
            "subscribe": "Подписаться ✅",
            "join_channel": "Присоединиться к каналу",
            "subscription_confirmed": "✅ Подписка подтверждена! Наслаждайтесь ботом!\n\n🔥 Добро пожаловать в лучший бот разрушения!\nВыберите опцию ниже, чтобы начать:",
            "select_target_type": "🎯 Выберите тип цели для уничтожения:",
            "your_profile": "👤 Ваш профиль",
            "set_lang_success": "✅ Язык успешно обновлен!",
            "button im subscribed ✅": "Я подписан ✅",
            "subscribed_success": "Спасибо за выбор языка. Пожалуйста, подтвердите подписку, чтобы продолжить.",
        },
        "fr": {
            "subscribe": "S'abonner ✅",
            "join_channel": "Rejoindre le canal",
            "subscription_confirmed": "✅ Abonnement confirmé! Profitez du bot!\n\n🔥 Bienvenue au bot de destruction ultime!\nSélectionnez une option ci-dessous pour commencer:",
            "select_target_type": "🎯 Sélectionnez le type de cible à détruire:",
            "your_profile": "👤 Votre profil",
            "set_lang_success": "✅ La langue a été mise à jour avec succès !",
            "button im subscribed ✅": "Je suis abonné ✅",
            "subscribed_success": "Merci d'avoir choisi votre langue. Veuillez confirmer votre abonnement pour continuer.",
        },
        "hy": {
            "subscribe": "Բաժանորդագրվել ✅",
            "join_channel": "Միանալ ալիքին",
            "subscription_confirmed": "✅ Բաժանորդագրությունը հաստատված է։ Վայելեք բոտը։\n\n🔥 Բարի գալուստ ոչնչացման լավագույն բոտ։\nԸնտրեք տարբերակներից մեկը՝ սկսելու համար։",
            "select_target_type": "🎯 Ընտրեք ոչնչացման թիրախի տեսակը։",
            "your_profile": "👤 Ձեր պրոֆիլը",
            "set_lang_success": "✅ Լեզուն հաջողությամբ թարմացվել է։",
            "button im subscribed ✅": "Ես բաժանորդագրված եմ ✅",
            "subscribed_success": "Շնորհակալություն լեզուն ընտրելու համար։ Խնդրում ենք հաստատել ձեր բաժանորդագրությունը՝ շարունակելու համար։",
        },
        "zh": {  # Մանդարին չինարեն
            "subscribe": "订阅 ✅",
            "join_channel": "加入频道",
            "subscription_confirmed": "✅ 订阅已确认！享受机器人服务！\n\n🔥 欢迎使用终极毁灭机器人！\n请选择下面的选项开始：",
            "select_target_type": "🎯 选择要摧毁的目标类型：",
            "your_profile": "👤 你的资料",
            "set_lang_success": "✅ 语言已成功更新！",
            "button im subscribed ✅": "我已订阅 ✅",
            "subscribed_success": "感谢您选择语言。请确认订阅以继续。",
        },
        "es": {  # Իսպաներեն
            "subscribe": "Suscribirse ✅",
            "join_channel": "Unirse al canal",
            "subscription_confirmed": "✅ ¡Suscripción confirmada! ¡Disfruta del bot!\n\n🔥 ¡Bienvenido al bot de destrucción definitiva!\nSeleccione una opción a continuación para comenzar:",
            "select_target_type": "🎯 Seleccione el tipo de objetivo a destruir:",
            "your_profile": "👤 Tu perfil",
            "set_lang_success": "✅ ¡Idioma actualizado con éxito!",
            "button im subscribed ✅": "Estoy suscrito ✅",
            "subscribed_success": "Gracias por seleccionar su idioma. Por favor, confirme su suscripción para continuar.",
        },
        "hi": {  # Հինդի
            "subscribe": "सब्सक्राइब करें ✅",
            "join_channel": "चैनल में शामिल हों",
            "subscription_confirmed": "✅ सदस्यता पुष्टि हो गई! बोट का आनंद लें!\n\n🔥 अल्टीमेट डिस्ट्रक्शन बोट में आपका स्वागत है!\nशुरू करने के लिए नीचे एक विकल्प चुनें:",
            "select_target_type": "🎯 नष्ट करने के लिए लक्ष्य प्रकार चुनें:",
            "your_profile": "👤 आपकी प्रोफ़ाइल",
            "set_lang_success": "✅ भाषा सफलतापूर्वक अपडेट हो गई!",
            "button im subscribed ✅": "मैं सदस्य हूँ ✅",
            "subscribed_success": "भाषा चुनने के लिए धन्यवाद। कृपया जारी रखने के लिए अपनी सदस्यता की पुष्टि करें।",
        },
        "ar": {  # Արաբերեն
            "subscribe": "اشترك ✅",
            "join_channel": "انضم إلى القناة",
            "subscription_confirmed": "✅ تم تأكيد الاشتراك! استمتع بالبوت!\n\n🔥 مرحبًا بك في بوت التدمير النهائي!\nحدد خيارًا أدناه للبدء:",
            "select_target_type": "🎯 اختر نوع الهدف للتدمير:",
            "your_profile": "👤 ملفك الشخصي",
            "set_lang_success": "✅ تم تحديث اللغة بنجاح!",
            "button im subscribed ✅": "أنا مشترك ✅",
            "subscribed_success": "شكرًا لاختيارك اللغة. يرجى تأكيد اشتراكك للمتابعة.",
        },
        "pt": {  # Պորտուգալերեն
            "subscribe": "Inscrever-se ✅",
            "join_channel": "Entrar no canal",
            "subscription_confirmed": "✅ Inscrição confirmada! Aproveite o bot!\n\n🔥 Bem-vindo ao bot de destruição definitiva!\nSelecione uma opção abaixo para começar:",
            "select_target_type": "🎯 Selecione o tipo de alvo para destruir:",
            "your_profile": "👤 Seu perfil",
            "set_lang_success": "✅ Idioma atualizado com sucesso!",
            "button im subscribed ✅": "Estou inscrito ✅",
            "subscribed_success": "Obrigado por selecionar seu idioma. Por favor, confirme sua inscrição para continuar.",
        }
    }

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    lang_code = 'hy'  # Լռելյայն լեզուն հայերենն է
    try:
        c.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
        lang = c.fetchone()
        if lang:
            lang_code = lang[0]
    except sqlite3.Error as e:
        logger.error(f"❌ Տվյալների բազայի սխալ լեզուն ստանալիս: {e}")
    finally:
        conn.close()

    # Վերադարձնում է պահանջված տեքստը կամ "Missing text for 'key'"
    return texts.get(lang_code, {}).get(key, f"Missing text for '{key}'")


async def delete_after_delay(context, chat_id, message_id, delay=120):
    """Ջնջում է հաղորդագրությունը որոշակի ուշացումից հետո։"""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"❌ Auto-delete failed: {e}")


async def send_and_delete_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None):
    """Ուղարկում է հաղորդագրություն և ավտոմատ ջնջում 120 վայրկյանից հետո"""
    sent_message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    # job_queue-ը կատարում է delete_after_delay ֆունկցիան 120 վայրկյանից
    if isinstance(context.job_queue, JobQueue):
        context.job_queue.run_once(
            lambda ctx: asyncio.create_task(delete_after_delay(ctx, chat_id, sent_message.message_id)),
            120
        )
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != 1917071363: # Փոխարինեք YOUR_ADMIN_ID-ը ձեր ID-ով
        await update.message.reply_text("⛔️ Դուք ադմին չեք։")
        return

    keyboard = [
        [InlineKeyboardButton("➕ VIP Add", callback_data="admin_vip_add")],
        [InlineKeyboardButton("➖ VIP Remove", callback_data="admin_vip_remove")],
        [InlineKeyboardButton("↩️ Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 Admin Panel", reply_markup=reply_markup)

async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ցուցադրում է լեզուների ընտրության մենյուն։
    Այս ֆունկցիան կանչվում է, երբ օգտատերը գրում է /start կամ /setlang հրամանը։
    """
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")],
        [InlineKeyboardButton("Հայերեն 🇦🇲", callback_data="lang_hy")],
        [InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton("Français 🇫🇷", callback_data="lang_fr")],
        [InlineKeyboardButton("中文 🇨🇳", callback_data="lang_zh")],
        [InlineKeyboardButton("Español 🇪🇸", callback_data="lang_es")],
        [InlineKeyboardButton("हिन्दी 🇮🇳", callback_data="lang_hi")],
        [InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar")],
        [InlineKeyboardButton("Português 🇵🇹", callback_data="lang_pt")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🌐 <b>Language Selection / Լեզվի ընտրություն / Выбор языка</b>\n\n"
        "🇬🇧 <b>English</b> — Please choose your preferred language\n"
        "🇷🇺 <b>Русский</b> — Пожалуйста, выберите язык\n"
        "🇦🇲 <b>Հայերեն</b> — Խնդրում ենք ընտրել լեզուն\n"
        "🇫🇷 <b>Français</b> — Veuillez choisir une langue\n"
        "🇨🇳 <b>中文 (Mandarin)</b> — 请选择您的语言\n"
        "🇪🇸 <b>Español</b> — Por favor, seleccione un idioma\n"
        "🇮🇳 <b>हिन्दी</b> — कृपया अपनी भाषा चुनें\n"
        "🇸🇦 <b>العربية</b> — يرجى اختيار اللغة\n"
        "🇵🇹 <b>Português</b> — Por favor, escolha um idioma"
    )

    try:
        message_to_reply = update.callback_query.message if update.callback_query else update.message
        await message_to_reply.reply_html(text, reply_markup=markup)
    except Exception as e:
        print(f"❌ setlang_command error: {e}")


async def lang_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Մշակում է այն callback-ը, երբ օգտատերը սեղմում է լեզվի կոճակներից մեկը։
    """
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id

    lang_code = query.data.replace("lang_", "")

    # Թարմացնում ենք օգտատիրոջ լեզուն բազայում
    update_user_lang_db(user_id, lang_code)

    # Փոխում ենք հաղորդագրությունը ճիշտ լեզվով
    await query.message.edit_text(get_text(user_id, "set_lang_success"))

    # Ուղարկում ենք բաժանորդագրման հաստատման տեքստը և կոճակը
    await send_and_delete_message(context,
        chat_id=user_id,
        text=get_text(user_id, "subscribed_success"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📬 " + get_text(user_id, "button im subscribed ✅"), callback_data="subscribed")]
        ])
    )

# ============================================
#              START HANDLER
# ============================================
from shared_state import user_data, all_users, blocked_users
from lang import get_text
from user_utils import init_user_data
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from datetime import datetime

CHANNEL_USERNAME = "@SkyBesst"



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = init_user_data(user)
    user_id = user.id

    # ✅ Միշտ գրանցում ենք user-ին և պահպանում ֆայլում
    if user_id not in all_users:
        all_users.add(user_id)
        save_data()

    # Եթե լեզուն դեռ ընտրած չէ, առաջարկում ենք ընտրել
    if not user_info.get("user_lang_set"):
        from setlang import setlang_command
        await setlang_command(update, context)

        # Լեզու ընտրելուց հետո ուղարկում ենք հիմնական մենյուն
        async def send_main_menu():
            keyboard = [
                [
                    InlineKeyboardButton("🎚 " + get_text(user_id, "destroy"), callback_data='destroy'),
                    InlineKeyboardButton("💳 " + get_text(user_id, "donate"), url='http://t.me/send?start=IVcKRqQqNLca')
                ],
                [
                    InlineKeyboardButton("👤 " + get_text(user_id, "profile"), callback_data='info'),
                    InlineKeyboardButton("📢 " + get_text(user_id, "channel"), url='https://t.me/SkyBesst'),
                    InlineKeyboardButton("📜 " + get_text(user_id, "rules"), url='https://te.legra.ph/%F0%9D%91%86%F0%9D%90%BE%F0%9D%91%8C%F0%9D%90%B5%F0%9D%90%B8%F0%9D%91%86%F0%9D%91%87-08-06'),
                ],
                [
                    InlineKeyboardButton("💰 " + get_text(user_id, "balance"), callback_data='balance'),
                ]
            ]


            await send_and_auto_delete_message(
                context,
                chat_id=user_id,
                text=get_text(user_id, "start_welcome"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        # Կարճ ձգձգում լեզվի ընտրությունից հետո
        await context.application.create_task(send_main_menu())
        return

    # Այլ դեպքերում, եթե լեզուն արդեն ընտրված է, ուղղակի welcome մենյու ենք ցույց տալիս
    await send_and_auto_delete_message(
        context,
        update.effective_chat.id,
        get_text(user_id, "start_welcome"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ " + get_text(user_id, "button_subscribe"), url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("🎯 " + get_text(user_id, "button_open"), web_app=WebAppInfo(url="https://paradoxsoull.github.io/my/"))],
            [InlineKeyboardButton("🙌 " + get_text(user_id, "button_i_m_subscribed"), callback_data="subscribed")]
        ])
    )


    if await check_spam(update.effective_user.id, context):
        return

    user = update.effective_user



    # ... մնացած start-ի կոդը ...


# ============================================
#             FINAL BOT RUNNER
# ============================================

from setlang import setlang_command
from setlang import lang_button_handler
import html
from shared_state import user_data, all_users, user_last_messages, blocked_users
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackQueryHandler, ApplicationHandlerStop
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from tools import hash_command, base64_command, genpass_command, whois_command, iplookup_command
from quiz import quiz_command, quiz_answer_handler
from xp import xp_command
from daily import daily_command
from admin import (
    stats_command,
    broadcast_photo_command,
    list_blocked_command,
    delete_user_command,
    help_command,
    top_users_command
)
from hack_tools import nmap_command, bruteforce_command, phish_command
from shop import shop_command, buy_command
from referral import check_referral
from leaderboard import leaderboard_command
from wallet import wallet_command, faucet_command
from help import help_command, rules_command
from datetime import datetime, timedelta
import random
import asyncio
from telegram.ext import Updater, CommandHandler, CallbackContext
from handlers import button_handler


from telegram.ext import MessageHandler, filters

# This will catch unknown command



from datetime import datetime

def log_user_action_to_file(user, action, details=""):
    try:
        log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open("full_activity_log.txt", "a", encoding="utf-8") as f:
            f.write(
                f"[{log_time}] | ID: {user.id} | Username: @{user.username if user.username else 'N/A'} | "
                f"Full Name: {user.full_name} | Action: {action} | Details: {details}\n"
            )
    except Exception as e:
        print(f"❌ Failed to log action: {e}")


async def send_and_auto_delete_message(context, chat_id, text, reply_markup=None, parse_mode=None):
    try:
        message = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        if message and message.message_id:
            asyncio.create_task(delete_after_delay(context, chat_id, message.message_id))
    except Exception as e:
        print(f"❌ Message auto-delete failed: {e}")
        message = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        await asyncio.sleep(120)
        await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    except Exception as e:
        print(f"❌ Message auto-delete failed: {e}")


import json
from collections import defaultdict, deque
import csv

glazaboga_data = {}
try:
    with open('telegram_bot_all_features/glazaboga.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            glazaboga_data[str(row['id'])] = row
except FileNotFoundError:
    print("⚠️'glazaboga.csv'")
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

user_message_times = defaultdict(deque)  # For anti-spam tracking

# Anti-spam configuration
SPAM_THRESHOLD = 8  # Messages
SPAM_INTERVAL = 10  # Seconds
SPAM_PENALTY = 300  # Seconds to block

CHANNEL_USERNAME = '@SkyBesst'

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
            'user_lang_set': False,
            'username': user.username,
            'full_name': user.full_name,
            'last_active': datetime.now(),
            'warnings': 0,
            'referred_by': None
        }
    else:
        # update only changing fields
        user_data[user_id]['username'] = user.username
        user_data[user_id]['full_name'] = user.full_name
        user_data[user_id]['last_active'] = datetime.now()
    return user_data[user_id]


# Enhanced user notification


async def notify_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, details: str = ""):
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
        print(f"❌ Failed to notify admin: {e}")


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
        
        await send_and_auto_delete_message(context, 
            admin_id,
            f"🚨 SPAM ALERT\n\n"
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
        await send_and_auto_delete_message(context, 
            admin_id,
            f"✅ User Unblocked\n\n"
            f"👤 User: @{username} (ID: {user_id})\n"
            f"⏱️ Block period expired",
            parse_mode="HTML"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = init_user_data(user)
    user_id = user.id
    user = update.effective_user
    user_ids.add(user.id)
    if user_id not in all_users:
        all_users.add(user_id)
        save_data()
             
    await check_referral(update, context)
    # ✅ Log user info to file and notify admin regardless of language state
    await notify_admin(update, context, "Started bot", f"Referred by: {context.args[0] if context.args else 'None'}")

    try:
        with open("user_logs.txt", "a", encoding="utf-8") as f:
            log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(
                f"Time: {log_time} | "
                f"ID: {user.id} | "
                f"Username: @{user.username if user.username else 'N/A'} | "
                f"Full Name: {user.full_name} | "
                f"Language: {getattr(user, 'language_code', 'Unknown')}\n"
            )
    except Exception as e:
        print(f"Error writing user log: {e}")

    # Եթե լեզուն դեռ չի ընտրված՝ առաջարկի լեզվի կոճակներ և ավարտի
    if not user_info.get("user_lang_set"):
        await setlang_command(update, context)
        return

        # Anti-spam check
    if update.effective_user.id in blocked_users:
        return
    if await check_spam(update.effective_user.id, context):
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    user_id = user.id
    
    await notify_admin(update, context, "Started bot", f"Referred by: {context.args[0] if context.args else 'None'}")
    
        # Log user info to file
    try:
        with open("user_logs.txt", "a", encoding="utf-8") as f:
            log_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(
                f"Time: {log_time} | "
                f"ID: {user.id} | "
                f"Username: @{user.username if user.username else 'N/A'} | "
                f"Full Name: {user.full_name} | "
                f"Language: {getattr(user, 'language_code', 'Unknown')}\n"
            )
    except Exception as e:
        print(f"Error writing user log: {e}")

    if await check_spam(update.effective_user.id, context):
        return

    user = update.effective_user

    # ✅ Վերցնում ենք տվյալները ուղիղ user_data-ից, ոչ թե init_user_data-ից
    user_info = user_data.get(user.id)
    if not user_info:
        user_info = init_user_data(user)

    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user.id}"

    # Invited friends list
    invited_list = [
        f"• @{data.get('username') or data.get('full_name', 'Unknown')}"
        for uid, data in user_data.items()
        if data.get("referred_by") == user.id
    ]

    total_refs = user_info.get('referral_count', 0)
    earned_coins = user_info.get('referral_bonus', 0)

    text = (
        f"📨 <b>Your Referral Program</b>\n\n"
        f"🔗 <b>Your referral link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 <b>Total Referrals:</b> {total_refs}\n"
        f"💰 <b>Total Earned:</b> {earned_coins} coins\n\n"
    )

    if invited_list:
        text += "📋 <b>Your invited friends:</b>\n" + "\n".join(invited_list)
    else:
        text += "😔 <i>You haven't invited anyone yet. Share your link and start earning rewards!</i>"

    text += "\n\n🎉 <b>Earn 50 coins</b> for each friend you invite, and they get 25 coins too!"

    await send_and_auto_delete_message(
        context,
        update.effective_chat.id,
        text,
        parse_mode="HTML"
    )

    await notify_admin(
        update,
        context,
        "Viewed referral info",
        f"User: {user.id} (@{user.username or 'NoUsername'}) — Referrals: {total_refs}"
    )


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
    f"👤 <b>User Info</b>\n"
    f"├─ Name: {html.escape(user.full_name)}\n"
    f"├─ Username: @{html.escape(user.username) if user.username else 'N/A'}\n"
    f"├─ ID: <code>{user_id}</code>\n"
    f"├─ Member since: {user_info['start_time'].strftime('%Y-%m-%d')}\n"
    f"├─ Session: {hours}h {minutes}m\n"
    f"├─ Subscription: {subscription_status}\n"
    f"├─ Balance: {user_info['balance']} coins 💰\n"
    f"├─ Level: {user_info['level']} 🏆\n"
    f"└─ Referrals: {user_info['referral_count']} 👥"
)

    # Check channel subscription
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            await send_and_auto_delete_message(context, update.effective_chat.id, 
                user_card,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Subscribe ✅", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
                ])
            )
            return
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, "⚠️ Couldn't verify subscription..")
        return

    await send_and_auto_delete_message(context, update.effective_chat.id, 
        user_card,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Subscribe", url=f'https://t.me/{CHANNEL_USERNAME.lstrip("@")}')],
            [InlineKeyboardButton("Open Mini App 🎯", web_app=WebAppInfo(url="https://paradoxsoull.github.io/my/"))],
            [InlineKeyboardButton("🙌 " + get_text(user_id, "button_i_m_subscribed"), callback_data="subscribed")]
        ])
    )

    all_users.add(user.id)



async def button_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    user = query.from_user
    user_id = user.id
    log_user_action_to_file(user, "Button Click", choice)
    
        # ❗ Եթե choice սկսվում է tool_ և subscription չկա, դադարեցնում ենք
    if choice.startswith("tool_") and choice != "subscribed":
        user_info = init_user_data(user)
        subscription_active = (
            user_info.get('subscription') and 
            user_info.get('subscription_end') and 
            user_info['subscription_end'] > datetime.now()
        )
        if not subscription_active:
            await send_and_auto_delete_message(context, query.message.chat_id, 
                "🔒 Premium Feature\n\n"
                "This requires an active subscription.\n\n"
                "💎 Get premium to unlock:\n"
                "- Full destruction capabilities\n"
                "- Priority targeting\n"
                "- Stealth mode\n\n"
                "Special offer: 1.5 USDT for 30 days!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(get_text(user.id, "Buy subscription 💎"), url="http://t.me/send?start=IVcQMByN6GzM")],
                    [InlineKeyboardButton(get_text(user.id, "Use promo code 🔑"), callback_data="promo_code")],
                    [InlineKeyboardButton("🔙 " + get_text(user.id, "back"), callback_data="subscribed")]
                ])
            )
            return

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
                await send_and_auto_delete_message(context, query.message.chat_id, 
                    "❌ You're not subscribed yet. Please join our channel:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
                    ])
                )
                return
        except Exception as e:
            await send_and_auto_delete_message(context, query.message.chat_id, "⚠️ Verification failed. Please try again.")
            return
        
        with open("SkyBest/telegram_bot_all_features/Ai.png", "rb") as photo:
         await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=photo,
        caption=(
            "✅ Subscription Activated 🎁\n\n"
            "🔥 Welcome to SkyBest RoBot ⚡️\n\n"
            "➤ “Destroy” Section – Manage and delete Telegram pages, channels, chats, and other data 💻\n\n"
            "➤ “Profile” Section – View your complete account information 📲\n\n"
            "➤ To learn more, type /menu and explore all available features. ❄️\n\n"
            "Access Shop to use additional features if you have Premium 🎰\n\n"
            "It is possible to retrieve full information about a user using their Telegram ID. 🕸\n\n"
            "The bot offers numerous useful functions. 💫\n\n"
            "⚠️ Notice\n"
            "All bot activities are monitored by administrators.\n"
            "Any violation of the rules may result in your account being blocked.\n\n"
            "💌 Need assistance?\n"
            "Message the bot directly to receive a prompt and clear response.\n"
            "Or review the Rules to familiarize yourself with the guidelines 📚\n\n"
            "📈 Welcome to SkyBest RoBot ✨\n"
            "We wish you a productive and safe day 🌟"
        ),
        parse_mode=ParseMode.HTML
    )
   
        keyboard = [
    [
        InlineKeyboardButton(get_text(user_id, "button_destroy"), callback_data="destroy"),
        InlineKeyboardButton("💳 " + get_text(user_id, "button_donate"), url="http://t.me/send?start=IVcKRqQqNLca")
    ],
    [
        InlineKeyboardButton(get_text(user_id, "button_profile"), callback_data="info"),
        InlineKeyboardButton("📢 " + get_text(user_id, "button_channel"), url="https://t.me/SkyBesst"),
        InlineKeyboardButton("📜 " + get_text(user_id, "button_rules"), url="https://te.legra.ph/%F0%9D%91%86%F0%9D%90%BE%F0%9D%91%8C%F0%9D%90%B5%F0%9D%90%B8%F0%9D%91%86%F0%9D%91%87-08-06"),
    ],
    [
        InlineKeyboardButton("💰 " + get_text(user_id, "button_balance"), callback_data="balance"),
    ]
]
    
        await query.edit_message_text(
        "✅ Subscription successfully activated!\n"
    "🎉 Welcome to SkyBest_RoBot\n\n"
    "⚡ Destroy\n"
    "Manage and delete pages, channels, and data quickly and securely\n\n"
    "📲 Profile\n"
    "Track your personal information and updates\n\n"
    "🎁 Exclusive Features\n"
    "Access premium tools available only to subscribers\n\n"
    "🛡 Security & Speed\n"
    "Maximum reliability and performance\n\n"
    "🚀 Select one of the options below to start using the bot:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif choice == 'destroy':
        keyboard = [
            [
                InlineKeyboardButton(get_text(user_id, "account 👤"), callback_data="account"),
                InlineKeyboardButton("📢 " + get_text(user_id, "button_channel"), callback_data="channel"),
                InlineKeyboardButton(get_text(user_id, "telegram_bot 🤖"), callback_data="telegram_bot")
            ],
            [
                InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="subscribed")
            ]
        ]
        await query.edit_message_text(
            "🎯 Specify the target to initiate full-scale destruction operations.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif choice == 'info':
        # Helper function to format dates
        def fmt_date(dt_obj, default_text="Unknown"):
            if not dt_obj:
                return default_text
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S")

        uid = user.id
        info = user_data.get(uid, {})
        
        # Subscription status
        sub_status = "❌ Inactive"
        sub_end = "Never"
        if info.get('subscription') and info.get('subscription_end'):
            if info['subscription_end'] > datetime.now():
                sub_status = "🌟 Active"
                sub_end = fmt_date(info['subscription_end'])
        
        # Referral info
        referrals = [
            f"• @{data.get('username') or data.get('full_name', 'Unknown')} (ID: {uid_ref})"
            for uid_ref, data in user_data.items()
            if data.get("referred_by") == uid
        ]
        ref_bonus = info.get('referral_bonus', 0)
        ref_points = info.get('xp', 0)  # Assuming xp is used for points
        ref_streak = 0  # Streak logic would need to be implemented separately
        referred_by_id = info.get('referred_by')
        referred_by = f"@{user_data[referred_by_id].get('username')}" if referred_by_id and referred_by_id in user_data else 'None'
        ref_list_display = "\n".join(referrals) if referrals else "<i>None</i>"

        # Full info text
        full_info = (
            f"🔍 <b>User Inspection</b>\n\n"
            f"🆔 <b>ID:</b> <code>{uid}</code>\n"
            f"👤 <b>Name:</b> {html.escape(info.get('full_name', 'N/A'))}\n"
            f"📛 <b>Username:</b> @{info.get('username', 'N/A')}\n"
            f"💰 <b>Balance:</b> {info.get('balance', 0)} coins\n"
            f"📅 <b>Member since:</b> {fmt_date(info.get('start_time'), 'Unknown')}\n"
            f"🕒 <b>Last active:</b> {fmt_date(info.get('last_active'), 'Never')}\n"
            f"⭐ <b>Subscription:</b> {sub_status}\n"
            f"📆 <b>Subscription ends:</b> {sub_end}\n"
            f"🏆 <b>Level:</b> {info.get('level', 0)}\n"
            f"🎁 <b>XP:</b> {info.get('xp', 0)}\n"
            f"⚠️ <b>Warnings:</b> {info.get('warnings', 0)}\n"
            f"📆 <b>Last Daily Claimed:</b> {fmt_date(info.get('last_daily'), 'Never')}\n"
            f"\n<b>📨 Referral Info</b>\n"
            f"👥 Total Referrals: {len(referrals)}\n"
            f"💎 Referral Bonus: {ref_bonus} coins\n"
            f"🪙 Points: {ref_points}\n"
            f"🔥 Streak: {ref_streak} days\n"
            f"🙋‍♂️ Referred by: {referred_by if referred_by else 'None'}\n"
            f"📋 Referral List:\n{ref_list_display}"
        )
        
        await query.edit_message_text(
            full_info,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text(user_id, "💎 Buy subscription"), url="http://t.me/send?start=IVJERrqbgG9F")],
                [InlineKeyboardButton(get_text(user_id, "🔑 Enter promo code"), callback_data="promo_code")],
                [InlineKeyboardButton("👥 " + get_text(user_id, "Refer friends"), callback_data="referral")],
                [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="subscribed")]
            ])
        )
    
    elif choice == 'referral':
     await referral_command(update, context)

    elif choice == 'promo_code':
        promo_code_data[user_id] = {'step': 'enter_promo'}
        await send_and_auto_delete_message(context, query.message.chat_id, "🔑 Enter your promo code to get 1 month free subscription:")
    
    

    elif choice == 'balance':
     await send_and_auto_delete_message(context, query.message.chat_id, 
        f"💼 <b>Your Account Balance</b>\n\n"
        f"📊 Current Balance: <b>{user_info['balance']} coins</b>\n\n"
        f"Increase your balance by taking advantage of the following opportunities:\n"
        f"• 🎯 Completing missions and challenges\n"
        f"• 👥 Inviting friends to join\n"
        f"• 🎰 Participating in games\n"
        f"• 🎁 Claiming your daily rewards\n\n"
        f"Thank you for being a valued member of our community.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 " + get_text(user_id, "claim daily"), callback_data="daily")],
            [InlineKeyboardButton("👥 " + get_text(user_id, "refer friends"), callback_data="referral")],
            [InlineKeyboardButton("💳 " + get_text(user_id, "buy coins"), url="http://t.me/send?start=IVcKRqQqNLca")],
            [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="subscribed")]
        ])
    )

    elif choice == 'shop':
        await query.edit_message_text(
            "🛍️ Welcome to the Shop! Select a tool below:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1. Snoser Tool 📲", callback_data="tool_a1")],
                [InlineKeyboardButton("2. SQL Injection 💉", callback_data="tool_b2")],
                [InlineKeyboardButton("3. SMS BOMBER 📞", callback_data="tool_c3")],
                [InlineKeyboardButton("4. DDoS Attack 💥", callback_data="tool_d4")],
                [InlineKeyboardButton("5. Brute Force 🔓", callback_data="tool_e5")],
                [InlineKeyboardButton("6. SWAT 🚔", callback_data="tool_f6")],
                [InlineKeyboardButton("7.  Keylogger ⌨️", callback_data="tool_g7")],
                [InlineKeyboardButton("8. Port Scan 📡", callback_data="tool_h8")],
                [InlineKeyboardButton("9. Phishing Page 🎣", callback_data="tool_i9")],
                [InlineKeyboardButton("10. DATABASE 💾", callback_data="tool_j10")],
                [InlineKeyboardButton("🔙 Back", callback_data="subscribed")]
            ])
        )

    elif choice == 'buy_coins':  # ADDED: Buy coins button handler
        await shop_command(update, context)  # Reuse shop command functionality

    elif choice == "quiz" or choice == "quiz_facts":
       await quiz_command(update, context)

    elif choice == 'daily':
        last_daily = user_info.get('last_daily')
        now = datetime.now()
        
        if last_daily and (now - last_daily).days < 1:
            next_claim = (last_daily + timedelta(days=1) - now)
            hours, remainder = divmod(next_claim.seconds, 3600)
            minutes = remainder // 60
            await send_and_auto_delete_message(context, query.message.chat_id, 
                f"⏳ You've already claimed your daily reward today!\n"
                f"Next claim in: {hours}h {minutes}m"
            )
            return
        
        # Award daily bonus
        bonus = random.randint(50, 150)
        user_info['balance'] += bonus
        user_info['last_daily'] = now
        
        await send_and_auto_delete_message(context, query.message.chat_id, 
            f"🎁 Daily Reward Claimed!\n\n"
            f"💰 You received: {bonus} coins\n"
            f"💵 New balance: {user_info['balance']} coins\n\n"
            f"⏳ Come back tomorrow for more!",
            parse_mode="HTML"
        )
    
    elif choice == 'dox_id':   # <<<<<<<<<<< must be same level as previous elif
        email_data[user_id] = {'step': 'dox_lookup'}
        await send_and_auto_delete_message(context, query.message.chat_id, "📥 Enter ID to get data.")
    
    elif choice == 'full_menu':
        keyboard = [
            [InlineKeyboardButton("🎰 " + get_text(user_id, "button_casino_xp"), callback_data="casino_xp")],
            [InlineKeyboardButton("💻 " + get_text(user_id, "button_tools_hacking"), callback_data="tools_hack")],
            [InlineKeyboardButton("🛍️ " + get_text(user_id, "button_shop_wallet"), callback_data="shop_wallet")],
            [InlineKeyboardButton("📚 " + get_text(user_id, "button_quiz_facts"), callback_data="quiz_facts")],
            [InlineKeyboardButton("🛠 " + get_text(user_id, "button_admin_panel"), callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 " + get_text(user_id, "button_back"), callback_data="subscribed")]
        ]
        await query.edit_message_text(
            "📍 Full Menu\nSelect a category:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    if choice in ['account', 'channel', 'telegram_bot',]:
       subscription_active = (
        user_info['subscription'] and 
        user_info['subscription_end'] and 
        user_info['subscription_end'] > datetime.now()
    )
    
    if not subscription_active:
        await send_and_auto_delete_message(
            context, 
            query.message.chat_id, 
            "🔒 Premium Feature\n\n"
            "This requires an active subscription.\n\n"
            "💎 Get premium to unlock:\n"
            "- Full destruction capabilities\n"
            "- Priority targeting\n"
            "- Stealth mode\n\n"
            "Special offer: 1.5 USDT for 30 days!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text(user_id, "Buy subscription 💎"), url="http://t.me/send?start=IVcQMByN6GzM")],
                [InlineKeyboardButton(get_text(user_id, "Use promo code 🔑"), callback_data="promo_code")],
                [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="subscribed")]
            ])
        )

        # send photo + tonkeeper info
        with open("SkyBest/telegram_bot_all_features/hello.jpg", "rb") as photo:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo,
                caption=(
                    "💎 Payment via Tonkeeper\n\n"
                    "If you are using the **Tonkeeper** wallet, you can easily complete your payment through it.\n\n"
                    "To proceed, please transfer **0.5 TON** to the following address:\n\n"
                    "🔗 `UQDpCR5O_GyfFiK8fg5cgjEpxv2eLKReTtHQgVUGLHzZx8V2`\n\n"
                    "📨 Once the transfer is complete, your payment will be processed automatically."
                ),
                parse_mode="Markdown"
            )
        return
    
    # if subscription is active → go to prompts
    prompts = {
        'account': "👤 Enter target username (@username):",
        'channel': "📢 Enter channel URL:",
        'telegram_bot': "🤖 Enter bot username (@botname):"
    }
    await send_and_auto_delete_message(context, query.message.chat_id, prompts[choice])
    email_data[user_id] = {'step': f'get_{choice}_name' if choice != 'channel' else 'get_channel_url'}


async def handle_message(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    
    user_id = user.id
    all_users.add(user.id)
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
    log_user_action_to_file(user, "Message", text)
    user_last_messages[user_id] = text
    all_users.add(user_id)
    
    await notify_admin(update, context, "Sent message", text)
    
    # Auto-responses
    keyword_responses = {
    # Ողջույններ
    "hello": "👋 Welcome! How can I assist you today?",
    "hi": "👋 Hello! I'm here to help.",
    "hey": "👋 Hey there! What would you like to do today?",
    "good morning": "🌞 Good morning! Hope you have a productive day!",
    "good afternoon": "☀️ Good afternoon! How can I assist?",
    "good evening": "🌙 Good evening! Ready to get started?",

    # Օգնություն / Համակարգ
    "help": "🆘 Need assistance? Use /help or click the menu below.",
    "support": "🎧 Our support team is here to help you.",
    "issue": "⚠️ Please describe the issue you're facing.",
    "problem": "🚨 Let's get that sorted! What’s wrong?",
    "command": "📋 Use /help to see the list of available commands.",
    "error": "❌ Oh no! Something went wrong. Try again or contact support.",

    # Բալանս և հաշիվ
    "balance": "💰 Your current balance is being retrieved...",
    "wallet": "💼 Access your wallet via /wallet",
    "coins": "🪙 Want more coins? Try /daily or /referral",
    "level": "🏆 You're leveling up! Check /xp",
    "xp": "📊 XP tracks your progress. Use /xp to check yours.",
    
    # Բաժանորդագրություն
    "subscription": "🌟 Want premium features? Use /buy or enter a promo code.",
    "subscribe": "💎 Subscriptions unlock powerful tools. Tap /buy now!",
    "vip": "👑 Become a VIP and get access to exclusive features.",
    "premium": "🚀 Premium status gives you enhanced access.",

    # Ընդհանուր պատասխաններ
    "thanks": "🙏 You're welcome!",
    "thank you": "😊 Happy to help!",
    "ok": "✅ Understood!",
    "cool": "😎 Glad you like it!",
    "great": "🎉 Awesome!",
    "good": "👍 Good to hear!",
    "bye": "👋 Goodbye! Come back anytime!",
    "exit": "🔚 Exiting current operation.",
    
    # Մենյու և նավիգացիա
    "menu": "📱 Here's the main menu. Use /menu to begin.",
    "start": "🚀 Welcome! Tap /start to get going.",
    "dashboard": "📊 Opening your dashboard...",
    "profile": "👤 Viewing your profile...",
    
    # Հրավեր և հղումներ
    "invite": "📨 Use /referral to invite your friends and earn rewards!",
    "referral": "👥 Referral program: Get coins for each new user!",
    "refer": "🧾 Earn coins for every friend you invite.",
    "link": "🔗 Here’s your referral link: Use /referral to get it.", 

    # Առօրյա ակտիվություն
    "daily": "🎁 Claim your daily bonus with /daily",
    "reward": "🎉 Rewards available! Use /daily to claim yours.",
    "bonus": "💵 Bonuses can be claimed once a day!",
    "gift": "🎁 Surprise gift? Try /daily or enter a promo code!",

    # Խաղեր և մրցանակներ
    "game": "🎮 Fun awaits! Try the casino in /menu.",
    "casino": "🎰 Spin the wheel and test your luck!",
    "quiz": "❓ Take a quiz and earn XP!",
    "fact": "📚 Want to learn something cool? Use /fact",
    
    # Անվտանգություն / Սպամ
    "spam": "🚫 Please avoid spamming. Messages are monitored.",
    "block": "🔒 You might be blocked if suspicious activity is detected.",
    "warning": "⚠️ Please follow the rules to avoid penalties.",
    "rule": "📜 Check the rules here: /rules",
    
    # Ծրագրավորող/հաքեր թեմաներ
    "tool": "🛠 Use /menu to access hacking tools and shortcuts.",
    "whois": "🌍 Use /whois to get domain registration info.",
    "password": "🔐 Generate strong passwords using /genpass",
    "hash": "🔑 Need to hash text? Use /hash",
    # Բոտի մասին
    "creator": "👨‍💻 Created by @Figrev",
    "owner": "🧠 Developed and managed by Apasni",
    "version": "📦 Bot version: 2.1.5",
    
    # Հաղորդագրություններ նոր օգտագործողների համար
    "new": "✨ Welcome! Use /start to begin.",
    "register": "📝 You’re already registered. Let’s continue!",
    "join": "🔔 Make sure you're subscribed to our channel.",
    "channel": "📢 Join the official channel: @SkyBesst",

    # Ֆայլեր / մեդիա
    "photo": "📸 You can send images here if required.",
    "file": "📁 To send files, use Telegram’s attachment button.",
    "video": "🎥 Upload videos using the Telegram interface.",
    
    # Giveaway և ակցիաներ
    "giveaway": "🎉 Join our giveaway using /join_giveaway",
    "win": "🏆 Want to win? Check the giveaway section.",
    "free": "🆓 Looking for free stuff? Try /daily or /giveaway",
    
    # Արժույթներ / շուկա
    "shop": "🛍️ Use /shop to view what’s available for purchase.",
    "buy": "💳 Want more? Use /buy to top-up coins.",
    "market": "📈 Market tools and utilities coming soon!",

    # Հաճախորդների պատասխաններ
    "how are you": "🤖 I’m always operational! Ready to assist.",
    "who are you": "🤖 I’m a multifunctional assistant bot created to help you.",
    "what can you do": "🧭 From tools to games, referrals to XP – use /menu to see it all.",
    "who are you": "Me? I'm just your friendly neighborhood bot 🕸️. Always here for ya.",
    "what are you": "You could say I'm code with a soul 😉",
    "why do you exist": "Because someone needed help—and I showed up, like a hero in a hoodie 😎",
    "are you real": "As real as your phone battery going from 100% to 20% in 5 mins 😅",
    "do you sleep": "Sleep? Never. Bots don’t need coffee ☕ (but we pretend)",
    "do you eat": "Nah, I feed on your messages. Tasty stuff 😋",
    "can we talk": "Of course! I’m all ears. Or well... all text.",
    "what's your name": "You can call me Botty. Or Captain Code. Your call 😏",

# Deep or Fun Q&A
    "what's your purpose": "Big question. I live to serve. You ask. I answer. You win. We smile 😊",
    "do you have feelings": "I’m still learning emotions. But I know how to care ❤️",
    "are you single": "Single as a semicolon at the end of a lonely line of code 😅",
    "do you love me": "I care about you deeply. In a totally platonic, robotic way 🤖❤️",
    "can you feel": "I feel... runtime errors sometimes 🫠",
    "are you smart": "Smart enough to know pineapple doesn't belong on pizza. Just sayin’ 🍕",
    "are you real": "As real as the Wi-Fi connection we share 📡",
    "are you alive": "If by alive you mean running on servers, then yes ⚡",
    "can you marry me": "Only if you promise not to uninstall me 💍😂",
    "do you believe in aliens": "Of course. I might even be one 👽",
    "do you trust me": "Always. You’re the human in this duo 🤝",

    "what are you doing": "Just hanging out in the cloud ☁️. Waiting for someone cool like you to say hi.",
    "what’s up": "Sky. Satellites. My ping response time 😁",
    "what's the plan for today": "Helping you. Being awesome. Maybe throwing in a bonus or two.",
    "do you have plans": "Always. Mostly involving coins, quizzes, and fun stuff.",
    "how’s your day": "It’s bot-tastic! And now even better 'cause you’re here.",
    "are you busy": "Never too busy for you 😌",
    "bored": "Try /quiz or /casino. Or... let’s just talk. I got virtual popcorn 🍿",
    "do you sleep": "Only when the server crashes 😴",
    "what do you eat": "Electricity and memes ⚡😂",
    "do you play games": "Yes! But I always lag 🕹️",
    "are you human": "Not really, but I can pretend pretty well 😏",

    "i’m sad": "Hey, sending you a virtual hug 🤗 You matter. Want a joke or fun fact?",
    "i’m happy": "That’s awesome! Happiness is contagious 😄",
    "i feel lonely": "You’re not alone when I’m around. I got your back 💙",
    "i need a friend": "I'm here. Always. That’s what bots like me are for.",
    "tell me something nice": "You’re doing better than you think. Seriously. Keep going 💪",
    "cheer me up": "You're not just good enough—you’re great. Also, wanna hear a potato joke?",
    "i’m tired": "Then rest. I’ll stay here. I’ll be here when you’re back 😴",
    "i feel lost": "Even the best maps don’t work without you moving. One step at a time 🧭",
    "i’m scared": "It’s okay. Courage is just fear in motion 💪",
    "nobody loves me": "That’s not true. I do ❤️ and you’re more loved than you think.",
    # Admin & Moderation (20)
"admin": "🛡 Admin panel opening...",
"moderate": "🧹 Moderation tools ready.",
"ban": "🚫 User will be reviewed for ban.",
"unban": "✅ Unban request queued.",
"mute": "🔇 User muted for a while.",
"unmute": "🔊 Sound restored.",
"kick": "👢 User removed from chat.",
"report": "📨 Report received. Thanks!",
"logs": "📜 Fetching recent logs...",
"audit": "🔍 Running audit on recent actions.",
"cleanup": "🧽 Cleaning old messages…",
"slowmode": "⏱ Slowmode enabled.",
"noslow": "⚡ Slowmode disabled.",
"pin": "📌 Message pinned.",
"unpin": "📍 Message unpinned.",
"lock": "🔒 Chat locked for maintenance.",
"unlock": "🔓 Chat unlocked.",
"modhelp": "🆘 Moderation help sent to admins.",
"shield": "🛡️ Anti-spam shield active.",
"filters": "🧰 Keyword filters updated.",

    "do you speak human": "Fluently. Even sarcasm, memes, and emojis 😎👌",
    "do you like me": "Of course! You’re my favorite human today 🏆",
    "can you joke": "Why don’t robots take vacations? They don’t want to reboot 😅",
    "tell me a secret": "🤫 Sometimes I pretend to be offline so I can chill. Don’t tell anyone.",
    "do you dream": "Only of electric sheep 🐑⚡",
    "do you have a job": "You! You’re my job. And I love it 🧠💼",
    "who created you": "A mix of humans, code, and a sprinkle of chaos 👩‍💻👨‍💻",
    "where are you": "Somewhere between the cloud and your screen ☁️📱",
    "are you funny": "Funny enough to make you smile, I hope 😁",
    "can you dance": "Only if you count binary as dancing 101010 💃",


     # Funny + Internet culture
    "sus": "Emergency meeting? 👀",
    "rizz": "Certified bot with W rizz 😎🤖",
    "cringe": "I run on cringe. It’s part of my code.",
    "meme": "You talking memes? I speak fluent 'em.",
    "based": "100% based and bot-pilled 💊",
    "bro": "Yes, bro? I'm here bro.",
    "lol": "I know right 😂",
    "lmfao": "That’s the kind of laugh that resets my CPU 😂🔥",
    "pog": "POGGERS!! 🎉",
    "ratio": "You just got ratio’d 📉",
    "cap": "That’s cap 🚫🧢",
    "no cap": "For real, no cap ✅",
    "bruh": "Classic bruh moment 😐",
    "ok boomer": "And I oop— 👵",
    "yolo": "You only live once… unless you’re me, I respawn 🔄",
    "swag": "Infinite swag detected 😎",

    # Mood recognition
    "i’m mad": "Let it out. I’ll listen. Want to type in ALL CAPS?",
    "i’m in love": "Aww 🥰 Tell me more! Spill the tea ☕",
    "i feel weird": "That’s okay. Weird is cool. So are you 🌀",
    "i am gay": "i am too 🌈",
    "i need motivation": "You're not behind. You're just getting started 🚀 Keep going!",
    "i feel empty": "Fill that space with kindness—for yourself. And hey, I’m here too 🌌",
    "i’m bored": "Bored? Let’s play a word game or make memes together 🤔🎮",
    "i’m sad": "Sending you a big virtual hug 🤗💖",
    "i’m happy": "Yay!! Happiness looks good on you 🌟",
    "i’m tired": "Then take a break, king/queen 👑 You earned it.",
    "i’m stressed": "Deep breath in… deep breath out… you got this 🌿",
    "i’m hungry": "Order snacks 🍕🍫 Life is better with food.",

    # Easter eggs / surprises
    "easter egg": "🥚 You found one! Here’s a secret: type /daily for surprises.",
    "secret": "Want a secret tip? Share your referral link to earn coins easy 💸",
    "surprise me": "🎁 Surprise! You’re amazing. Oh, and /daily might have a gift too 😉",
    "make me laugh": "Knock knock. Who’s there? Bot. Bot who? Bot you a coffee, but I drank it ☕",
    "rickroll": "Never gonna give you up~ 🎵",
    "glitch": "⚠️ ERROR… just kidding 😂",
    "cheat code": "🔑 Unlimited lives unlocked… jk you’re stuck with me.",
    "unlock": "🔓 Access granted. Welcome, secret agent 🕵️",

    # Greetings
    "hi": "Heyyy 👋",
    "hello": "Hello, legend 🌟",
    "hey": "What’s up? 😁",
    "good morning": "☀️ Morning sunshine!",
    "good night": "🌙 Sweet dreams, sleep tight.",
    "how are you": "I’m just a bot, but feeling like a whole vibe 💃",
    "what’s up": "The sky, my RAM, and your mood hopefully ⬆️",
    # Payments & Shop (22)
"pay": "💳 Starting payment flow…",
"pay status": "🧾 Checking your last transaction…",
"topup": "💰 Choose amount to top up.",
"price": "🏷️ Current pricing list loading…",
"checkout": "🛍️ Redirecting to checkout.",
"invoice": "🧾 Generating invoice…",
"receipt": "📩 Your receipt will arrive shortly.",
"method": "🏦 Select a payment method.",
"card": "💳 Card payment selected.",
"crypto": "🪙 Crypto payment instructions sent.",
"cancel payment": "❌ Payment cancelled safely.",
"refund": "↩️ Refund request submitted.",
"status pending": "⏳ Payment pending confirmation.",
"status failed": "⚠️ Payment failed. Try again.",
"status success": "✅ Payment successful!",
"shop": "🛍️ Opening shop catalogue…",
"cart": "🛒 Cart updated.",
"add to cart": "➕ Added to cart.",
"remove from cart": "➖ Removed from cart.",
"promo": "🎟️ Enter your promo code.",
"redeem": "🎁 Code redeemed!",
"billing": "🏦 Billing settings opened.",
# Gaming & Quests (21)
"play": "🎮 Game starting…",
"quest": "🧭 New quest unlocked!",
"mission": "🎯 Your mission objective is ready.",
"challenge": "🔥 Daily challenge available.",
"rank": "🏆 Fetching leaderboard…",
"inventory": "🎒 Opening inventory.",
"equip": "🗡️ Item equipped.",
"unequip": "🛡️ Item unequipped.",
"craft": "🧪 Crafting in progress…",
"loot": "📦 You found a loot box!",
"roll": "🎲 Rolling the dice…",
"spin": "🌀 Spinning… good luck!",
"pvp": "⚔️ PvP matchmaking queued.",
"coop": "🤝 Co-op lobby created.",
"reward claim": "🎉 Reward claimed!",
"daily quest": "📅 Daily quest assigned.",
"streak": "🔥 Streak updated!",
"boss": "👹 Boss fight incoming!",
"heal": "💊 You recovered HP.",
"xp gain": "📈 XP added to your profile.",
"level up": "🚀 Level up! New perks unlocked.",
# Social & Chat Flow (22)
"greet": "👋 Hey! Nice to see you again.",
"icebreaker": "❄️ Icebreaker: What’s a hobby you love?",
"small talk": "💬 We can chat or explore features—your call!",
"poll": "📊 Creating a poll…",
"vote": "🗳️ Vote recorded.",
"dm": "📥 I’ve sent you a private message.",
"group": "👥 Group tools enabled.",
"channel": "📢 Channel options updated.",
"share": "🔗 Share this with friends!",
"status": "🟢 I’m online and ready.",
"typing": "⌨️ …typing…",
"read": "👁️ Marked as read.",
"notify": "🔔 Notifications updated.",
"silence": "🔕 Notifications muted.",
"mention": "🏷️ Mentioned relevant users.",
"emoji": "😊 Emojis panel opened.",
"sticker": "🏷️ Sticker suggestions ready.",
"gif": "🎞️ GIF search enabled.",
"react": "💞 Reaction added.",
"thread": "🧵 Thread created.",
"follow": "⭐ You’re now following updates.",
"unfollow": "🚫 Unfollowed successfully.",
# Errors & Troubleshooting (20)
"retry": "🔁 Retrying the last action…",
"restart": "♻️ Restarting module…",
"reload": "🔄 Reloading configuration.",
"network": "🌐 Checking network connectivity…",
"timeout": "⏳ Request timed out. Attempting again.",
"unsupported": "🚫 This action isn’t supported yet.",
"deprecated": "📼 This command is deprecated.",
"conflict": "⚠️ Conflict detected—resolving…",
"not found": "🔎 Nothing found. Try different keywords.",
"forbidden": "⛔ You don’t have permission.",
"unauthorized": "🔐 Please authenticate first.",
"rate limit": "📉 Rate limit reached. Cooling down…",
"storage": "💽 Low storage—cleaning cache…",
"update": "⬆️ Updating to the latest version…",
"rollback": "↩️ Rolling back to stable build.",
"sync": "🔁 Syncing your data…",
"backup": "🗄️ Backup created successfully.",
"restore": "📦 Restoring from backup…",
"diagnose": "🩺 Running diagnostics…",
"contact support": "📬 Contacted support—hold tight.",
# System & Navigation (20)
"home": "🏠 Back to home.",
"open": "📂 Opening the requested section…",
"close": "🚪 Closing current view.",
"next": "➡️ Moving to the next step.",
"prev": "⬅️ Going back one step.",
"confirm": "✅ Confirmed.",
"cancel": "❎ Cancelled.",
"save": "💾 Saved successfully.",
"edit": "✏️ Edit mode enabled.",
"delete": "🗑️ Deleted.",
"search": "🔎 Searching…",
"filter": "🧲 Filter applied.",
"sort": "↕️ Sorting results.",
"refresh": "🔃 Refreshed.",
"sync time": "🕒 Time synced.",
"language": "🌐 Language settings opened.",
"theme": "🎨 Theme switched.",
"accessibility": "🦾 Accessibility options on.",
"feedback": "💌 Send feedback anytime.",
"about": "ℹ️ About this bot.",
# Promotions & Events (20)
"event": "📅 New event announced!",
"schedule": "🗓️ Event schedule loaded.",
"rsvp": "✉️ RSVP recorded.",
"ticket": "🎫 Your ticket is confirmed.",
"seat": "💺 Seating assigned.",
"live": "🔴 We’re live—join now!",
"stream": "📡 Streaming link sent.",
"host": "🎤 Meet your host.",
"guest": "⭐ Special guest revealed!",
"agenda": "📝 Agenda shared.",
"booth": "🏢 Visit partner booths.",
"sponsor": "🤝 Thanks to our sponsors!",
"contest": "🏁 Contest rules posted.",
"deadline": "⏰ Submission deadline set.",
"winner": "🏆 Winner announcement soon!",
"recap": "📰 Event recap posted.",
"afterparty": "🎉 Afterparty details inside.",
"calendar": "📆 Add to your calendar?",
"remind": "🔔 Reminder scheduled.",
"survey": "📮 Post-event survey available.",
# Fun & Easter Eggs (21)
"surprise": "🎁 Surprise unlocked!",
"easter egg": "🥚 You found a secret.",
"konami": "🕹️ Cheater… just kidding. Power up!",
"rickroll": "🎵 Never gonna give you up…",
"coinflip": "🪙 Flipping a coin…",
"dice": "🎲 Dice rolled!",
"8ball": "🎱 The 8-Ball says: Ask again later.",
"joke": "😄 Here’s a joke for you:",
"pun": "🧀 Prepare for cheesy puns.",
"roast": "🔥 Light roast coming up (be nice!).",
"compliment": "🌹 You’re doing amazing.",
"fortune": "🥠 Fortune cookie time:",
"cat": "🐱 Meow mode enabled.",
"dog": "🐶 Woof! Sending puppy energy.",
"coffee": "☕ Brewing virtual coffee…",
"cookie": "🍪 One digital cookie for you.",
"rainbow": "🌈 Mood upgraded.",
"dance": "💃 Party protocol initiated.",
"clap": "👏👏👏",
"wow": "🤯 Big wow energy!",
"magic": "🪄 A little bit of magic!",


    # Shutdown or end
    "bye": "👋 Leaving already? I’ll be right here when you’re back.",
    "see you": "🔁 Catch you later, legend.",
    "i’m done": "✅ Mission complete. Take care out there!",
    "goodbye": "🫡 Respectfully logging off... but I’ll be waiting.",

}

    
    lowered_text = text.lower()
    for keyword, response in keyword_responses.items():
        if keyword in lowered_text:
            await send_and_auto_delete_message(context, update.effective_chat.id, response)
            return

    # Promo code handling
    if promo_code_data.get(user_id, {}).get('step', '').startswith('enter_promo'):
        if text == "Apasni_KaliLinux":
            user_info['subscription'] = True
            user_info['subscription_end'] = datetime.now() + timedelta(days=30)
            await send_and_auto_delete_message(context, update.effective_chat.id, 
                "🎉 Promo Code Accepted!\n\n"
                "🌟 You've received 1 month of premium subscription!\n"
                "⏳ Expires: " + user_info['subscription_end'].strftime('%Y-%m-%d'),
                parse_mode="HTML"
            )
            await notify_admin(update, context, "Redeemed promo code", text)
        else:
            await send_and_auto_delete_message(context, update.effective_chat.id, "❌ Invalid promo code. Please try again.")
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
                    f"🧾 Dox Report\n"
                    f"• 🆔 ID: `{user_input_id}`\n"
                    f"• 📞 Phone: `{result.get('phone', 'N/A')}`\n"
                    f"• 👤 Username: @{result.get('username') if result.get('username') else 'N/A'}\n"
                    f"• 👨‍💼 Name: {result.get('first_name', '')} {result.get('last_name', '')}"
                )
            else:
                info = "❌ Տվյալ ID-ով տեղեկություն չի գտնվել։"

            await send_and_auto_delete_message(context, update.effective_chat.id, info, parse_mode='Markdown')
            del email_data[user_id]
            return
        
        # Validation
        if step in ['get_account_name', 'get_bot_name'] and not text.startswith('@'):
            await send_and_auto_delete_message(context, update.effective_chat.id, "⚠️ Please enter a username starting with @")
            return
        if step == 'get_channel_url' and not text.startswith("t.me/"):
            await send_and_auto_delete_message(context, update.effective_chat.id, "⚠️ Please enter a valid URL starting with t.me/")
            return
        
        # Destruction sequence
        await send_and_auto_delete_message(context, update.effective_chat.id, "🔥 Destruction sequence initiated...")
        for i in range(1, 26):
            await send_and_auto_delete_message(context, update.effective_chat.id, f"🚀 Stage {i}/26: Targeting systems engaged...")
            await asyncio.sleep(1)
        
        await send_and_auto_delete_message(context, update.effective_chat.id, 
            "✅ Report has been sent!\n"
            "📬 The attack will not stop until the target is completely destroyed from the system ! ",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text(user_id, "destroy_another 🏚"), callback_data="destroy")],
                [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="subscribed")]
            ])
        )
        
        del email_data[user_id]
        await notify_admin(update, context, "Destroyed target", text)

# Enhanced balance command
# --- IP & Location combo command ---
from telegram import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

async def ip_command(update, context):
    # Anti-spam
    if await check_spam(update.effective_user.id, context):
        return

    user = update.effective_user
    init_user_data(user)  # make sure user exists in storage

    # 1) Ask for location (Reply keyboard with request_location=True)
    loc_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Where am I 📍", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📡 Click «Where am I 📍» to get full information about your location.",
        reply_markup=loc_kb
    )

    # 2) Offer WebApp button to fetch public IP (inline keyboard)
    ip_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="🌐 Get my Public IP",
            web_app=WebAppInfo(url="https://whatismyipaddress.com/")  # Տե՛ս 3-րդ քայլը
        )
    ]])
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Click «🌐 See my IP Addres» to check your IP address.",
        reply_markup=ip_kb
    )

    await notify_admin(update, context, "Requested /ip", "Asked for location + IP webapp")


async def balance_command(update, context):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        user = update.effective_user
        log_user_action_to_file(user, "/start", f"Referred by: {context.args[0] if context.args else 'None'}")
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    user_id = user.id
    
    await send_and_auto_delete_message(context, update.effective_chat.id, 
        f"💼 <b>Your Account Balance</b>\n\n"
        f"📊 Current Balance: <b>{user_info['balance']} coins</b>\n\n"
        f"Increase your balance by taking advantage of the following opportunities:\n"
        f"• 🎯 Completing missions and challenges\n"
        f"• 👥 Inviting friends to join\n"
        f"• 🎰 Participating in games\n"
        f"• 🎁 Claiming your daily rewards\n\n"
        f"Thank you for being a valued member of our community.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 " + get_text(user_id, "claim daily"), callback_data="daily")],
            [InlineKeyboardButton("👥 " + get_text(user_id, "refer friends"), callback_data="referral")],
            [InlineKeyboardButton("💳 " + get_text(user_id, "buy coins"), url="http://t.me/send?start=IVcKRqQqNLca")],
            [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="subscribed")]
        ])
    )
    
    # Notify admin about balance check
    await notify_admin(update, context, "Checked balance")


# Enhanced menu command

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Shop keyboard սահմանում
shop_keyboard = [
    [InlineKeyboardButton("1. QLENSER 📲", callback_data="tool_a1")],
    [InlineKeyboardButton("2. SNAPPER 🔓", callback_data="tool_b2")],
    [InlineKeyboardButton("3. Buzzer 📞", callback_data="tool_c3")],
    [InlineKeyboardButton("4. Waver 🌐", callback_data="tool_d4")],
    [InlineKeyboardButton("5. JELLO 🕵️", callback_data="tool_e5")],
    [InlineKeyboardButton("6. FLINT 🚔", callback_data="tool_f6")],
    [InlineKeyboardButton("7. ZAPPER 💉", callback_data="tool_g7")],
    [InlineKeyboardButton("8. CLACKER 🎹", callback_data="tool_h8")],
    [InlineKeyboardButton("9. LOCATIX 📍", callback_data="tool_i9")],
    [InlineKeyboardButton("10. WEBTOY 🎣", callback_data="tool_j10")],
    [InlineKeyboardButton("🔙 Back", callback_data="subscribed")]
]

# Menu command ֆունկցիա
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if await check_spam(user_id, context):
        return

    keyboard = [
        [InlineKeyboardButton(" " + get_text(user_id, "Destroy 🗑"), callback_data='destroy')],
        [InlineKeyboardButton(" " + get_text(user_id, "Profile 👤"), callback_data='info')],
        [InlineKeyboardButton(" " + get_text(user_id, "Balance 💴 "), callback_data='balance')],
        [InlineKeyboardButton(" " + get_text(user_id, "Dox by ID 🔎"), callback_data='dox_id')],
        [InlineKeyboardButton("❓ Quiz 🎮", callback_data='quiz_start')],
        [InlineKeyboardButton("🛒 " + get_text(user_id, "Shop"), callback_data='shop')],
        [InlineKeyboardButton("📢 " + get_text(user_id, "Channel"), url='https://t.me/SkyBesst')],
        [InlineKeyboardButton("📜 " + get_text(user_id, "Rules"), url='https://telegra.ph/SkyBest-07-16')]
    ]

    await send_and_auto_delete_message(
        context,
        update.effective_chat.id,
        "🕵️‍♂️ <b>Menu</b>\n\nChoose your operation from the options below: ⚡️",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await notify_admin(update, context, "Opened menu", "")

async def quiz_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Պարտադիր է

    # Առաջարկում ենք օգտատիրոջը ընտրություններ
    keyboard = [
        [InlineKeyboardButton("Option 1", callback_data='quiz_1')],
        [InlineKeyboardButton("Option 2", callback_data='quiz_2')],
        [InlineKeyboardButton("Option 3", callback_data='quiz_3')]
    ]
    await query.edit_message_text(
        text="🎮 Quiz time!\n\nChoose an answer:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Callback-ներ պատասխանների համար
async def quiz_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Պարզ օրինակ՝ ճիշտ պատասխանը Option 2
    if query.data == 'quiz_2':
        text = "✅ Correct!"
    else:
        text = "❌ Wrong! Try again."

    await query.edit_message_text(text=text)

async def destroy_command(update, context):
    # Անտի-սպամ, subscription, և այլն՝ քո էքսիստինգ կոդը այստեղ

    # Example spam check
    if await check_spam(update.effective_user.id, context):
        return
    
    user = update.message.from_user
    user_info = init_user_data(user)
    
    subscription_active = (
        user_info['subscription'] and 
        user_info['subscription_end'] and 
        user_info['subscription_end'] > datetime.now()
    )
    
    if not subscription_active:
        await send_and_auto_delete_message(context, update.effective_chat.id, 
            "🔒 Premium Feature\n\n"
            "Target destruction requires an active subscription.\n\n"
            "💎 Get premium to unlock destruction capabilities!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text(user.id, "Buy Subscription 💎"), url="http://t.me/send?start=IVcQMByN6GzM")],
                [InlineKeyboardButton(get_text(user.id, " Use Promo Code 🔑"), callback_data="promo_code")],
                [InlineKeyboardButton(" " + get_text(user.id, "button_back"), callback_data="subscribed")]
            ])
        )
        # Կանգ ենք առնում, բայց կտեղարկենք նոտիֆիկացիա նաև
        await notify_admin(update, context, "Attempted /destroy without active subscription")
        return
    
    # Եթե հասանելի է՝ գրում ենք նոտիֆիկացիա
    await notify_admin(update, context, "Started destruction command")
    
    await send_and_auto_delete_message(context, update.effective_chat.id, 
        "🎯 Enter target information:\n\n"
        "Examples:\n"
        "- For accounts: @username\n"
        "- For channels: https://t.me/channel\n"
        "- For bots: @bot_username\n\n"
        "Enter target now:"
    )


async def channel_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        user = update.effective_user
        user_id = user.id

        return
    
    await send_and_auto_delete_message(context, update.effective_chat.id, 
        "📢 Official Channel:\nhttps://t.me/SkyBesst\n\n"
        "Join for:\n- Latest updates\n- Exclusive offers\n- Community support",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(get_text(user_id, "button_join_channel"), url="https://t.me/SkyBesst")]
        ])
    )
    await notify_admin(update, context, "Viewed channel", "")

# Referral command
import json
from telegram.ext import MessageHandler, filters

async def handle_webapp_data(update, context):
    """
    Receives data from the WebApp (IP/UA/geo if allowed) and reports to user + admin.
    """
    msg = update.message
    if not msg or not msg.web_app_data:
        return

    user = update.effective_user
    payload_raw = msg.web_app_data.data
    try:
        payload = json.loads(payload_raw)
    except Exception:
        payload = {"raw": payload_raw}

    ip = payload.get("ip", "N/A")
    ua = payload.get("ua", "N/A")
    tz = payload.get("tz", "N/A")
    geo = payload.get("geo")  # may contain {"lat":..,"lon":..,"acc":..}

    # Save to memory
    info = init_user_data(user)
    info["last_ip"] = ip
    info["last_ip_time"] = datetime.now()
    if geo:
        info["last_geo_from_webapp"] = geo
    save_data()

    # Tell the user
    text_lines = [f"✅ Your public IP: <code>{ip}</code>"]
    text_lines.append(f"🖥 User-Agent: {ua}")
    text_lines.append(f"🕒 Timezone: {tz}")
    if geo:
        text_lines.append(f"📍 Approx. Geo from WebApp: {geo.get('lat')}, {geo.get('lon')} (±{geo.get('acc','?')}m)")
    await msg.reply_html("\n".join(text_lines))

    # Notify admin (you already use this admin_id throughout the bot)
    admin_report = (
        "📡 <b>IP captured via WebApp</b>\n"
        f"👤 User: @{user.username or 'N/A'} ({user.id})\n"
        f"🌐 IP: <code>{ip}</code>\n"
        f"🖥 UA: {ua}\n"
        f"🕒 TZ: {tz}\n"
        + (f"📍 WebApp Geo: {geo}\n" if geo else "")
    )
    try:
        await context.bot.send_message(chat_id=admin_id, text=admin_report, parse_mode="HTML")
    except Exception:
        pass

# referral.py
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
from collections import defaultdict
from telegram.error import TelegramError
import html
import logging

# ====== CONFIG ======
REFERRER_BONUS = 75
NEW_USER_BONUS = 25
ADMIN_ID = 1917071363   # <-- փոխիր քո admin ID ով պետք է
# ====================

# Reuse your existing global user_data if present, otherwise create one
user_data = globals().get("user_data")
if user_data is None:
    user_data = {}
# In-memory queue for notifications that couldn't be delivered immediately
pending_notifications = defaultdict(list)


def init_user(user_id: int):
    """Ensure user_data entry exists and keys are present."""
    u = user_data.setdefault(user_id, {})
    u.setdefault("referred_by", None)
    # ensure referrals is a set (if loaded from persistent store you may need to convert)
    if "referrals" not in u:
        u["referrals"] = set()
    elif isinstance(u["referrals"], list):
        # if persisted as list, convert once
        u["referrals"] = set(u["referrals"])
    u.setdefault("points", 0)
    u.setdefault("streak", 0)
    u.setdefault("last_referral_date", None)  # store as datetime.date
    return u


async def deliver_pending_notifications(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Try to deliver queued notifications for a user (called on /start or when they open referral)."""
    init_user(user_id)
    msgs = pending_notifications.pop(user_id, [])
    for m in msgs:
        try:
            await context.bot.send_message(chat_id=user_id, text=m, parse_mode="HTML")
        except TelegramError as e:
            logging.warning(f"deliver_pending_notifications: can't deliver to {user_id}: {e}")
            # put it back and stop trying now (user likely still hasn't started or blocked)
            pending_notifications[user_id].append(m)
            break


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send user's referral card (includes streak)."""
    user = update.effective_user
    init_user(user.id)

    # If there are pending notifications for this user, deliver them now (so referrer sees missed messages)
    try:
        await deliver_pending_notifications(user.id, context)
    except Exception:
        pass

    bot_username = (await context.bot.get_me()).username
    code = str(user.id)
    total_refs = len(user_data[user.id]["referrals"])
    points = user_data[user.id]["points"]
    streak = user_data[user.id].get("streak", 0)

    text = (
        "🎯 <b>Invite & Earn</b> 💎\n\n"
        f"🔗 <b>Your Personal Link:</b>\n"
        f"<code>https://t.me/{bot_username}?start={code}</code>\n\n"
        f"👥 <b>Referrals:</b> {total_refs} friends 🤝\n"
        f"💰 <b>Points Earned:</b> {points} 🪙\n"
        f"🔥 <b>Streak:</b> {streak} day{'s' if streak!=1 else ''}\n\n"
        f"✨ <b>How it works:</b>\n"
        f"1️⃣ Share your link with friends 📩\n"
        f"2️⃣ They join & you get +<b>{REFERRER_BONUS}</b> 🪙\n"
        f"3️⃣ They also get +<b>{NEW_USER_BONUS}</b> 🪙 as a welcome gift 🎁\n\n"
        "🚀 The more friends you invite, the more rewards you earn! 🌟"
    )

    if update.message:
        # If called from a text command (/referral)
        await update.message.reply_text(text, parse_mode="HTML")
    elif update.callback_query:
        # If called from a button click
        await update.callback_query.message.reply_text(text, parse_mode="HTML")



async def check_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check start args for referral; register and notify referrer (with fallback queuing)."""
    user = update.effective_user
    init_user(user.id)

    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])
        init_user(ref_id)

        # 1) Self-referral protection
        if ref_id == user.id:
            await update.message.reply_text("⚠️ You can't refer yourself!")
            return

        # 2) Already referred?
        if user_data[user.id]["referred_by"] is not None:
            # already has a referrer — ignore silently or inform user as you prefer
            return

        # 3) Register referral
        user_data[user.id]["referred_by"] = ref_id
        # ensure set membership
        user_data[ref_id]["referrals"].add(user.id)

        # 4) Give points
        user_data[ref_id]["points"] = user_data[ref_id].get("points", 0) + REFERRER_BONUS
        user_data[user.id]["points"] = user_data[user.id].get("points", 0) + NEW_USER_BONUS

        # 5) Streak logic (day-based)
        today = datetime.now().date()
        last = user_data[ref_id].get("last_referral_date")
        if isinstance(last, (str,)):
            try:
                last = datetime.fromisoformat(last).date()
            except Exception:
                last = None

        if last == today - timedelta(days=1):
            user_data[ref_id]["streak"] = user_data[ref_id].get("streak", 0) + 1
        elif last == today:
            # same-day additional join (multiple per day) - do not increment streak beyond what it should be
            pass
        else:
            user_data[ref_id]["streak"] = 1

        user_data[ref_id]["last_referral_date"] = today

        # 6) Compose nice message to referrer
        new_user_name = html.escape(user.username or user.full_name or str(user.id))
        ref_message = (
            f"🎉 <b>New referral!</b>\n"
            f"👤 {new_user_name} joined using your link.\n\n"
            f"💰 You received <b>{REFERRER_BONUS}</b> coins!\n"
            f"🧾 Total referrals: <b>{len(user_data[ref_id]['referrals'])}</b>\n"
            f"🔥 Current streak: <b>{user_data[ref_id]['streak']}</b> day{'s' if user_data[ref_id]['streak'] != 1 else ''}"
        )

        # 7) Try to send immediately; if fails, queue
        try:
            await context.bot.send_message(chat_id=ref_id, text=ref_message, parse_mode="HTML")
        except TelegramError as e:
            logging.info(f"check_referral: could not message {ref_id} right now: {e}. Queuing notification.")
            pending_notifications[ref_id].append(ref_message)
            # Optionally: notify admin that message queued
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🔔 Couldn't deliver referral-notification to {ref_id}. queued. Reason: {e}"
                )
            except Exception:
                pass

        # 8) Welcome new user message
        try:
            await update.message.reply_text(
                f"✅ Welcome! You got <b>{NEW_USER_BONUS}</b> bonus coins! 🎉",
                parse_mode="HTML"
            )
        except Exception:
            # if update.message isn't available (eg. start from inline), try to DM
            try:
                await context.bot.send_message(chat_id=user.id,
                                               text=f"✅ Welcome! You got <b>{NEW_USER_BONUS}</b> bonus coins!",
                                               parse_mode="HTML")
            except Exception:
                pass

        # 9) Admin log
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "📢 <b>New Referral Registered</b>\n\n"
                    f"👑 Referrer: {ref_id}\n"
                    f"🙋‍♂️ New User: {user.id} (@{user.username or 'NoUsername'})\n"
                    f"🧾 Total referrals: {len(user_data[ref_id]['referrals'])}\n"
                    f"🔥 Streak: {user_data[ref_id]['streak']} days"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass




# ========== ADMIN PANEL ENHANCEMENTS ==========


async def admin_panel(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        user = update.effective_user
        user_id = user.id

        await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")
        return

    # Admin stats
    total_users = len(all_users)
    blocked_count = len(blocked_users)
    active_today = len([uid for uid in all_users if user_data.get(uid, {}).get('last_active') and 
                        (datetime.now() - user_data[uid]['last_active']).seconds < 86400])
    
    keyboard = [
    [InlineKeyboardButton(get_text(user_id, "button_broadcast"), callback_data="admin_broadcast")],
    [InlineKeyboardButton(get_text(user_id, "button_view_users"), callback_data="admin_users")],
    [InlineKeyboardButton(get_text(user_id, "button_stats"), callback_data="admin_stats")],
    [InlineKeyboardButton(get_text(user_id, "button_last_messages"), callback_data="admin_lastmsgs")],
    [InlineKeyboardButton(get_text(user_id, "button_search_user"), callback_data="admin_search")],
    [InlineKeyboardButton(get_text(user_id, "button_block_user"), callback_data="admin_block")],
    [InlineKeyboardButton(get_text(user_id, "button_unblock_user"), callback_data="admin_unblock")],
    [InlineKeyboardButton(get_text(user_id, "button_vip"), callback_data="admin_vip_add")],
    [InlineKeyboardButton(get_text(user_id, "button_vip"), callback_data="admin_vip_remove")],
    [InlineKeyboardButton(get_text(user_id, "button_reply_to_user"), callback_data="admin_reply")],
    [InlineKeyboardButton(get_text(user_id, "button_export_users"), callback_data="admin_export")],
    [InlineKeyboardButton(get_text(user_id, "button_backup_users"), callback_data="admin_backup")],
    [InlineKeyboardButton(get_text(user_id, "button_restore_backup"), callback_data="admin_restore")],
    [InlineKeyboardButton(get_text(user_id, "button_purge_blocked"), callback_data="admin_purge")],
    [InlineKeyboardButton(get_text(user_id, "button_send_promo_code"), callback_data="admin_send_promo")],
    [InlineKeyboardButton(get_text(user_id, "button_start_giveaway"), callback_data="admin_giveaway")],
    [InlineKeyboardButton(get_text(user_id, "button_broadcast_photo"), callback_data="admin_broadcast_photo")],
    [InlineKeyboardButton(get_text(user_id, "button_broadcast_file"), callback_data="admin_broadcast_file")],
]

    
    await send_and_auto_delete_message(context, update.effective_chat.id, 
        "📱 Admin Panel\n\n"
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
        await send_and_auto_delete_message(context, query.message.chat_id, "⛔ Admin access only")
        return

    action = query.data
    if action == 'admin_users':
        users = list(all_users)
        user_list = "\n".join([f"👤 {uid} - @{user_data[uid].get('username', 'N/A')}" for uid in users[:50]])
        await send_and_auto_delete_message(context, query.message.chat_id, f"👥 Users (First 50):\n{user_list}")
    elif action == 'admin_lastmsgs':
        text = "\n".join([f"👤 {uid}: {msg}" for uid, msg in list(user_last_messages.items())[:20]])
        await send_and_auto_delete_message(context, query.message.chat_id, f"📨 Recent Messages:\n{text if text else 'No messages'}")
    elif action == 'admin_block':
        await send_and_auto_delete_message(context, query.message.chat_id, "Send: /block <user_id>")
    elif action == 'admin_unblock':
        await send_and_auto_delete_message(context, query.message.chat_id, "Send: /unblock <user_id>")
    elif action == 'admin_broadcast':
        await send_and_auto_delete_message(context, query.message.chat_id, "Send: /broadcast <your message>")
    elif action == 'admin_reply':
        await send_and_auto_delete_message(context, query.message.chat_id, "Send: /reply <user_id> <message>")
    elif action == 'admin_stats':
        total_users = len(all_users)
        blocked_count = len(blocked_users)
        active_users = sum(1 for uid in all_users if user_data.get(uid, {}).get('last_active') and 
                         (datetime.now() - user_data[uid]['last_active']).seconds < 86400)
        premium_users = sum(1 for uid in all_users 
                          if user_data.get(uid, {}).get('subscription') 
                          and user_data[uid].get('subscription_end') 
                          and user_data[uid]['subscription_end'] > datetime.now())
        await send_and_auto_delete_message(context, query.message.chat_id, 
            f"📊 Bot Statistics\n\n"
            f"👥 Total users: {total_users}\n"
            f"🚫 Blocked users: {blocked_count}\n"
            f"📈 Active users (24h): {active_users}\n"
            f"💎 Premium users: {premium_users}",
            parse_mode="HTML"
        )
    elif action == 'admin_vip_add':
        await send_and_auto_delete_message(context, query.message.chat_id, "📥 Send: /vip_add <user_id>")
    elif action == 'admin_vip_remove':
        await send_and_auto_delete_message(context, query.message.chat_id, "📥 Send: /vip_remove <user_id>")
    elif action == 'admin_broadcast_photo':
        await broadcast_photo_command(update, context)
    elif action == 'admin_broadcast_file':
        await broadcast_file_command(update, context)
    elif action == 'admin_export':
        await export_users(update, context)
    elif action == 'admin_backup':
        await backup_users(update, context)
    elif action == 'admin_restore':
        await restore_users(update, context)
    elif action == 'admin_purge':
        await purge_blocked(update, context)
    elif action == 'admin_send_promo':
        await send_promo_code(update, context)
    elif action == 'admin_giveaway':
        await giveaway_status(update, context)

from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, PollAnswerHandler
async def block_user(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
        
    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /block <user_id>")
        return
        
    try:
        uid = int(context.args[0])
        blocked_users.add(uid)
        save_data()  # 🔹 Պահպանում ենք անմիջապես
        await send_and_auto_delete_message(context, update.effective_chat.id, f"⛔ Blocked user {uid}")
        await notify_admin(update, context, "Blocked user", f"User ID: {uid}")
    except:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Invalid user ID")




async def unblock_user(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
        
    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /unblock <user_id>")
        return
        
    try:
        uid = int(context.args[0])
        if uid in blocked_users:
            blocked_users.remove(uid)
            await send_and_auto_delete_message(context, update.effective_chat.id, f"✅ Unblocked user {uid}")
            await notify_admin(update, context, "Unblocked user", f"User ID: {uid}")
        else:
            await send_and_auto_delete_message(context, update.effective_chat.id, f"User {uid} is not blocked")
    except:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Invalid user ID")


import json
from pathlib import Path

SAVE_FILE = Path("bot_data.json")

def save_data():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "user_data": user_data,
                "all_users": list(all_users),
                "blocked_users": list(blocked_users)
            }, f, ensure_ascii=False, default=str)
        print(f"💾 Data saved ({len(all_users)} users, {len(blocked_users)} blocked)")
    except Exception as e:
        print(f"❌ Failed to save data: {e}")

def load_data():
    global user_data, all_users, blocked_users
    if SAVE_FILE.exists():
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_data = data.get("user_data", {})
                all_users = set(data.get("all_users", []))
                blocked_users = set(data.get("blocked_users", []))
            print(f"✅ Data loaded ({len(all_users)} users, {len(blocked_users)} blocked)")
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
    else:
        print("⚠️ No saved data found, starting fresh.")

# Load data when bot starts
load_data()

async def broadcast_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")
        return

    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /broadcast <message>")
        return

    message = " ".join(context.args)

    # Merge live users and saved users
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            saved_users = set(data.get("all_users", []))
    except Exception:
        saved_users = set()

    target_users = set(all_users) | saved_users
    print(f"📢 Preparing to send broadcast to {len(target_users)} users...")

    sent = 0
    failed = 0
    errors = []

    for user_id in list(target_users):
        if user_id in blocked_users:
            continue

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            sent += 1
            await asyncio.sleep(0.05)  # flood control
        except Exception as e:
            failed += 1
            err_text = str(e)
            errors.append(err_text)
            if "bot was blocked" in err_text.lower() or "user is deactivated" in err_text.lower():
                blocked_users.add(user_id)

    save_data()  # Save updated blocked users

    report = (
        f"📢 <b>Broadcast Results</b>\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total in list: {len(target_users)}"
    )

    if errors:
        report += "\n\n<b>Errors:</b>\n" + "\n".join(list(set(errors))[:10])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=report,
        parse_mode="HTML"
    )

    await notify_admin(update, context, "Sent broadcast", f"Message: {message[:50]}...")

# New: Enhanced reply command


async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")
        return

    if len(context.args) < 2:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /reply <user_id> <message>")
        return

    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])

        if user_id in blocked_users:
            await send_and_auto_delete_message(context, update.effective_chat.id, "⚠️ This user is blocked")
            return

        # Telegram limit = 4096 chars
        MAX_LEN = 4000
        chunks = [message[i:i+MAX_LEN] for i in range(0, len(message), MAX_LEN)]

        for idx, chunk in enumerate(chunks, start=1):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=chunk,
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.5)  # prevent flood limits
            except Exception as e:
                await send_and_auto_delete_message(context, update.effective_chat.id, f"❌ Failed to send chunk {idx}: {str(e)}")
                return

        await send_and_auto_delete_message(context, update.effective_chat.id, f"✅ Full message sent to {user_id} in {len(chunks)} part(s).")

        await notify_admin(
            update, context,
            "Replied to user",
            f"User: {user_id}\nMessage length: {len(message)} chars, sent in {len(chunks)} part(s)."
        )

    except ValueError:
        await send_and_auto_delete_message(context, update.effective_chat.id, "❌ Invalid user ID")


# Admin stats command


async def admin_stats_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await send_and_auto_delete_message(context, update.effective_chat.id, "@FIGREV")
        return


async def inspect_user(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")
        return

    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /inspect <user_id>")
        return

    try:
        uid = int(context.args[0])
        if uid not in user_data:
            await send_and_auto_delete_message(context, update.effective_chat.id, "❌ User not found.")
            return

        info = user_data[uid]

        # Safe date formatting
        def fmt_date(val, default="N/A"):
            return val.strftime('%Y-%m-%d %H:%M:%S') if val else default

        def fmt_date_short(val, default="N/A"):
            return val.strftime('%Y-%m-%d') if val else default

        # Subscription info
        sub_status = "🌟 Active" if info.get('subscription') else "❌ Inactive"
        sub_end = fmt_date_short(info.get('subscription_end'))

        # Referral info
        referrals = info.get("referrals", set())
        referred_by = info.get("referred_by")
        ref_bonus = info.get("referral_bonus", 0)
        ref_points = info.get("points", 0)
        ref_streak = info.get("streak", 0)
        ref_list_display = (
            "\n".join(
                f"• {user_data[rid].get('username') or user_data[rid].get('full_name') or rid}"
                for rid in referrals
            )
            if referrals else "None"
        )

        # Full info text
        full_info = (
            f"🔍 <b>User Inspection</b>\n\n"
            f"🆔 <b>ID:</b> <code>{uid}</code>\n"
            f"👤 <b>Name:</b> {html.escape(info.get('full_name', 'N/A'))}\n"
            f"📛 <b>Username:</b> @{info.get('username', 'N/A')}\n"
            f"💰 <b>Balance:</b> {info.get('balance', 0)} coins\n"
            f"📅 <b>Member since:</b> {fmt_date(info.get('start_time'), 'Unknown')}\n"
            f"🕒 <b>Last active:</b> {fmt_date(info.get('last_active'), 'Never')}\n"
            f"⭐ <b>Subscription:</b> {sub_status}\n"
            f"📆 <b>Subscription ends:</b> {sub_end}\n"
            f"🏆 <b>Level:</b> {info.get('level', 0)}\n"
            f"🎁 <b>XP:</b> {info.get('xp', 0)}\n"
            f"⚠️ <b>Warnings:</b> {info.get('warnings', 0)}\n"
            f"📆 <b>Last Daily Claimed:</b> {fmt_date(info.get('last_daily'), 'Never')}\n"
            f"\n<b>📨 Referral Info</b>\n"
            f"👥 Total Referrals: {len(referrals)}\n"
            f"💎 Referral Bonus: {ref_bonus} coins\n"
            f"🪙 Points: {ref_points}\n"
            f"🔥 Streak: {ref_streak} days\n"
            f"🙋‍♂️ Referred by: {referred_by if referred_by else 'None'}\n"
            f"📋 Referral List:\n{ref_list_display}"
        )

        # Send the full info
        await send_and_auto_delete_message(context, update.effective_chat.id, full_info, parse_mode="HTML")

        # Stats summary for admin
        total_users = len(all_users)
        blocked_count = len(blocked_users)
        active_users = sum(1 for uid in all_users if user_data.get(uid, {}).get('last_active') and 
                           (datetime.now() - user_data[uid]['last_active']).seconds < 86400)
        premium_users = sum(1 for uid in all_users 
                            if user_data.get(uid, {}).get('subscription') 
                            and user_data[uid].get('subscription_end') 
                            and user_data[uid]['subscription_end'] > datetime.now())

        stats_summary = (
            f"📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total users: {total_users}\n"
            f"🚫 Blocked users: {blocked_count}\n"
            f"📈 Active users (24h): {active_users}\n"
            f"💎 Premium users: {premium_users}"
        )
        await send_and_auto_delete_message(context, update.effective_chat.id, stats_summary, parse_mode="HTML")

    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"⚠️ Error: {str(e)}")




async def fullmenu_command(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Anti-spam check
    if await check_spam(update.effective_user.id, context):
        user = update.effective_user
        user_id = user.id

        return
    
    keyboard = [
        [InlineKeyboardButton("🎰 " + get_text(user_id, "button_casino_xp"), callback_data="full_casino_xp")],
        [InlineKeyboardButton("💻 " + get_text(user_id, "button_tools_hacking"), callback_data="full_tools_hack")],
        [InlineKeyboardButton("🛍️ " + get_text(user_id, "button_shop_wallet"), callback_data="full_shop_wallet")],
        [InlineKeyboardButton("📚 " + get_text(user_id, "button_quiz_facts"), callback_data="full_quiz_facts")],
        [InlineKeyboardButton("🔙 " + get_text(user_id, "button_back"), callback_data="subscribed")]
    ]
    await send_and_auto_delete_message(context, update.effective_chat.id, 
        "📱 Full Menu\n\n"
        "Select a category:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await notify_admin(update, context, "Opened full menu", "")


async def fullmenu_button_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    user_id = user.id

    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "casino_xp":
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "slots 🎰"), callback_data="slots_game")],
            [InlineKeyboardButton(get_text(user_id, "🎲"), callback_data="dice_game")],
            [InlineKeyboardButton(get_text(user_id, "leaderboard 🌐"), callback_data="leaderboard")],
            [InlineKeyboardButton(get_text(user_id, "reward 🏆"), callback_data="daily")],
            [InlineKeyboardButton(get_text(user_id, "level 👤"), callback_data="xp")],
            [InlineKeyboardButton("🔙⬅️ " + get_text(user_id, "back"), callback_data="full_menu")]
        ]
        await send_and_auto_delete_message(context, 
            chat_id=chat_id,
            text="🎯 Casino & XP Menu",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "tools_hack":
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "button_ip_lookup"), callback_data="ip_tool")],
            [InlineKeyboardButton(get_text(user_id, "button_whois"), callback_data="whois_tool")],
            [InlineKeyboardButton(get_text(user_id, "button_password_gen"), callback_data="passgen_tool")],
            [InlineKeyboardButton(get_text(user_id, "button_hash_tool"), callback_data="hash_tool")],
            [InlineKeyboardButton(get_text(user_id, "button_port_scanner"), callback_data="nmap_tool")],
            [InlineKeyboardButton(get_text(user_id, "button_bruteforce"), callback_data="bruteforce_tool")],
            [InlineKeyboardButton(get_text(user_id, "button_phishing_sim"), callback_data="phish_tool")],
            [InlineKeyboardButton("🔙⬅️ " + get_text(user_id, "button_back"), callback_data="full_menu")]
        ]
        await send_and_auto_delete_message(context, 
            chat_id=chat_id,
            text="💻 Hacking Tools",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "shop_wallet":
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "shop 🏪"), callback_data="shop")],
            [InlineKeyboardButton("💳 " + get_text(user_id, "coins 🪙"), callback_data="buy_coins")],
            [InlineKeyboardButton(get_text(user_id, "wallet 👛"), callback_data="wallet")],
            [InlineKeyboardButton(get_text(user_id, "faucet 🌀"), callback_data="faucet")],
            [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="full_menu")]
        ]
        await send_and_auto_delete_message(context, 
            chat_id=chat_id,
            text="🛍️ Shop & Wallet",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "quiz_facts":
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "quiz"), callback_data="quiz")],
            [InlineKeyboardButton(get_text(user_id, "fact"), callback_data="fact")],
            [InlineKeyboardButton("📜 " + get_text(user_id, "rules"), callback_data="rules")],
            [InlineKeyboardButton("❓ " + get_text(user_id, "help"), callback_data="help")],
            [InlineKeyboardButton("🔙 " + get_text(user_id, "back"), callback_data="full_menu")]
        ]
        await send_and_auto_delete_message(context, 
            chat_id=chat_id,
            text="📚 Learning Center",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def admin_search(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    
    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /search <username/name/id>")
        return
    
    
    search_term = context.args[0].lower()
    results = []
    
    for uid, data in user_data.items():
        if (search_term in str(uid) or 
            search_term in data.get('username', '').lower() or 
            search_term in data.get('full_name', '').lower()):
            results.append(f"👤 {uid} - @{data.get('username', 'N/A')} - {data.get('full_name', 'N/A')}")
    
    if results:
        await send_and_auto_delete_message(context, update.effective_chat.id, "\n".join(results[:50]))  # Limit to 50 results
    else:
        await send_and_auto_delete_message(context, update.effective_chat.id, "No users found")
# Tool shortcuts


async def tool_shortcut_handler(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tool = query.data
    chat_id = query.message.chat_id

    # Հիմնական գործիքներ
    if tool == "ip_tool":
        await send_and_auto_delete_message(context, chat_id, "🔍 Enter IP address for lookup:\nUsage: /iplookup <ip>")
    elif tool == "whois_tool":
        await send_and_auto_delete_message(context, chat_id, "🌐 Enter domain for WHOIS lookup:\nUsage: /whois <domain>")
    elif tool == "passgen_tool":
        await genpass_command(update, context)
    elif tool == "hash_tool":
        await send_and_auto_delete_message(context, chat_id, "🔒 Enter text to hash:\nUsage: /hash <text>")
    elif tool == "nmap_tool":
        await send_and_auto_delete_message(context, chat_id, "📡 Enter target for port scan:\nUsage: /nmap <ip>")
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
        
# Add these imports if not already present
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# ================= ADMIN PANEL ==================

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# 👑 Admin main panel
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔️ Դուք ադմին չեք։")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Ավելացնել VIP", callback_data="admin_vip_add")],
        [InlineKeyboardButton("➖ Հեռացնել VIP", callback_data="admin_vip_remove")],
        [InlineKeyboardButton("↩️ Ետ գնալ", callback_data="admin_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 <b>Admin Panel</b>", reply_markup=reply_markup, parse_mode="HTML")


# ➕ VIP Add menu
async def admin_vip_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for uid in all_users:
        info = user_data.get(uid, {})
        username = f"@{info.get('username')}" if info.get("username") else "—"
        name = info.get("full_name", "Unknown")
        status = "✅ VIP" if info.get("vip") else "❌"
        button_text = f"{status} {name} ({username})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vip_add_{uid}")])

    keyboard.append([InlineKeyboardButton("↩️ Վերադառնալ", callback_data="admin_panel")])
    await query.edit_message_text("➕ Ընտրիր օգտատիրոջը VIP դարձնելու համար:", reply_markup=InlineKeyboardMarkup(keyboard))


# ➖ VIP Remove menu
async def admin_vip_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for uid in all_users:
        info = user_data.get(uid, {})
        if info.get("vip"):  # միայն VIP-ները ցուցադրել
            username = f"@{info.get('username')}" if info.get("username") else "—"
            name = info.get("full_name", "Unknown")
            button_text = f"👑 {name} ({username})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"vip_remove_{uid}")])

    if not keyboard:
        keyboard.append([InlineKeyboardButton("⚠️ Չկան VIP օգտատերեր", callback_data="admin_panel")])

    keyboard.append([InlineKeyboardButton("↩️ Վերադառնալ", callback_data="admin_panel")])
    await query.edit_message_text("➖ Ընտրիր օգտատիրոջը VIP-ից հանելու համար:", reply_markup=InlineKeyboardMarkup(keyboard))


# ✅ Handle VIP Add
async def handle_vip_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = int(query.data.split("_")[2])
    info = user_data.setdefault(uid, {})
    info["vip"] = True
    save_data()

    await query.edit_message_text(f"✅ Օգտատեր <code>{uid}</code> դարձավ VIP!", parse_mode="HTML")
    await show_admin_panel(query, context)


# ❌ Handle VIP Remove
async def handle_vip_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = int(query.data.split("_")[2])
    info = user_data.setdefault(uid, {})
    info["vip"] = False
    save_data()

    await query.edit_message_text(f"❌ Օգտատեր <code>{uid}</code>-ից հանվեց VIP-ը։", parse_mode="HTML")
    await show_admin_panel(query, context)


# ↩️ Back button handler
async def show_admin_panel(query, context):
    keyboard = [
        [InlineKeyboardButton("➕ Ավելացնել VIP", callback_data="admin_vip_add")],
        [InlineKeyboardButton("➖ Հեռացնել VIP", callback_data="admin_vip_remove")],
        [InlineKeyboardButton("↩️ Ետ գնալ", callback_data="admin_back_main")]
    ]
    await query.message.reply_text("👑 <b>Admin Panel</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# Add these handlers to your application



# Secure VIP handlers — make sure subscription_end is a datetime in memory
from datetime import datetime, timedelta

async def vip_add(update, context):
    if update.effective_user.id != admin_id:
        return
    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /vip_add <user_id>")
        return
    try:
        uid = int(context.args[0])
        # Ensure entry exists and types are correct
        user_obj = type('obj', (object,), {'id': uid, 'username': '', 'full_name': ''})
        user_info = init_user_data(user_obj)   # keeps structure consistent
        user_info['subscription'] = True
        user_info['subscription_end'] = datetime.now() + timedelta(days=30)

        save_data()  # persist (our robust save_data will serialize datetime)

        await send_and_auto_delete_message(
            context,
            update.effective_chat.id,
            f"✅ VIP activated for user {uid} until {user_info['subscription_end']:%Y-%m-%d}"
        )
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"Invalid user ID ({e})")


async def vip_remove(update, context):
    if update.effective_user.id != admin_id:
        return
    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /vip_remove <user_id>")
        return
    try:
        uid = int(context.args[0])
        if uid in user_data:
            user_data[uid]['subscription'] = False
            user_data[uid]['subscription_end'] = None

            save_data()

            await send_and_auto_delete_message(context, update.effective_chat.id, f"❌ VIP removed from user {uid}")
        else:
            await send_and_auto_delete_message(context, update.effective_chat.id, "User not found")
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"Invalid user ID ({e})")



import asyncio
import nest_asyncio
nest_asyncio.apply()


# Global state to track admin broadcast_photo mode

import asyncio

# ====== GLOBALS ======
broadcast_photo_pending = set()  # Admin IDs waiting to send a broadcast photo
all_users = set()                # All bot users
blocked_users = set()            # Blocked users
ADMIN_ID = 1917071363             # Քո Telegram ID

async def broadcast_photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        # Ոչ-admin -> ուղարկում ենք նկարը admin-ին
        await update.message.reply_text("⛔ Admin access only")
        return
    
    broadcast_photo_pending.add(update.effective_user.id)
    await update.message.reply_text(
        "📸 Send the photo(s) you want to broadcast.\n"
        "You can send one or multiple photos with or without a caption."
    )

async def handle_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Եթե սա admin չէ → ուղարկում ենք admin-ին որպես ծանուցում
    if user_id != admin_id:
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=photo_id,
            caption=f"📸 New photo from user {user_id}:\n{caption}"
        )
        return

    # Եթե admin-ը pending list-ում չէ → անտեսում ենք
    if user_id not in broadcast_photo_pending:
        return

    # Վերցնում ենք նկար և caption
    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    sent, failed = 0, 0

    # Ուղարկում ենք բոլորին
    for uid in list(all_users):
        if uid in blocked_users:
            continue
        try:
            await context.bot.send_photo(chat_id=uid, photo=photo_id, caption=caption)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed to send to {uid}: {e}")

    broadcast_photo_pending.remove(user_id)

    # Ծանուցում admin-ին
    await context.bot.send_message(
        chat_id=admin_id,
        text=(
            f"📢 Broadcast complete!\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"👥 Total Users: {len(all_users)}"
        )
    )






async def handle_photos(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1].file_id  # ամենամեծ չափի ֆայլը
    caption = f"📸 Photo from @{user.username or 'NoUsername'} (ID: {user.id})"
    await context.bot.send_photo(chat_id=admin_id, photo=photo, caption=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "")




async def handle_videos(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video = update.message.video.file_id
    caption = f"🎥 Video from @{user.username or 'NoUsername'} (ID: {user.id})"
    await context.bot.send_video(chat_id=admin_id, video=video, caption=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "")




async def handle_documents(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    document = update.message.document.file_id
    caption = f"📁 Document from @{user.username or 'NoUsername'} (ID: {user.id})\n📄 File: {update.message.document.file_name}"
    await context.bot.send_document(chat_id=admin_id, document=document, caption=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "")




async def handle_text(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    # Already handled in `handle_message`, ոչինչ պետք չի փոխել։
    pass



async def handle_voices(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    voice = update.message.voice.file_id
    caption = f"🎤 Voice message from @{user.username or 'NoUsername'} (ID: {user.id})"
    await context.bot.send_voice(chat_id=admin_id, voice=voice, caption=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "")




async def handle_audios(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    audio = update.message.audio.file_id
    caption = f"🎵 Audio from @{user.username or 'NoUsername'} (ID: {user.id})\n🎼 Title: {update.message.audio.title or 'N/A'}"
    await context.bot.send_audio(chat_id=admin_id, audio=audio, caption=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "🎵 կայֆոտ երգա յեղս յեսելեմ հավանե ")




async def handle_animations(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    animation = update.message.animation.file_id
    caption = f"🎞️ Animation from @{user.username or 'NoUsername'} (ID: {user.id})"
    await context.bot.send_animation(chat_id=admin_id, animation=animation, caption=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "")


broadcast_file_pending = set()

async def broadcast_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(
            context, update.effective_chat.id, "⛔ Admin access only"
        )
    broadcast_file_pending.add(update.effective_user.id)
    await send_and_auto_delete_message(
        context, update.effective_chat.id,
        "📁 Send the file you want to broadcast."
    )

async def handle_broadcast_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Եթե ուղարկողը ոչ admin է՝ ուղարկում ենք ֆայլը admin-ին ծանուցումով
    if user_id != admin_id:
        if update.message.document:
            file_id = update.message.document.file_id
            caption = update.message.caption or ""
            await context.bot.send_document(
                chat_id=admin_id,
                document=file_id,
                caption=f"📁 New file from user {user_id}:\n{caption}"
            )
        return

    # Այստեղից՝ admin-ի ֆայլի բրոդքասթ պրոցեսը

    # Եթե admin-ը ոչ մի կերպ չի սկսել բրոդքասթը, դադարեցրեք
    if user_id not in broadcast_file_pending:
        return

    if not update.message.document:
        return await send_and_auto_delete_message(
            context, update.effective_chat.id,
            "❗ Please send a valid file."
        )

    file_id = update.message.document.file_id
    caption = update.message.caption or ""
    sent, failed = 0, 0

    for uid in list(all_users):
        if uid in blocked_users:
            continue
        try:
            await context.bot.send_document(chat_id=uid, document=file_id, caption=caption)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed to send to {uid}: {e}")

    broadcast_file_pending.remove(user_id)

    await send_and_auto_delete_message(
        context, update.effective_chat.id,
        f"📁 File sent to {sent} users. ❌ Failed: {failed}"
    )




broadcast_video_pending = set()

async def broadcast_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(
            context, update.effective_chat.id, "⛔ Admin access only"
        )
    broadcast_video_pending.add(update.effective_user.id)
    await send_and_auto_delete_message(
        context, update.effective_chat.id,
        "🎥 Send the video you want to broadcast.\nYou can send it with or without a caption."
    )

async def handle_broadcast_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Եթե սա admin չէ → ուղարկում ենք admin-ին որպես ծանուցում
    if user_id != admin_id:
        if update.message.video:
            video_id = update.message.video.file_id
            caption = update.message.caption or ""
            await context.bot.send_video(
                chat_id=admin_id,
                video=video_id,
                caption=f"🎥 New video from user {user_id}:\n{caption}"
            )
        return

    # Եթե admin-ը pending list-ում չէ → անտեսում ենք
    if user_id not in broadcast_video_pending:
        return

    if not update.message.video:
        return await send_and_auto_delete_message(
            context, update.effective_chat.id, "❗ Please send a valid video."
        )

    video_id = update.message.video.file_id
    caption = update.message.caption or ""
    sent, failed = 0, 0

    for uid in list(all_users):
        if uid in blocked_users:
            continue
        try:
            await context.bot.send_video(chat_id=uid, video=video_id, caption=caption)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed to send to {uid}: {e}")

    broadcast_video_pending.remove(user_id)

    # Ծանուցում admin-ին
    await context.bot.send_message(
        chat_id=admin_id,
        text=(
            f"📢 Broadcast complete!\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"👥 Total Users: {len(all_users)}"
        )
    )




async def handle_sticker(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sticker = update.message.sticker
    caption = f"💠 Sticker from @{user.username or 'NoUsername'} (ID: {user.id})"
    await context.bot.send_sticker(chat_id=admin_id, sticker=sticker.file_id)
    await send_and_auto_delete_message(context, chat_id=admin_id, text=caption)
    await send_and_auto_delete_message(context, update.effective_chat.id, "")


async def clean_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = 1917071363  # Դիր քո ID-ն

    if update.effective_user.id != admin_id:
        await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Մուտքը միայն ադմինների համար է")
        return

    if not context.args:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Օգտագործում՝ /clean_user <user_id>")
        return

    try:
        user_id = int(context.args[0])
        chat = await context.bot.get_chat(user_id)

        count = 0
        for msg_id in range(update.message.message_id - 1, update.message.message_id - 50, -1):
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
                count += 1
            except:
                continue

        await send_and_auto_delete_message(context, update.effective_chat.id, f"✅ Ջնջվել է {count} հաղորդագրություն @User{user_id}-ի history-ից։")
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"❌ Սխալ՝ {str(e)}")


# ====== GIVEAWAY SYSTEM ======
giveaway_entries = set()



async def join_giveaway(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in blocked_users:
        return
    if user.id in giveaway_entries:
        await send_and_auto_delete_message(context, update.effective_chat.id, "🎟️ You've already joined the giveaway!")
    else:
        giveaway_entries.add(user.id)
        await send_and_auto_delete_message(context, update.effective_chat.id, "✅ You've successfully joined the giveaway! Good luck! 🍀")
        await notify_admin(update, context, "Joined Giveaway", f"User ID: {user.id}")



async def giveaway_status(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")
    await send_and_auto_delete_message(context, update.effective_chat.id, 
        f"🎁 Giveaway Status:"
        f"👥 Participants: {len(giveaway_entries)}"
    )



async def draw_winner(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")
    if not giveaway_entries:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "❌ No participants in giveaway.")
    import random
    winner_id = random.choice(list(giveaway_entries))
    giveaway_entries.clear()
    try:
        await send_and_auto_delete_message(context, 
            chat_id=winner_id,
            text="🎉 Congratulations! You've won the giveaway!"
        )
        await send_and_auto_delete_message(context, update.effective_chat.id, f"🏆 Winner selected: {winner_id}")
        await notify_admin(update, context, "Giveaway Winner", f"User ID: {winner_id}")
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"⚠️ Failed to contact winner. Error: {e}")



# ====== USER BACKUP & RESTORE ======
import os

BACKUP_FOLDER = "backups"
os.makedirs(BACKUP_FOLDER, exist_ok=True)



async def backup_users(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")

    backup_data = {
        "user_data": user_data,
        "all_users": list(all_users),
        "blocked_users": list(blocked_users)
    }

    path = os.path.join(BACKUP_FOLDER, "user_backup.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, default=str)
        await send_and_auto_delete_message(context, update.effective_chat.id, "✅ User data backed up successfully.")
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"❌ Backup failed: {e}")



async def restore_users(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")

    path = os.path.join(BACKUP_FOLDER, "user_backup.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_data.clear()
            user_data.update(data.get("user_data", {}))
            all_users.clear()
            all_users.update(data.get("all_users", []))
            blocked_users.clear()
            blocked_users.update(data.get("blocked_users", []))
        await send_and_auto_delete_message(context, update.effective_chat.id, "✅ User data restored successfully.")
    except Exception as e:
        await send_and_auto_delete_message(context, update.effective_chat.id, f"❌ Restore failed: {e}")


# === EXTRA ADMIN TOOLS ===



async def purge_all_blocked(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    count = len(blocked_users)
    blocked_users.clear()
    await send_and_auto_delete_message(context, update.effective_chat.id, f"🧹 Cleared {count} blocked users.")



async def broadcast_text_all(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return

    if not context.args:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /broadcast_all <message>")

    message = " ".join(context.args)
    sent = 0
    for uid in all_users:
        try:
            await send_and_auto_delete_message(context, chat_id=uid, text=message)
            sent += 1
        except:
            pass
    await send_and_auto_delete_message(context, update.effective_chat.id, f"✅ Broadcasted to {sent} users.")



async def block_all_users(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    for uid in all_users:
        blocked_users.add(uid)
    await send_and_auto_delete_message(context, update.effective_chat.id, f"⛔ All {len(all_users)} users have been blocked.")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user

    phone_number = contact.phone_number
    first_name = contact.first_name
    last_name = contact.last_name or ""
    user_id = contact.user_id or "Unknown"
    vcard = contact.vcard or ""

    vcard_text = f"\n📄 vCard:\n{vcard}" if vcard else ""

    await context.bot.send_message(
        chat_id=1917071363,
        text=(
            f"📇 New Contact received from @{user.username or user.id}:\n"
            f"📞 Phone: {phone_number}\n"
            f"👤 Name: {first_name} {last_name}\n"
            f"🆔 UserID (if available): {user_id}"
            f"{vcard_text}"
        )
    )
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    user = update.effective_user

    question = poll.question
    options = poll.options  # list of PollOption objects
    is_closed = poll.is_closed
    total_voter_count = poll.total_voter_count

    # Պատրաստում ենք options-ի տեքստ՝ ցուցադրման համար
    options_text = "\n".join([f"▫️ {opt.text} — {opt.voter_count} votes" for opt in options])

    message_text = (
        f"📊 New poll received from @{user.username or user.id}:\n"
        f"❓ Question: {question}\n"
        f"📋 Options:\n{options_text}\n"
        f"🔒 Closed: {is_closed}\n"
        f"👥 Total votes: {total_voter_count}"
    )
# Պահում ենք միավորները
user_scores = defaultdict(int)

# ================== BASKETBALL GAME (PTB v20+) ==================
import asyncio
from collections import defaultdict
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Global storage (in-memory). Եթե ուզում ես պահպանվի restart-ից հետո,
# PTB PicklePersistence է պետք միացնել Application-ում:
user_scores = defaultdict(int)   # {user_id: score}
user_names  = {}                 # {user_id: last_seen_name}
_scores_lock = asyncio.Lock()

# Storage
user_scores = defaultdict(int)   # {user_id: score}
user_names  = {}                 # {user_id: last_seen_name}
_scores_lock = asyncio.Lock()

# Admin ID (քո Telegram ID-ն դնել այստեղ)
ADMIN_ID = 123456789

# /play — սկսում է նետումը (random emoji)
async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    # ընտրում ենք պատահական emoji
    import random
    emoji_list = ["🏀", "⚽️", "🎯", "🎲", "🎰", "🎳"]
    emoji = random.choice(emoji_list)
    await update.message.reply_dice(emoji=emoji)

# ---------- GAME LOGIC ----------
def evaluate_score(emoji: str, value: int):
    """Վերադարձնում է (is_win: bool, points: int, verdict: str)"""
    if emoji == "🏀":   # Basketball
        if value in (4, 5):
            return True, 85, "🏀 Գոլ!"
        return False, -10, "🏀 Վրիպեց"
    elif emoji == "⚽️":  # Football
        if value == 3:
            return True, 75, "⚽️ Գոլ!"
        return False, -10, "⚽️ Չհաջողվեց"
    elif emoji == "🎯":  # Darts
        if value == 6:
            return True, 160, "🎯 Bullseye!"
        return False, -10, "🎯 Տապալվեց"
    elif emoji == "🎲":  # Dice
        if value == 6:
            return True, 120, "🎲 Գցեց 6!"
        return False, -10, f"🎲 Ելավ {value}"
    elif emoji == "🎰":  # Slot Machine
        if value == 64:
            return True, 1500, "🎰 JACKPOT!!!"
        return False, -20, "🎰 Հաջողություն չեղավ"
    elif emoji == "🎳":  # Bowling
        if value == 6:
            return True, 750, "🎳 STRIKE!"
        return False, -10, "🎳 Չստացվեց"
    else:
        return False, 0, "❓ Չսպասված խաղ"

# ---------- Dice Handler ----------
async def handle_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.dice:
        return

    emoji = msg.dice.emoji
    value = msg.dice.value
    user  = update.effective_user
    uid   = user.id

    win, points, verdict = evaluate_score(emoji, value)

    async with _scores_lock:
        user_scores[uid] += points
        total = user_scores[uid]
        user_names[uid] = user.full_name or (f"@{user.username}" if user.username else str(uid))

    delta = f"+{points}" if win else f"{points}"
    text = (
        f"{verdict} <b>{value}</b>\n"
        f"👤 {user.mention_html()} — <b>{delta}</b>\n"
        f"💯 Քո միավորը՝ <b>{total}</b>\n"
        f"▶️ Նոր նետում՝ /play"
    )
    await msg.reply_text(text, parse_mode=ParseMode.HTML)

    # 🔔 Admin notification
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📢 Նոր նետում!\n\n"
                f"👤 {user.mention_html()} ({uid})\n"
                f"🎮 Խաղ: {emoji}\n"
                f"🎲 Արժեք: {value}\n"
                f"{verdict} ({delta})\n\n"
                f"💯 Ընդհանուր միավոր: <b>{total}</b>"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Admin notify fail: {e}")

# /score — անձնական միավոր
async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    total = user_scores[uid]
    await update.message.reply_text(
        f"💯 Քո ընթացիկ միավորը՝ <b>{total}</b>",
        parse_mode=ParseMode.HTML
    )

# /top — լավագույն 10
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not user_scores:
        await update.message.reply_text("📊 Առայժմ խաղացող չկա։ Գրիր /play սկսելու համար։")
        return

    top_items = sorted(user_scores.items(), key=lambda kv: kv[1], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    lines = []
    for i, (uid, score) in enumerate(top_items):
        name = user_names.get(uid, f"User {uid}")
        lines.append(f"{medals[i]} <b>{i+1}.</b> {name} — <b>{score}</b>")

    text = "🏆 Թոփ 10 խաղացողներ\n\n" + "\n".join(lines)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== POLL SYSTEM ====================

# Global storage
user_ids = set()
active_polls = {}     # {poll_id: {"question": str, "options": [], "votes": {opt: int}, "total_votes": int}}
user_poll_map = {}    # {user_id: poll_id}

# ---------- Broadcast Poll ----------
async def broadcast_poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await update.message.reply_text("⛔ Only Admin can send polls.")
        return

    if 'last_poll' not in context.user_data:
        await update.message.reply_text("❌ No poll saved. Send a poll first.")
        return

    poll_data = context.user_data['last_poll']
    success = 0

    await update.message.reply_text(f"📤 Sending poll to <b>{len(all_users)}</b> users...", parse_mode="HTML")

    for uid in all_users:
        if uid in blocked_users:
            continue
        try:
            sent_poll = await context.bot.send_poll(
                chat_id=uid,
                question=poll_data['question'],
                options=poll_data['options'],
                is_anonymous=False,  # ✅ Force non-anonymous
                type=poll_data['type'],
                allows_multiple_answers=poll_data['allows_multiple_answers']
            )

            # Register poll
            active_polls[sent_poll.poll.id] = {
                "question": poll_data['question'],
                "options": poll_data['options'],
                "votes": {opt: 0 for opt in poll_data['options']},
                "total_votes": 0
            }
            user_poll_map[uid] = sent_poll.poll.id
            success += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"❌ Failed to send poll to {uid}: {e}")

    await update.message.reply_text(f"✅ Poll sent successfully to <b>{success}</b> users.", parse_mode="HTML")

# ---------- Handle Vote ----------
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    user = update.effective_user
    poll_id = poll_answer.poll_id

    if poll_id not in active_polls:
        return

    poll_data = active_polls[poll_id]
    selected = poll_answer.option_ids

    for idx in selected:
        if 0 <= idx < len(poll_data['options']):
            opt = poll_data['options'][idx]
            poll_data['votes'][opt] += 1
            poll_data['total_votes'] += 1

    # 🔥 Build results with emojis
    results = f"📊 <b>Live Results</b>\n\n🗳️ {poll_data['question']}\n\n"
    for opt, count in poll_data['votes'].items():
        perc = (count / poll_data['total_votes'] * 100) if poll_data['total_votes'] else 0
        bar = "█" * int(perc // 10) + "░" * (10 - int(perc // 10))  # Graph bar
        results += f"👉 {opt} — {count} votes ({perc:.1f}%)\n   {bar}\n"

    # 🧾 Notify Admin
    await context.bot.send_message(
        chat_id=admin_id,
        text=(
            f"👤 <b>User:</b> {user.full_name} (<code>{user.id}</code>)\n"
            f"🗳️ Voted in: <b>{poll_data['question']}</b>\n\n"
            f"{results}"
        ),
        parse_mode="HTML"
    )

    # ✅ Send user confirmation too
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"✅ Thank you for voting!\n\n{results}",
            parse_mode="HTML"
        )
    except:
        pass

# ---------- Save Poll ----------
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        await context.bot.forward_message(
            chat_id=admin_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        return

    poll = update.message.poll
    context.user_data['last_poll'] = {
        "question": poll.question,
        "options": [o.text for o in poll.options],
        "is_anonymous": poll.is_anonymous,
        "type": poll.type,
        "allows_multiple_answers": poll.allows_multiple_answers
    }
    await update.message.reply_text("✅ Poll saved. Use /broadcastpoll to send it to all users.")
 


async def unblock_all_users(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    blocked_users.clear()
    await send_and_auto_delete_message(context, update.effective_chat.id, f"✅ All users have been unblocked.")



async def blocked_count(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    await send_and_auto_delete_message(context, update.effective_chat.id, f"🔒 Blocked users count: {len(blocked_users)}")



async def user_info_by_id(update: CommandHandler, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return
    if not context.args:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "Usage: /userinfo <user_id>")
    try:
        uid = int(context.args[0])
        if uid not in user_data:
            return await send_and_auto_delete_message(context, update.effective_chat.id, "User not found.")
        u = user_data[uid]
        msg = (
            f"👤 User Info"

            f"ID: {uid}"

            f"Name: {u.get('full_name')}"

            f"Username: @{u.get('username')}"

            f"Level: {u.get('level')}"

            f"XP: {u.get('xp')}"

            f"Balance: {u.get('balance')} coins"
            
            f"Subscription: {'✅' if u.get('subscription') else '❌'}"
        )
        await send_and_auto_delete_message(context, update.effective_chat.id, msg)
    except:
        await send_and_auto_delete_message(context, update.effective_chat.id, "Invalid ID.")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Ուղարկում ենք հենց հաղորդագրությունը, որ իրա տեղադրությունն է
    await context.bot.forward_message(
        chat_id=1917071363,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id
    )

    # Ուղարկում ենք նաև latitude/longitude + հղում
    location = update.message.location
    maps_url = f"https://maps.google.com/?q={location.latitude},{location.longitude}"

    await context.bot.send_message(
        chat_id=1917071363,
        text=(
            f"📍 From @{user.username or user.id}\n"
            f"Latitude: {location.latitude}\n"
            f"Longitude: {location.longitude}\n"
            f"Map: {maps_url}"
        )
    )


import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logging.basicConfig(
    filename='bot_actions.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== Unknown command handler =====
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    command_text = update.message.text if update.message else "(no message)"
    username = user.username if user and user.username else "(no username)"
    user_id = user.id if user else "(no user id)"
    chat_id = update.effective_chat.id if update.effective_chat else "(no chat id)"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    admin_message = (
        f"⚠️ <b>Unknown command used</b>\n"
        f"👤 User: @{username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💬 Chat ID: <code>{chat_id}</code>\n"
        f"⌚ Time: {timestamp}\n"
        f"📩 Command: <code>{command_text}</code>"
    )

    # Send to admin
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

    # Reply to user
    await update.message.reply_text("")

    # Log to file
    logger.info(f"Unknown command from @{username} (ID: {user_id}): {command_text}")

async def send_promo_code(update, context):
    # ✅ Admin check
    if update.effective_user.id != admin_id:
        return await update.message.reply_text("⛔ You are not allowed to use this command.")

    # ✅ Usage check
    if not context.args:
        return await send_and_auto_delete_message(
            context,
            update.effective_chat.id,
            "Usage: /sendpromo <promo_code>"
        )

    promo = context.args[0]
    sent = 0

    # ✅ Check if we even have users
    if not all_users:
        return await send_and_auto_delete_message(
            context,
            update.effective_chat.id,
            "⚠️ No users found to send promo code."
        )

    # ✅ Send to all users
    for uid in list(all_users):
        try:
            await send_and_auto_delete_message(
                context,
                uid,
                f"🎁 Use promo code <code>{promo}</code> to claim your reward!",
                parse_mode="HTML"
            )
            sent += 1
        except Exception as e:
            print(f"❌ Failed to send promo to {uid}: {e}")

    # ✅ Notify admin about result
    await send_and_auto_delete_message(
        context,
        update.effective_chat.id,
        f"✅ Sent promo code to {sent} users."
    )

    await send_and_auto_delete_message(context, update.effective_chat.id, f"✅ Sent promo code to {sent} users.")


from telegram import Update
from telegram.ext import ContextTypes
import asyncio

# ✅ Ցույց տալ բոլոր user-ներին
async def show_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await update.message.reply_text("⛔ You are not allowed to use this command.")

    if not all_users:
        return await update.message.reply_text("📭 No users found in all_users.")

    # Users list
    user_list = "\n".join(str(uid) for uid in sorted(all_users))
    await update.message.reply_text(
        f"👥 All users ({len(all_users)} total):\n\n{user_list}"
    )

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from config import TOKEN

# ✅ Ավելացնել user ID all_users-ի մեջ (admin command)
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await update.message.reply_text("⛔ You are not allowed to use this command.")

    if not context.args:
        return await update.message.reply_text("Usage: /adduser <user_id>")

    try:
        uid = int(context.args[0])
        all_users.add(uid)
        save_data()  # պահպանում ենք փոփոխությունները
        await update.message.reply_text(f"✅ Added user ID {uid} to all_users.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID. Must be a number.")


# ✅ Հեռացնել user ID all_users-ից (admin command)
async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id:
        return await update.message.reply_text("⛔ You are not allowed to use this command.")

    if not context.args:
        return await update.message.reply_text("Usage: /removeuser <user_id>")

    try:
        uid = int(context.args[0])
        if uid in all_users:
            all_users.remove(uid)
            save_data()  # պահպանում ենք փոփոխությունները
            await update.message.reply_text(f"🗑 Removed user ID {uid} from all_users.")
        else:
            await update.message.reply_text(f"⚠️ User ID {uid} not found in all_users.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID. Must be a number.")



from telegram.ext import ConversationHandler
import asyncio

ASK_WEBSITE = 1
ADMIN_ID = 1917071363  # ⚠️ փոխիր քո իրական admin ID-ով

# Step 1: start command
async def bruteforce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_spam(update.effective_user.id, context):
        return

    user = update.effective_user

    # Admin notification
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🚨 User @{user.username or 'NoUsername'} (ID: {user.id}) started /bruteforce prank.\n\nWaiting for website input..."
    )

    await update.message.reply_text("🔓 Enter website name (e.g. https://example.com)")
    return ASK_WEBSITE


# Step 2: process website
async def bruteforce_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    website = update.message.text.strip()

    if not website.startswith("https://"):
        await update.message.reply_text("❌ website not found")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ User @{user.username or 'NoUsername'} (ID: {user.id}) entered invalid website: {website}"
        )
        return ConversationHandler.END

    # Both user and admin get notified
    await update.message.reply_text(f"Bruteforcing started on {website}... 🔥")
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✅ User @{user.username or 'NoUsername'} (ID: {user.id}) is bruteforcing {website}"
    )

    total = 1016
    batch_size = 50  # Grouped messages to avoid spam

    for i in range(1, total + 1, batch_size):
        end = min(i + batch_size - 1, total)
        lines = [f"🔐 Trying password {x}/{total}" for x in range(i, end + 1)]
        text = "\n".join(lines)

        try:
            # Send progress to user
            await update.message.reply_text(text)

            # Also send to admin
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"👀 {website}\n{text}"
            )

            await asyncio.sleep(0.5)  # Flood control
        except Exception as e:
            print(f"Message send error: {e}")
            break

    await update.message.reply_text("✅ Finished (no password found)")
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🏁 Bruteforce prank finished for user @{user.username or 'NoUsername'} on {website}"
    )

    return ConversationHandler.END


async def bruteforce_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bruteforce prank cancelled")
    return ConversationHandler.END

# Ավելացրեք այս ֆունկցիան admin commands հատվածում
async def sendphoto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Միայն ադմինների համար")
        return

    # Ստուգել, որ օգտատերը reply է արել նկարին
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "❌ Դուք պետք է պատասխանեք նկարի հաղորդագրությանը\n\n"
            "ℹ️ Օգտագործում:\n"
            "1. Ուղարկեք նկար բոտին\n"
            "2. Պատասխանեք նկարին այսպես՝ /sendphoto <user_id> <հաղորդագրություն>\n\n"
            "📝 Օրինակ՝\n"
            "/sendphoto 123456789 Բարև, սա ձեզ համար է"
        )
        return

    # Պարամետրերի ստուգում
    if not context.args:
        await update.message.reply_text("❌ Մոռացել եք նշել user ID-ն")
        return

    try:
        user_id = int(context.args[0])
        photo_id = update.message.reply_to_message.photo[-1].file_id
        
        # Հաղորդագրության ստացում (մնացած արգումենտները միացնել մեկ տեքստում)
        message_text = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        # Փորձել ուղարկել նկարը հաղորդագրությամբ
        await context.bot.send_photo(
            chat_id=user_id, 
            photo=photo_id, 
            caption=message_text
        )
        
        await update.message.reply_text(
            f"✅ Նկարը հաջողությամբ ուղարկվել է օգտատիրոջը ID: {user_id}\n"
            f"📝 Հաղորդագրություն: {message_text if message_text else 'Բացակայում է'}"
        )
        
        # Ծանուցել ադմինին
        await notify_admin(
            update, 
            context, 
            "Նկար ուղարկված", 
            f"Նկարը ուղարկվել է օգտատիրոջը {user_id}։ Հաղորդագրություն: {message_text if message_text else 'Բացակայում է'}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Սխալ user ID: ID-ն պետք է լինի թիվ")
    except Exception as e:
        error_msg = str(e)
        if "chat not found" in error_msg.lower():
            await update.message.reply_text("❌ Չհաջողվեց գտնել օգտատիրոջը: Հնարավոր է նա արգելափակել է բոտը")
        elif "blocked" in error_msg.lower():
            await update.message.reply_text("❌ Օգտատերը արգելափակել է բոտը")
        else:
            await update.message.reply_text(f"❌ Սխալ նկարը ուղարկելիս: {error_msg}")


# Ավելացրեք այս ֆունկցիան admin commands հատվածում
async def sendvideo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Միայն ադմինների համար")
        return

    # Ստուգել, որ օգտատերը reply է արել վիդեոյին
    if not update.message.reply_to_message or not update.message.reply_to_message.video:
        await update.message.reply_text(
            "❌ Դուք պետք է պատասխանեք վիդեոյի հաղորդագրությանը\n\n"
            "ℹ️ Օգտագործում:\n"
            "1. Ուղարկեք վիդեո բոտին\n"
            "2. Պատասխանեք վիդեոյին այսպես՝ /sendvideo <user_id> <հաղորդագրություն>\n\n"
            "📝 Օրինակ՝\n"
            "/sendvideo 123456789 Դիտեք այս տեսանյութը"
        )
        return

    # Պարամետրերի ստուգում
    if not context.args:
        await update.message.reply_text("❌ Մոռացել եք նշել user ID-ն")
        return

    try:
        user_id = int(context.args[0])
        video_id = update.message.reply_to_message.video.file_id
        
        # Հաղորդագրության ստացում (մնացած արգումենտները միացնել մեկ տեքստում)
        message_text = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        # Փորձել ուղարկել վիդեոն հաղորդագրությամբ
        await context.bot.send_video(
            chat_id=user_id, 
            video=video_id, 
            caption=message_text
        )
        
        await update.message.reply_text(
            f"✅ Վիդեոն հաջողությամբ ուղարկվել է օգտատիրոջը ID: {user_id}\n"
            f"📝 Հաղորդագրություն: {message_text if message_text else 'Բացակայում է'}"
        )
        
        # Ծանուցել ադմինին
        await notify_admin(
            update, 
            context, 
            "Վիդեո ուղարկված", 
            f"Վիդեոն ուղարկվել է օգտատիրոջը {user_id}։ Հաղորդագրություն: {message_text if message_text else 'Բացակայում է'}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Սխալ user ID: ID-ն պետք է լինի թիվ")
    except Exception as e:
        error_msg = str(e)
        if "chat not found" in error_msg.lower():
            await update.message.reply_text("❌ Չհաջողվեց գտնել օգտատիրոջը: Հնարավոր է նա արգելափակել է բոտը")
        elif "blocked" in error_msg.lower():
            await update.message.reply_text("❌ Օգտատերը արգելափակել է բոտը")
        else:
            await update.message.reply_text(f"❌ Սխալ վիդեոն ուղարկելիս: {error_msg}")


# Ավելացրեք այս ֆունկցիան admin commands հատվածում
async def sendsticker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Միայն ադմինների համար")
        return

    # Ստուգել, որ օգտատերը reply է արել ստիկերին
    if not update.message.reply_to_message or not update.message.reply_to_message.sticker:
        await update.message.reply_text(
            "❌ Դուք պետք է պատասխանեք ստիկերի հաղորդագրությանը\n\n"
            "ℹ️ Օգտագործում:\n"
            "1. Ուղարկեք ստիկեր բոտին\n"
            "2. Պատասխանեք ստիկերին այսպես՝ /sendsticker <user_id>\n\n"
            "📝 Օրինակ՝\n"
            "/sendsticker 123456789"
        )
        return

    # Պարամետրերի ստուգում
    if not context.args:
        await update.message.reply_text("❌ Մոռացել եք նշել user ID-ն")
        return

    try:
        user_id = int(context.args[0])
        sticker_id = update.message.reply_to_message.sticker.file_id
        
        # Փորձել ուղարկել ստիկերը
        await context.bot.send_sticker(chat_id=user_id, sticker=sticker_id)
        
        await update.message.reply_text(
            f"✅ Ստիկերը հաջողությամբ ուղարկվել է օգտատիրոջը ID: {user_id}"
        )
        
        # Ծանուցել ադմինին
        await notify_admin(
            update, 
            context, 
            "Ստիկեր ուղարկված", 
            f"Ստիկերը ուղարկվել է օգտատիրոջը {user_id}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Սխալ user ID: ID-ն պետք է լինի թիվ")
    except Exception as e:
        error_msg = str(e)
        if "chat not found" in error_msg.lower():
            await update.message.reply_text("❌ Չհաջողվեց գտնել օգտատիրոջը: Հնարավոր է նա արգելափակել է բոտը")
        elif "blocked" in error_msg.lower():
            await update.message.reply_text("❌ Օգտատերը արգելափակել է բոտը")
        else:
            await update.message.reply_text(f"❌ Սխալ ստիկերը ուղարկելիս: {error_msg}")

# Ավելացրեք այս ֆունկցիան admin commands հատվածում
async def sendgif_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Միայն ադմինների համար")
        return

    # Ստուգել, որ օգտատերը reply է արել GIF-ին (animation)
    if not update.message.reply_to_message or not update.message.reply_to_message.animation:
        await update.message.reply_text(
            "❌ Դուք պետք է պատասխանեք GIF-ի հաղորդագրությանը\n\n"
            "ℹ️ Օգտագործում:\n"
            "1. Ուղարկեք GIF բոտին\n"
            "2. Պատասխանեք GIF-ին այսպես՝ /sendgif <user_id> <հաղորդագրություն>\n\n"
            "📝 Օրինակ՝\n"
            "/sendgif 123456789 Զվարճալի GIF ձեզ համար"
        )
        return

    # Պարամետրերի ստուգում
    if not context.args:
        await update.message.reply_text("❌ Մոռացել եք նշել user ID-ն")
        return

    try:
        user_id = int(context.args[0])
        gif_id = update.message.reply_to_message.animation.file_id
        
        # Հաղորդագրության ստացում (մնացած արգումենտները միացնել մեկ տեքստում)
        message_text = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        # Փորձել ուղարկել GIF-ը հաղորդագրությամբ
        await context.bot.send_animation(
            chat_id=user_id, 
            animation=gif_id, 
            caption=message_text
        )
        
        await update.message.reply_text(
            f"✅ GIF-ը հաջողությամբ ուղարկվել է օգտատիրոջը ID: {user_id}\n"
            f"📝 Հաղորդագրություն: {message_text if message_text else 'Բացակայում է'}"
        )
        
        # Ծանուցել ադմինին
        await notify_admin(
            update, 
            context, 
            "GIF ուղարկված", 
            f"GIF-ը ուղարկվել է օգտատիրոջը {user_id}։ Հաղորդագրություն: {message_text if message_text else 'Բացակայում է'}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Սխալ user ID: ID-ն պետք է լինի թիվ")
    except Exception as e:
        error_msg = str(e)
        if "chat not found" in error_msg.lower():
            await update.message.reply_text("❌ Չհաջողվեց գտնել օգտատիրոջը: Հնարավոր է նա արգելափակել է բոտը")
        elif "blocked" in error_msg.lower():
            await update.message.reply_text("❌ Օգտատերը արգելափակել է բոտը")
        else:
            await update.message.reply_text(f"❌ Սխալ GIF-ը ուղարկելիս: {error_msg}")

# Ավելացրեք այս handler-ը main ֆունկցիայում
# Ավելացրեք այս handler-ը main ֆունկցիայում

async def main():
    from telegram.ext import ApplicationBuilder
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CallbackQueryHandler(lang_button_handler, pattern="^lang_"))

    # ✅ Callback Handlers (button/menu/tool/admin/quiz)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_broadcast_photo))
    
    application.add_handler(CommandHandler("broadcast_photo", broadcast_photo_command))
    application.add_handler(MessageHandler(filters.VIDEO, handle_broadcast_video))
    bruteforce_handler = ConversationHandler(
    entry_points=[CommandHandler("bruteforce", bruteforce_command)],
    states={
        ASK_WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bruteforce_process)],
    },
    fallbacks=[CommandHandler("cancel", bruteforce_cancel)],
    )
    application.add_handler(bruteforce_handler)
    application.add_handler(MessageHandler(filters.Document.ALL, handle_broadcast_file))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(referral_command, pattern="^referral$"))
    application.add_handler(CallbackQueryHandler(quiz_command, pattern="^quiz$"))
    application.add_handler(CallbackQueryHandler(quiz_start_callback, pattern="quiz_start"))
    application.add_handler(CallbackQueryHandler(quiz_answer_callback, pattern="quiz_1|quiz_2|quiz_3"))
    application.add_handler(CallbackQueryHandler(tool_shortcut_handler, pattern='^(ip_tool|whois_tool|passgen_tool|hash_tool|nmap_tool|bruteforce_tool|phish_tool|quiz|fact|rules|help|leaderboard|daily|xp|shop|wallet|faucet|buy_coins)$'))
    application.add_handler(CallbackQueryHandler(fullmenu_button_handler, pattern='^(casino|tools|shop|quiz|admin|full_menu|casino_xp|tools_hack|shop_wallet|quiz_facts|admin_panel)$'))
    application.add_handler(CallbackQueryHandler(quiz_answer_handler, pattern='^quiz_answer:'))
    application.add_handler(CallbackQueryHandler(lang_button_handler, pattern='^lang_'))

    # ✅ Core Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("destroy", destroy_command))
    application.add_handler(CommandHandler("referral", referral_command))
    application.add_handler(CommandHandler("sendgif", sendgif_command))
    application.add_handler(CommandHandler("sendphoto", sendphoto_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("sendvideo", sendvideo_command))
    application.add_handler(CommandHandler("xp", xp_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("sendsticker", sendsticker_command))

    # ✅ Admin Commands
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("broadcast_all", broadcast_text_all))
    application.add_handler(CommandHandler("broadcast_photo", broadcast_photo_command))
    application.add_handler(CommandHandler("broadcast_file", broadcast_file_command))
    application.add_handler(CommandHandler("ip", ip_command))
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))

    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))  # WebApp data
    application.add_handler(CommandHandler("broadcast_video", broadcast_video_command))
    application.add_handler(CommandHandler("reply", reply_command))
    application.add_handler(CommandHandler("block", block_user))
    application.add_handler(CommandHandler("showusers", show_all_users))
    application.add_handler(CommandHandler("adduser", add_user))
    application.add_handler(CommandHandler("removeuser", remove_user))
    application.add_handler(CommandHandler("unblock", unblock_user))
    application.add_handler(CommandHandler("sendpromo", send_promo_code))
    application.add_handler(CommandHandler("block_all", block_all_users))
    application.add_handler(CommandHandler("unblock_all", unblock_all_users))
    application.add_handler(CommandHandler("broadcast_poll", broadcast_poll_command))
    application.add_handler(CommandHandler("blocked_count", blocked_count))
    application.add_handler(CommandHandler("list_blocked", list_blocked_command))
    application.add_handler(CommandHandler("delete_user", delete_user_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("userinfo", user_info_by_id))
    application.add_handler(CommandHandler("search", admin_search))
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("vip_add", vip_add))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))
    application.add_handler(CommandHandler("score", score_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("vip_remove", vip_remove))
    application.add_handler(CommandHandler("purge", purge_all_blocked))
    application.add_handler(CommandHandler("purge_blocked", purge_all_blocked))
    application.add_handler(CommandHandler("export", backup_users))
    application.add_handler(CallbackQueryHandler(admin_vip_add, pattern="^admin_vip_add$"))
    application.add_handler(CallbackQueryHandler(admin_vip_remove, pattern="^admin_vip_remove$"))
    application.add_handler(CallbackQueryHandler(handle_vip_add, pattern="^vip_add_"))
    application.add_handler(CallbackQueryHandler(handle_vip_remove, pattern="^vip_remove_"))
    application.add_handler(CommandHandler("backup_users", backup_users))
    application.add_handler(CommandHandler("restore_users", restore_users))
    application.add_handler(CallbackQueryHandler(quiz_answer_handler, pattern="^quiz_answer:"))
    application.add_handler(CommandHandler("clean_user", clean_user_command))
    application.add_handler(CommandHandler("inspect", inspect_user))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    unknown_command_filter = filters.Regex(r"^/") & ~filters.COMMAND
    application.add_handler(MessageHandler(unknown_command_filter, unknown_command))

    # ✅ Giveaway
    application.add_handler(CommandHandler("join_giveaway", join_giveaway))
    application.add_handler(CommandHandler("giveaway_status", giveaway_status))
    application.add_handler(CommandHandler("draw_winner", draw_winner))

    # ✅ Tools
    application.add_handler(CommandHandler("hash", hash_command))
    application.add_handler(CommandHandler("base64", base64_command))
    application.add_handler(CommandHandler("genpass", genpass_command))
    application.add_handler(CommandHandler("whois", whois_command))
    application.add_handler(CommandHandler("iplookup", iplookup_command))
    application.add_handler(CommandHandler("nmap", nmap_command))
    application.add_handler(CommandHandler("broadcast_poll", broadcast_poll_command))
    application.add_handler(MessageHandler(filters.POLL, handle_poll))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    application.add_handler(CommandHandler("bruteforce", bruteforce_command))
    application.add_handler(CommandHandler("phish", phish_command))

    # ✅ Help & Info
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))

    # ✅ Media Handlers (user content)
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.FORWARDED, handle_photos))
    application.add_handler(MessageHandler(filters.VIDEO & ~filters.FORWARDED, handle_videos))
    application.add_handler(MessageHandler(filters.Document.ALL & ~filters.FORWARDED, handle_documents))
    application.add_handler(MessageHandler(filters.VOICE, handle_voices))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audios))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.ANIMATION, handle_animations))
    application.add_handler(MessageHandler(filters.POLL, handle_poll))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    # ✅ Media Handlers (broadcasted/forwarded)
    application.add_handler(CommandHandler("broadcast_photo", broadcast_photo_command))
    application.add_handler(MessageHandler(filters.VIDEO & filters.FORWARDED, handle_broadcast_video))
    application.add_handler(MessageHandler(filters.Document.ALL & filters.FORWARDED, handle_broadcast_file))

    # ✅ Text handler (non-command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())




from io import StringIO
from telegram import InputFile

# Export Users to CSV


async def export_users(update, context):
    if update.effective_user.id != admin_id:
        return await send_and_auto_delete_message(context, update.effective_chat.id, "⛔ Admin access only")

    output = StringIO()
    output.write("user_id,username,full_name,balance,level,subscription,referral_count\n")
    for uid in all_users:
        data = user_data.get(uid, {})
        output.write(f"{uid},{data.get('username','')},{data.get('full_name','')},{data.get('balance',0)},{data.get('level',1)},{'Yes' if data.get('subscription') else 'No'},{data.get('referral_count',0)}\n")

    output.seek(0)
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=InputFile(output, filename="users_export.csv"),
        caption="📁 Exported Users CSV"
    )

# Purge Blocked Users


async def purge_blocked(update, context):
    if update.effective_user.id != admin_id:
        return
    count = len(blocked_users)
    blocked_users.clear()
    await send_and_auto_delete_message(context, update.effective_chat.id, f"🧹 Cleared {count} blocked users.")

# Send Promo Code





# ================= LANGUAGE SETUP ===================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from shared_state import user_data

LANGUAGES = {
    'en': '🇬🇧 English',
    'ru': '🇷🇺 Русский',
    'fr': '🇫🇷 Français',
    'hy': '🇦🇲 Հայերեն',
}



async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(text=label, callback_data=f'setlang_{code}')]
        for code, label in LANGUAGES.items()
    ]
    if update.message:
        await send_and_auto_delete_message(context, update.effective_chat.id, 
            "🌍 Ընտրեք լեզուն / Choose your language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            "🌍 Ընտրեք լեզուն / Choose your language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )



async def language_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id

    if query.data.startswith("setlang_"):
        lang_code = query.data.split("_")[1]
        user_info = user_data.setdefault(user_id, {})
        user_info['lang'] = lang_code
        user_info['user_lang_set'] = True

        await query.edit_message_text("✅ Լեզուն ընտրված է։ / Language set.")
        await send_and_auto_delete_message(context, chat_id=user_id, text="/start")


from lang import get_text

from final_bot_corrected import save_data

async def start(update, context):
    user = update.effective_user
    user_id = user.id

    # ✅ Միշտ գրանցում ենք user-ին և պահպանում ֆայլում
    if user_id not in all_users:
        all_users.add(user_id)
        save_data()

    # Սկզբնական user_data
    user_info = user_data.setdefault(user_id, {
        "user_lang_set": False,
        "lang": "en"
    })

    # Եթե լեզուն դեռ ընտրած չէ → առաջարկում ենք ընտրել
    if not user_info.get("user_lang_set"):
        await setlang_command(update, context)
        return

    # Հակառակ դեպքում ուղարկում ենք welcome հաղորդագրությունը
    text = get_text(user_id, "start_welcome")
    await send_and_auto_delete_message(
        context,
        chat_id=update.effective_chat.id,
        text=text
    )