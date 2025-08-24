# db.py
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = "bot_logs.db"

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    first_seen TEXT,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    user_id INTEGER,
    username TEXT,
    full_name TEXT,
    chat_id INTEGER,
    message_id INTEGER,
    event_type TEXT, -- command, message, callback, system
    content TEXT,    -- plain text of message or command
    callback_data TEXT,
    ip TEXT,
    metadata TEXT,   -- JSON for extensibility
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    user_id INTEGER,
    username TEXT,
    full_name TEXT,
    error_message TEXT,
    traceback TEXT,
    metadata TEXT
);
"""

def init_dbs():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()
    conn.close()

def _get_conn():
    return sqlite3.connect(DB_PATH, timeout=30)

def upsert_user(user_id:int, username:Optional[str], full_name:Optional[str]):
    conn = _get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cur.fetchone():
        cur.execute(
            "UPDATE users SET username=?, full_name=?, last_seen=? WHERE user_id=?",
            (username, full_name, now, user_id)
        )
    else:
        cur.execute(
            "INSERT INTO users (user_id, username, full_name, first_seen, last_seen) VALUES (?,?,?,?,?)",
            (user_id, username, full_name, now, now)
        )
    conn.commit()
    conn.close()

def insert_event(ts: str, user_id: Optional[int], username: Optional[str],
                 full_name: Optional[str], chat_id: Optional[int],
                 message_id: Optional[int], event_type: str, content: Optional[str],
                 callback_data: Optional[str], ip: Optional[str], metadata: Optional[Dict[str,Any]]):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO events (ts, user_id, username, full_name, chat_id, message_id, event_type, content, callback_data, ip, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, user_id, username, full_name, chat_id, message_id, event_type, content, callback_data, ip, json.dumps(metadata or {})))
    conn.commit()
    conn.close()

def insert_error(ts: str, user_id: Optional[int], username: Optional[str], full_name: Optional[str],
                 error_message: str, traceback_str: str, metadata: Optional[Dict[str,Any]]):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO errors (ts, user_id, username, full_name, error_message, traceback, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ts, user_id, username, full_name, error_message, traceback_str, json.dumps(metadata or {})))
    conn.commit()
    conn.close()
