"""
数据库初始化脚本（仅首次建库或重置测试环境使用）。
- 与 ensure_tables 共享同一 schema 定义，字段名/枚举值完全对齐。
- 运行后会 DROP 并重建所有表，同时写入初始测试数据。
- 生产环境不应直接调用此脚本；日常启动通过 ensure_tables 补全缺失表。
"""
import sqlite3
import os
import sys
from passlib.context import CryptContext

# 支持两种运行方式：直接执行 或 作为包导入
try:
    from .db_config import SQLITE_DB_PATH
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.database.db_config import SQLITE_DB_PATH

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_database():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # ── 清空旧表（重置顺序：子表先删）─────────────────────────────────────
    tables_to_drop = [
        "adopt_records", "credit_events", "user_credit_profiles",
        "nutrition_feedbacks", "nutrition_plans", "agent_trace_logs",
        "user_sanctions", "moderation_logs", "messages", "comments",
        "posts", "applications", "announcements", "pets", "users",
    ]
    for t in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {t}")

    # ── users ──────────────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE users (
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
    cursor.execute('''CREATE TABLE pets (
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
    cursor.execute('''CREATE TABLE posts (
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
    cursor.execute('''CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── messages ───────────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        receiver_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── applications ── 字段名 apply_reason，状态值 pending/approved/rejected ─
    cursor.execute('''CREATE TABLE applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
        apply_reason TEXT,
        status TEXT DEFAULT 'pending',  -- pending, approved, rejected
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── announcements ──────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        is_hot INTEGER DEFAULT 0,
        date TEXT
    )''')

    # ── moderation_logs ────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_id INTEGER,
        admin_id INTEGER,
        reason TEXT NOT NULL,
        evidence_url TEXT,
        delete_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── user_sanctions ─────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE user_sanctions (
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
    cursor.execute('''CREATE TABLE agent_trace_logs (
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
    cursor.execute('''CREATE TABLE nutrition_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_name TEXT,
        species TEXT,
        plan_data TEXT,             -- JSON 字符串
        is_active INTEGER DEFAULT 1,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── nutrition_feedbacks ────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE nutrition_feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER REFERENCES nutrition_plans(id) ON DELETE CASCADE,
        weight_change TEXT,
        appetite_status TEXT,
        stool_status TEXT,
        activity_change TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── user_credit_profiles ───────────────────────────────────────────────
    cursor.execute('''CREATE TABLE user_credit_profiles (
        user_id INTEGER PRIMARY KEY,
        responsibility_score REAL DEFAULT 100.0,
        engagement_score REAL DEFAULT 0.0,
        community_score REAL DEFAULT 0.0,
        level TEXT DEFAULT 'Bronze',    -- Bronze, Silver, Gold, Black
        last_decay_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── credit_events ──────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE credit_events (
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

    # ── adopt_records ──────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE adopt_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
        adopt_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── 高频查询索引 ───────────────────────────────────────────────────────
    cursor.execute("CREATE INDEX idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX idx_posts_user_id ON posts(user_id)")
    cursor.execute("CREATE INDEX idx_posts_create_time ON posts(create_time)")
    cursor.execute("CREATE INDEX idx_comments_post_id ON comments(post_id)")
    cursor.execute("CREATE INDEX idx_messages_receiver_id ON messages(receiver_id)")
    cursor.execute("CREATE INDEX idx_nutrition_plans_user_id ON nutrition_plans(user_id)")
    cursor.execute("CREATE INDEX idx_applications_user_id ON applications(user_id)")
    cursor.execute("CREATE INDEX idx_agent_trace_logs_trace_id ON agent_trace_logs(trace_id)")
    cursor.execute("CREATE INDEX idx_credit_events_user_id ON credit_events(user_id)")
    cursor.execute("CREATE INDEX idx_user_sanctions_user_id ON user_sanctions(user_id)")

    # ── 种子数据 ───────────────────────────────────────────────────────────
    notices = [
        ('关于本周末在中心公园举办线下领养日的通知', '请参加活动的领养人携带好身份证件...', 1, '2026-03-05'),
        ('新上线：AI 宠物行为翻译官功能说明', '通过上传视频，AI 可以分析宠物的肢体语言...', 0, '2026-03-02'),
        ('救助站物资捐赠感谢名单公示（二月）', '感谢社会各界对流浪动物的支持...', 0, '2026-02-28'),
    ]
    cursor.executemany(
        "INSERT INTO announcements (title, content, is_hot, date) VALUES (?,?,?,?)", notices
    )

    _h = _pwd_context.hash
    test_users = [
        ('用户A',    'user@test.com',  _h('123'), 'individual', 'active', '程序员', '13800000001', '公寓', '猫'),
        ('阳光救助站', 'admin@test.com', _h('123'), 'org_admin',  'active', '站长',   '13800000002', '救助中心', '狗'),
        ('系统管理员', 'root@test.com',  _h('123'), 'root',       'active', 'IT',     '13800000003', '总部', '所有'),
    ]
    cursor.executemany(
        "INSERT INTO users (username, email, password, role, status, occupation, contact, living_env, preference) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        test_users
    )

    pets_data = [
        (2, 'org', '布丁',  '英国短毛猫',   2, '极少', '安静', '性格温和，喜欢陪伴工作中的主人。它有一双大大的金黄色眼睛，非常治愈。',
         'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=1000&auto=format&fit=crop'),
        (2, 'org', '豆包',  '比熊犬',       1, '不掉毛', '中等', '体型小，聪明，不掉毛，适合公寓居住。非常粘人，是绝佳的伴侣犬。',
         'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?q=80&w=1000&auto=format&fit=crop'),
        (2, 'org', '辛巴',  '金毛寻回犬',   3, '较多', '高', '典型的大暖男，对人非常友好，适合有院子的家庭。喜欢玩水和接球。',
         'https://images.unsplash.com/photo-1552053831-71594a27632d?q=80&w=1000&auto=format&fit=crop'),
        (2, 'org', '年糕',  '萨摩耶',       1, '非常多', '高', '微笑天使，虽然爱掉毛，但颜值极高，性格活泼。需要主人有足够的耐心打理毛发。',
         'https://images.unsplash.com/photo-1529429617329-8a79e088c02c?q=80&w=1000&auto=format&fit=crop'),
        (2, 'org', '奥利奥', '边境牧羊犬',  2, '中等', '极高', '智商天花板，能够听懂许多复杂的指令。需要大量运动和智力挑战。',
         'https://images.unsplash.com/photo-1503256207526-0df5d6342a00?q=80&w=1000&auto=format&fit=crop'),
        (2, 'org', '奶油',  '布偶猫',       1, '中等', '安静', '颜值超高，像洋娃娃一样。性格极好，任抱任摸。',
         'https://images.unsplash.com/photo-1533738363-b7f9aef128ce?q=80&w=1000&auto=format&fit=crop'),
    ]
    cursor.executemany(
        "INSERT INTO pets (owner_id, owner_type, name, species, age, is_shedding, energy_level, description, image_url) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        pets_data
    )

    conn.commit()
    conn.close()
    print("数据库初始化成功！Schema 已与 ensure_tables 对齐。")

if __name__ == "__main__":
    init_database()
