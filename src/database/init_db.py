"""
数据库初始化脚本 - 增强版种子数据
- 包含丰富的管理员测试数据：不同信用等级、全流程状态、全风险等级。
"""
import sqlite3
import os
import sys
import json
from datetime import datetime, timedelta
from passlib.context import CryptContext

try:
    from .db_config import SQLITE_DB_PATH
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.database.db_config import SQLITE_DB_PATH

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_database():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # ── 清空旧表 ──────────────────────────────────────────────────────────
    tables_to_drop = [
        "adopt_records", "credit_events", "user_credit_profiles",
        "nutrition_feedbacks", "nutrition_plans", "agent_trace_logs",
        "user_sanctions", "moderation_logs", "pet_chat_profiles", "pet_chat_history",
        "messages", "comments", "posts", "applications", "announcements", "pets", "users",
    ]
    for t in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {t}")

    # ── 建表逻辑 (与 ensure_tables 对齐) ───────────────────────────────────
    cursor.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active',
        occupation TEXT,
        contact TEXT,
        living_env TEXT,
        preference TEXT
    )''')

    cursor.execute('''CREATE TABLE pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        source_post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
        owner_type TEXT DEFAULT 'personal',
        name TEXT NOT NULL,
        species TEXT,
        age INTEGER DEFAULT 1,
        is_shedding TEXT,
        energy_level TEXT,
        description TEXT,
        image_url TEXT,
        adoption_preferences TEXT,
        tags TEXT DEFAULT '[]',
        lng REAL, lat REAL,
        status TEXT DEFAULT '待领养',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
        apply_reason TEXT,
        pet_owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        ai_decision TEXT,
        ai_readiness_score REAL,
        ai_summary TEXT,
        assessment_payload TEXT,
        flow_status TEXT DEFAULT 'submitted', -- submitted, need_more_info, waiting_publisher, manual_review, approved, rejected
        risk_level TEXT DEFAULT 'Medium',    -- Low, Medium, High
        consensus_score REAL,
        missing_fields TEXT,
        conflict_notes TEXT,
        followup_questions TEXT,
        evaluation_trace_id TEXT,
        evaluation_started_at DATETIME,
        evaluation_finished_at DATETIME,
        evaluation_error TEXT,
        publisher_feedback TEXT,
        manual_review_reason TEXT,
        memory_scope TEXT,
        feedback_written INTEGER DEFAULT 0,
        owner_note TEXT,
        owner_followed_ai INTEGER DEFAULT 0, -- 关键缺失字段
        decision_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        decision_time DATETIME,
        status TEXT DEFAULT 'pending_owner_review',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE user_credit_profiles (
        user_id INTEGER PRIMARY KEY,
        responsibility_score REAL DEFAULT 100.0,
        engagement_score REAL DEFAULT 0.0,
        community_score REAL DEFAULT 0.0,
        level TEXT DEFAULT 'Bronze',
        last_decay_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    cursor.execute('''CREATE TABLE announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        is_hot INTEGER DEFAULT 0,
        date TEXT
    )''')

    cursor.execute('''CREATE TABLE posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        title TEXT,
        content TEXT NOT NULL,
        image_url TEXT,
        type TEXT DEFAULT 'daily',
        likes INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # ── 插入用户数据 ──────────────────────────────────────────────────────
    _h = _pwd_context.hash
    users = [
        ('用户A', 'user@test.com', _h('123'), 'user', '程序员', '1380001', '公寓', '猫'),
        ('系统管理员', 'root@test.com', _h('123'), 'admin', 'IT', '1380002', '办公室', '所有'),
        ('李雷', 'lilei@test.com', _h('123'), 'user', '学生', '1380003', '宿舍', '狗'),
        ('韩梅梅', 'han@test.com', _h('123'), 'user', '教师', '1380004', '别墅', '金毛'),
        ('张三', 'zhang@test.com', _h('123'), 'user', '自由职业', '1380005', '平房', '布偶猫'),
        ('王五', 'wang@test.com', _h('123'), 'user', '医生', '1380006', '公寓', '柯基'),
    ]
    cursor.executemany(
        "INSERT INTO users (username, email, password, role, occupation, contact, living_env, preference) VALUES (?,?,?,?,?,?,?,?)",
        users
    )

    # ── 插入信用档案 (涵盖高中低等级) ─────────────────────────────────────
    credits = [
        (1, 95.0, 80.0, 70.0, 'Gold'),    # 用户A
        (2, 100.0, 100.0, 100.0, 'Black'), # 管理员
        (3, 45.0, 10.0, 5.0, 'Bronze'),   # 李雷 (等级低)
        (4, 85.0, 60.0, 50.0, 'Silver'),  # 韩梅梅
        (5, 70.0, 40.0, 30.0, 'Bronze'),  # 张三
        (6, 110.0, 90.0, 85.0, 'Gold'),   # 王五
    ]
    cursor.executemany(
        "INSERT INTO user_credit_profiles (user_id, responsibility_score, engagement_score, community_score, level) VALUES (?,?,?,?,?)",
        credits
    )

    # ── 插入宠物数据 ──────────────────────────────────────────────────────
    pets = [
        (1, 'personal', '布丁', '猫', 2, '极少', '安静', '温和的猫', 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=500'),
        (1, 'personal', '豆包', '狗', 1, '不掉毛', '活跃', '可爱的比熊', 'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?w=500'),
        (4, 'personal', '辛巴', '狗', 3, '多', '高', '霸气的金毛', 'https://images.unsplash.com/photo-1552053831-71594a27632d?w=500'),
    ]
    cursor.executemany(
        "INSERT INTO pets (owner_id, owner_type, name, species, age, is_shedding, energy_level, description, image_url) VALUES (?,?,?,?,?,?,?,?,?)",
        pets
    )

    # ── 插入领养申请 (涵盖所有流程状态、风险等级和冲突/追问) ──────────────
    # status: pending_owner_review, approved, rejected
    # flow_status: submitted, need_more_info, waiting_publisher, manual_review, approved, rejected
    apps = [
        # 1. 已提交 + Low风险
        (3, 1, '我很喜欢猫，有耐心。', 1, 'Low', 'submitted', 'pending_owner_review', '[]', '[]', '[]'),
        
        # 2. 等待补充信息 + Medium风险 + 缺失字段
        (5, 2, '想要一只狗陪我。', 1, 'Medium', 'need_more_info', 'pending_owner_review', 
         json.dumps(['居住面积', '家庭成员意见']), '[]', json.dumps(['请补充您的居住面积详情', '家里其他人同意养狗吗？'])),
        
        # 3. 等待发布者处理 + High风险 + 冲突记录
        (3, 3, '给孩子买个玩具。', 4, 'High', 'waiting_publisher', 'pending_owner_review', 
         '[]', json.dumps(['动机不纯：将宠物视为玩具', '学生身份：经济来源不稳定']), '[]'),
        
        # 4. 进入人工复核 + Medium风险 + 冲突记录
        (6, 1, '有丰富的养猫经验，家里已经有一只了。', 1, 'Medium', 'manual_review', 'pending_owner_review', 
         '[]', json.dumps(['环境兼容性：需要核实原住宠物的反应']), '[]'),
        
        # 5. 流程通过 + Low风险
        (4, 1, '家里环境很大，有全职太太照顾。', 1, 'Low', 'approved', 'approved', '[]', '[]', '[]'),
        
        # 6. 流程拒绝 + High风险
        (5, 3, '我就想要最贵的。', 4, 'High', 'rejected', 'rejected', '[]', json.dumps(['极其不负责任的发言']), '[]'),
        
        # 7. 提交 + Medium风险 + 追问
        (1, 3, '我想领养辛巴。', 4, 'Medium', 'submitted', 'pending_owner_review', '[]', '[]', 
         json.dumps(['你每天能陪它多久？', '如果它生病了你打算怎么办？'])),
    ]
    
    for app in apps:
        cursor.execute(
            """INSERT INTO applications 
               (user_id, pet_id, apply_reason, pet_owner_id, risk_level, flow_status, status, missing_fields, conflict_notes, followup_questions) 
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            app
        )

    # ── 插入公告和帖子 ────────────────────────────────────────────────────
    cursor.execute("INSERT INTO announcements (title, content, is_hot, date) VALUES (?,?,?,?)", 
                   ('新版管理后台上线', '管理员现在可以更直观地筛选申请了。', 1, '2026-03-27'))
    
    cursor.execute("INSERT INTO posts (user_id, title, content, type) VALUES (?,?,?,?)",
                   (1, '晒晒我的猫', '布丁今天特别乖。', 'daily'))

    conn.commit()
    conn.close()
    print("数据库初始化成功！已注入全场景模拟测试数据。")

if __name__ == "__main__":
    init_database()
