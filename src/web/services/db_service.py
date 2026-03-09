import sqlite3
import os
from src.database.db_config import SQLITE_DB_PATH

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'individual',
        status TEXT DEFAULT 'active',
        occupation TEXT,
        contact TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        content TEXT NOT NULL,
        image_url TEXT,
        type TEXT DEFAULT 'daily',
        likes INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pet_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT '待审核',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_id INTEGER,
        admin_id INTEGER,
        reason TEXT NOT NULL,
        evidence_url TEXT,
        delete_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS user_sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        admin_id INTEGER,
        type TEXT NOT NULL,
        reason TEXT NOT NULL,
        evidence_url TEXT,
        expire_date DATETIME,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS agent_trace_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trace_id TEXT NOT NULL,
        endpoint TEXT,
        agent_name TEXT,
        tool_name TEXT,
        latency_ms INTEGER,
        fallback_used INTEGER DEFAULT 0,
        input_msg TEXT,
        output_msg TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS nutrition_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pet_name TEXT,
        species TEXT,
        plan_data TEXT,
        is_active INTEGER DEFAULT 1,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS nutrition_feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER,
        weight_change TEXT,
        appetite_status TEXT,
        stool_status TEXT,
        activity_change TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
