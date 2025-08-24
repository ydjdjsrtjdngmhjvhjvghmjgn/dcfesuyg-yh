
import sqlite3
from datetime import datetime

conn = sqlite3.connect("botdata.db", check_same_thread=False)
cur = conn.cursor()

def init_db():
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
    blocked INTEGER DEFAULT 0,
        lang TEXT DEFAULT 'en',
        last_daily TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS wallets (
        user_id INTEGER PRIMARY KEY,
        btc REAL DEFAULT 0.001,
        eth REAL DEFAULT 0.02,
        usdt REAL DEFAULT 15
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER,
        referred_id INTEGER,
        UNIQUE(referrer_id, referred_id)
    )
    ''')
    conn.commit()

def add_user(user_id, username):
    cur.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()

def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    return cur.fetchone()

def update_xp(user_id, amount):
    cur.execute("UPDATE users SET xp = xp + ? WHERE id=?", (amount, user_id))
    cur.execute("SELECT xp FROM users WHERE id=?", (user_id,))
    xp = cur.fetchone()[0]
    level = xp // 100 + 1
    cur.execute("UPDATE users SET level = ? WHERE id=?", (level, user_id))
    conn.commit()

def get_wallet(user_id):
    cur.execute("SELECT * FROM wallets WHERE user_id=?", (user_id,))
    data = cur.fetchone()
    if not data:
        cur.execute("INSERT INTO wallets (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return (user_id, 0.001, 0.02, 15)
    return data

def update_wallet(user_id, coin, amount):
    cur.execute(f"UPDATE wallets SET {coin} = {coin} + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def set_lang(user_id, lang):
    cur.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
    conn.commit()

def get_lang(user_id):
    cur.execute("SELECT lang FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 'en'

def set_daily(user_id):
    now = datetime.now().isoformat()
    cur.execute("UPDATE users SET last_daily=? WHERE id=?", (now, user_id))
    conn.commit()

def get_last_daily(user_id):
    cur.execute("SELECT last_daily FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None
