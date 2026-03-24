import sqlite3
import os
from contextlib import contextmanager
from src.database.db_config import SQLITE_DB_PATH

def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
    return conn

@contextmanager
def get_db():
    """上下文管理器：自动处理连接的关闭，防止连接泄漏"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def ensure_tables(conn: sqlite3.Connection):
    """
    以 CREATE TABLE IF NOT EXISTS 保证表结构与 init_db.py 一致。
    本函数只补全缺失表/字段，不 DROP 任何已有数据。
    字段命名、状态枚举与 init_db.py 保持统一。
    """
    cur = conn.cursor()

    # ── users ──────────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'individual',
        status TEXT DEFAULT 'active',   -- active, muted, banned
        occupation TEXT,
        contact TEXT,
        living_env TEXT,
        preference TEXT
    )''')

    # ── pets ───────────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        owner_type TEXT DEFAULT 'org',  -- org (救助站) or personal (个人送养)
        name TEXT NOT NULL,
        species TEXT,
        age INTEGER DEFAULT 1,
        is_shedding TEXT,
        energy_level TEXT,
        description TEXT,
        image_url TEXT,
        tags TEXT DEFAULT '[]',
        lng REAL,
        lat REAL,
        status TEXT DEFAULT '待领养',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── posts ──────────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        title TEXT,
        content TEXT NOT NULL,
        image_url TEXT,
        type TEXT DEFAULT 'daily',  -- daily, experience, adopt_help, seek_help
        likes INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── comments ───────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── messages ───────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── applications ── 统一字段名 apply_reason，状态 pending/approved/rejected ──
    cur.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
        apply_reason TEXT,
        status TEXT DEFAULT 'pending',  -- pending, approved, rejected
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── announcements ──────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        is_hot INTEGER DEFAULT 0,
        date TEXT
    )''')

    # ── moderation_logs ────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_id INTEGER,
        admin_id INTEGER,
        reason TEXT NOT NULL,
        evidence_url TEXT,
        delete_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── user_sanctions ─────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS user_sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        admin_id INTEGER,
        type TEXT NOT NULL,         -- MUTE, BAN
        reason TEXT NOT NULL,
        evidence_url TEXT,
        expire_date DATETIME,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── agent_trace_logs ───────────────────────────────────────────────────
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

    # ── nutrition_plans ────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS nutrition_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_name TEXT,
        species TEXT,
        plan_data TEXT,             -- JSON 字符串
        is_active INTEGER DEFAULT 1,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── nutrition_feedbacks ────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS nutrition_feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER REFERENCES nutrition_plans(id) ON DELETE CASCADE,
        weight_change TEXT,
        appetite_status TEXT,
        stool_status TEXT,
        activity_change TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── user_credit_profiles ───────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS user_credit_profiles (
        user_id INTEGER PRIMARY KEY,
        responsibility_score REAL DEFAULT 100.0,
        engagement_score REAL DEFAULT 0.0,
        community_score REAL DEFAULT 0.0,
        level TEXT DEFAULT 'Bronze',    -- Bronze, Silver, Gold, Black
        last_decay_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── credit_events ──────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS credit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_type TEXT NOT NULL,   -- visit_report, course_done, help_others, pet_return
        dimension TEXT NOT NULL,    -- responsibility, engagement, community
        content TEXT,
        base_points REAL,
        llm_multiplier REAL,
        final_points REAL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── pet_chat_history ───────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS pet_chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_name TEXT NOT NULL,
        role TEXT NOT NULL,        -- 'user' or 'pet'
        content TEXT NOT NULL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pet_chat_history_user_pet ON pet_chat_history(user_id, pet_name)")

    # ── adopt_records ──────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adopt_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
        adopt_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── 高频查询索引 ───────────────────────────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_create_time ON posts(create_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver_id ON messages(receiver_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nutrition_plans_user_id ON nutrition_plans(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_trace_logs_trace_id ON agent_trace_logs(trace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_events_user_id ON credit_events(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sanctions_user_id ON user_sanctions(user_id)")

    conn.commit()
