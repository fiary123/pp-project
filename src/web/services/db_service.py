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
        preference TEXT,
        avatar_url TEXT
    )''')
    try:
        cur.execute('ALTER TABLE users ADD COLUMN avatar_url TEXT')
    except Exception:
        pass

    # ── pets ───────────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        source_post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
        owner_type TEXT DEFAULT 'org',  -- org (救助站) or personal (个人送养)
        name TEXT NOT NULL,
        species TEXT,
        age INTEGER DEFAULT 1,
        is_shedding TEXT,
        energy_level TEXT,
        description TEXT,
        image_url TEXT,
        image_urls TEXT,
        adoption_preferences TEXT,
        tags TEXT DEFAULT '[]',
        lng REAL,
        lat REAL,
        status TEXT DEFAULT '待领养',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    try:
        cur.execute('ALTER TABLE pets ADD COLUMN image_urls TEXT')
    except Exception:
        pass
    try:
        cur.execute('ALTER TABLE pets ADD COLUMN adoption_preferences TEXT')
    except Exception:
        pass
    try:
        cur.execute('ALTER TABLE pets ADD COLUMN source_post_id INTEGER')
    except Exception:
        pass

    # ── posts ──────────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        title TEXT,
        content TEXT NOT NULL,
        image_url TEXT,
        image_urls TEXT,
        type TEXT DEFAULT 'daily',
        pet_name TEXT,
        pet_gender TEXT,
        pet_age TEXT,
        pet_breed TEXT,
        adopt_reason TEXT,
        location TEXT,
        likes INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    # 迁移：为旧数据库动态加列
    for col, definition in [
        ('image_urls', 'TEXT'),
        ('pet_name', 'TEXT'),
        ('pet_gender', 'TEXT'),
        ('pet_age', 'TEXT'),
        ('pet_breed', 'TEXT'),
        ('adopt_reason', 'TEXT'),
        ('location', 'TEXT'),
    ]:
        try:
            cur.execute(f'ALTER TABLE posts ADD COLUMN {col} {definition}')
        except Exception:
            pass

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
    for col, definition in [
        ('pet_owner_id', 'INTEGER'),
        ('ai_decision', 'TEXT'),
        ('ai_readiness_score', 'REAL'),
        ('ai_summary', 'TEXT'),
        ('assessment_payload', 'TEXT'),
        ('flow_status', 'TEXT'),
        ('risk_level', 'TEXT'),
        ('consensus_score', 'REAL'),
        ('missing_fields', 'TEXT'),
        ('conflict_notes', 'TEXT'),
        ('followup_questions', 'TEXT'),
        ('evaluation_trace_id', 'TEXT'),
        ('evaluation_started_at', 'DATETIME'),
        ('evaluation_finished_at', 'DATETIME'),
        ('evaluation_error', 'TEXT'),
        ('publisher_feedback', 'TEXT'),
        ('manual_review_reason', 'TEXT'),
        ('memory_scope', 'TEXT'),
        ('feedback_written', 'INTEGER DEFAULT 0'),
        ('owner_note', 'TEXT'),
        ('owner_followed_ai', 'INTEGER'),
        ('decision_by', 'INTEGER'),
        ('decision_time', 'DATETIME'),
        ('accept_return_visit', 'INTEGER DEFAULT 0'),
        ('application_reason', 'TEXT'),
    ]:
        try:
            cur.execute(f'ALTER TABLE applications ADD COLUMN {col} {definition}')
        except Exception:
            pass

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

    # ── publisher_preferences ──────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS publisher_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        publisher_id INTEGER,
        pet_id INTEGER,
        hard_constraints_json TEXT DEFAULT '[]',
        soft_preferences_json TEXT DEFAULT '[]',
        risk_tolerance TEXT DEFAULT 'medium',
        raw_preferences_json TEXT DEFAULT '{}',
        version INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(publisher_id, pet_id)
    )''')

    # ── adoption_ai_reviews ────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adoption_ai_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        trace_id TEXT,
        agent_outputs_json TEXT DEFAULT '[]',
        consensus_result_json TEXT DEFAULT '{}',
        route_decision TEXT DEFAULT '',
        overall_score REAL,
        consensus_score REAL,
        disagreement_score REAL,
        risk_level TEXT DEFAULT 'Medium',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── adoption_followups ─────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adoption_followups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        question TEXT,
        answer TEXT,
        source TEXT DEFAULT 'applicant',
        impact_score REAL DEFAULT 0.0,
        trace_id TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── adoption_case_memory ───────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adoption_case_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER UNIQUE,
        case_summary TEXT,
        decision_result TEXT DEFAULT '',
        owner_followed_ai INTEGER,
        followup_outcome TEXT DEFAULT '',
        risk_tags_json TEXT DEFAULT '[]',
        feedback_id INTEGER,
        embedding_status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── adoption_flow_events ───────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adoption_flow_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        event_type TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT,
        actor_role TEXT DEFAULT '',
        actor_id INTEGER,
        payload_json TEXT DEFAULT '{}',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── adoption_signal_weights ────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adoption_signal_weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_type TEXT NOT NULL,
        signal_key TEXT NOT NULL,
        positive_count INTEGER DEFAULT 0,
        negative_count INTEGER DEFAULT 0,
        weight REAL DEFAULT 0,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(signal_type, signal_key)
    )''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pet_chat_history_user_pet ON pet_chat_history(user_id, pet_name)")

    # ── pet_chat_profiles ──────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS pet_chat_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_name TEXT NOT NULL,
        profile_json TEXT DEFAULT '{}',
        summary TEXT DEFAULT '',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, pet_name)
    )''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pet_chat_profiles_user_pet ON pet_chat_profiles(user_id, pet_name)")

    # ── adopt_records ──────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS adopt_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
        adopt_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── mutual_aid_tasks ───────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS mutual_aid_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        task_type TEXT NOT NULL,        -- 上门喂养/上门铲屎/代遛狗/宠物陪伴/其他互助
        pet_name TEXT NOT NULL,
        pet_species TEXT DEFAULT '猫',
        start_time TEXT NOT NULL,
        end_time TEXT,
        location TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'open',     -- open, accepted, completed, cancelled
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── mutual_aid_orders ──────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS mutual_aid_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER REFERENCES mutual_aid_tasks(id) ON DELETE CASCADE,
        helper_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'accepted', -- accepted, completed, cancelled
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mutual_aid_tasks_user_id ON mutual_aid_tasks(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mutual_aid_tasks_status ON mutual_aid_tasks(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mutual_aid_orders_task_id ON mutual_aid_orders(task_id)")

    # ── mutual_aid_reports ─────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS mutual_aid_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER REFERENCES mutual_aid_tasks(id) ON DELETE CASCADE,
        reporter_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'pending',   -- pending, resolved_cancel, resolved_dismiss
        resolve_note TEXT,
        admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolve_time DATETIME
    )''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mutual_aid_reports_status ON mutual_aid_reports(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_mutual_aid_reports_task_id ON mutual_aid_reports(task_id)")

    # ── 高频查询索引 ───────────────────────────────────────────────────────
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_create_time ON posts(create_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver_id ON messages(receiver_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_nutrition_plans_user_id ON nutrition_plans(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_applications_flow_status ON applications(flow_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_applications_pet_owner_id ON applications(pet_owner_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_trace_logs_trace_id ON agent_trace_logs(trace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_ai_reviews_application_id ON adoption_ai_reviews(application_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_ai_reviews_trace_id ON adoption_ai_reviews(trace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_followups_application_id ON adoption_followups(application_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_case_memory_application_id ON adoption_case_memory(application_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_flow_events_application_id ON adoption_flow_events(application_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_flow_events_type ON adoption_flow_events(event_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_adoption_signal_weights_type_key ON adoption_signal_weights(signal_type, signal_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_events_user_id ON credit_events(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sanctions_user_id ON user_sanctions(user_id)")

    # ── notifications ──────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        type TEXT NOT NULL,         -- system, moderation, credit
        title TEXT,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)")

    # ── email_codes ────────────────────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS email_codes (
        email TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        expire_at DATETIME NOT NULL
    )''')

    # ── user_profiles (Phase 1) ───────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        housing_type TEXT,
        housing_size REAL,
        rental_status TEXT,
        pet_experience TEXT,
        available_time REAL,
        family_support INTEGER DEFAULT 1,
        budget_level TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── user_preferences (Phase 1) ────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        preferred_pet_type TEXT,
        preferred_age_range TEXT,
        preferred_size TEXT,
        accept_special_care INTEGER DEFAULT 0,
        accept_high_energy INTEGER DEFAULT 1,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── pet_features (Phase 1) ───────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS pet_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER UNIQUE NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
        energy_level TEXT,
        care_level TEXT,
        beginner_friendly INTEGER DEFAULT 1,
        social_level TEXT,
        special_care_flag INTEGER DEFAULT 0,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── pet_requirements (Phase 1) ────────────────────────────────────────
    cur.execute('''CREATE TABLE IF NOT EXISTS pet_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER UNIQUE NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
        require_experience TEXT,
        require_stable_housing INTEGER DEFAULT 1,
        require_return_visit INTEGER DEFAULT 1,
        region_limit TEXT,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
