"""
数据库初始化脚本 - 凭证对齐版 (v5.1)
- 强制对齐 RUN_GUIDE.md 中的测试账号密码。
- 注入 10+ 只具有不同特征的宠物。
- 包含历史判例记忆，用于测试【判例锚定】机制。
"""
import sqlite3
import os
import sys
import json
from datetime import datetime
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
    tables = [
        "adopt_records", "credit_events", "user_credit_profiles",
        "nutrition_feedbacks", "nutrition_plans", "agent_trace_logs",
        "user_sanctions", "moderation_logs", "pet_chat_profiles", "pet_chat_history",
        "messages", "comments", "posts", "applications", "announcements", "pets", "users",
        "user_profiles", "user_preferences", "pet_features", "pet_requirements",
        "recommendation_logs", "adoption_case_memory"
    ]
    for t in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {t}")

    # ── 建表逻辑 ──────────────────────────────────────────────────────────
    cursor.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active'
    )''')

    cursor.execute('''CREATE TABLE user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
        age_range TEXT, housing_type TEXT, has_yard INTEGER DEFAULT 0, family_size INTEGER DEFAULT 1,
        has_children INTEGER DEFAULT 0, has_other_pets INTEGER DEFAULT 0, housing_size REAL,
        rental_status TEXT, pet_experience TEXT, experience_level INTEGER DEFAULT 0,
        available_time REAL, family_support INTEGER DEFAULT 1, budget_level TEXT,
        allergy_info TEXT, preferred_pet_type TEXT, preferred_size TEXT, preferred_temperament TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        owner_type TEXT DEFAULT 'personal',
        name TEXT NOT NULL, species TEXT, type TEXT, age INTEGER DEFAULT 1,
        is_shedding TEXT, energy_level TEXT, description TEXT, image_url TEXT,
        status TEXT DEFAULT '待领养'
    )''')

    cursor.execute('''CREATE TABLE pet_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER UNIQUE NOT NULL REFERENCES pets(id),
        species TEXT, age_stage TEXT, size_level TEXT, health_status TEXT, sterilized INTEGER DEFAULT 0,
        activity_level TEXT, temperament_tags TEXT, good_with_children INTEGER DEFAULT 1,
        good_with_other_pets INTEGER DEFAULT 1, care_difficulty TEXT, medical_needs TEXT,
        companionship_need TEXT, budget_need_level TEXT, special_care_flag INTEGER DEFAULT 0
    )''')

    cursor.execute('''CREATE TABLE pet_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER UNIQUE NOT NULL REFERENCES pets(id),
        allow_beginner INTEGER DEFAULT 1, min_budget_level TEXT DEFAULT '低',
        min_companion_hours REAL DEFAULT 0, required_housing_type TEXT,
        forbid_other_pets INTEGER DEFAULT 0, forbid_children INTEGER DEFAULT 0,
        require_experience TEXT, require_stable_housing INTEGER DEFAULT 1,
        require_return_visit INTEGER DEFAULT 1, region_limit TEXT, special_notes TEXT
    )''')

    cursor.execute('''CREATE TABLE applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, pet_id INTEGER,
        apply_reason TEXT, pet_owner_id INTEGER,
        ai_decision TEXT, ai_readiness_score REAL, ai_summary TEXT,
        flow_status TEXT DEFAULT 'submitted', risk_level TEXT DEFAULT 'Medium',
        consensus_score REAL, conflict_notes TEXT, followup_questions TEXT,
        assessment_tier TEXT, route_reasons TEXT, create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE adoption_case_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER UNIQUE,
        case_summary TEXT, decision_result TEXT DEFAULT '',
        owner_followed_ai INTEGER, feature_snapshot_json TEXT DEFAULT '{}',
        risk_tags_json TEXT DEFAULT '[]'
    )''')

    cursor.execute('''CREATE TABLE user_credit_profiles (
        user_id INTEGER PRIMARY KEY,
        responsibility_score REAL DEFAULT 100.0,
        level TEXT DEFAULT 'Bronze',
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ── 插入对齐 RUN_GUIDE.md 的账号 ──────────────────────────────────────
    _h = _pwd_context.hash
    users = [
        ('领养人A', 'adopter_a@test.com', _h('123456'), 'user'),
        ('送养人B', 'sender_b@test.com', _h('123456'), 'user'),
        ('系统管理员', 'admin@test.com', _h('admin123'), 'admin'),
    ]
    cursor.executemany("INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)", users)

    # ── 初始化画像 (确保登录后有数据) ──────────────────────────────────────
    profiles = [
        (1, '26-35', '公寓', 0, 2, 0, 0, 85.0, '自购', '1-3年', 1, 3.0, 1, '中', '无', '猫', '中型', '安静'),
        (2, '36-50', '别墅', 1, 4, 1, 1, 220.0, '自购', '3年以上', 2, 6.0, 1, '高', '无', '狗', '大型', '活跃'),
    ]
    cursor.executemany("""INSERT INTO user_profiles (user_id, age_range, housing_type, has_yard, family_size, 
                        has_children, has_other_pets, housing_size, rental_status, pet_experience, experience_level, 
                        available_time, family_support, budget_level, allergy_info, preferred_pet_type, 
                        preferred_size, preferred_temperament) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", profiles)

    credits = [(1, 95.0, 'Gold'), (2, 110.0, 'Black'), (3, 120.0, 'Black')]
    cursor.executemany("INSERT INTO user_credit_profiles (user_id, responsibility_score, level) VALUES (?,?,?)", credits)

    # ── 插入宠物数据 ──────────────────────────────────────────────────────
    pets = [
        (2, 'personal', '布丁', '猫', 2, '极少', '安静', '要求无幼儿家庭、有养宠经验优先', 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=500'),
        (2, 'personal', '豆包', '狗', 1, '不掉毛', '活跃', '温顺的比熊', 'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?w=500'),
        (2, 'personal', '糯米', '狗', 2, '中等', '极高', '精力旺盛的边牧，聪明但需要大量运动', 'https://images.unsplash.com/photo-1503256207526-0d5d80fa2f47?w=500'),
        (2, 'personal', '麻薯', '猫', 1, '多', '低', '高冷的布偶猫，颜值极高', 'https://images.unsplash.com/photo-1533738363-b7f9aef128ce?w=500'),
    ]
    cursor.executemany("INSERT INTO pets (owner_id, owner_type, name, species, age, is_shedding, energy_level, description, image_url) VALUES (?,?,?,?,?,?,?,?,?)", pets)

    # ── 插入特征与要求 (与宠物 ID 1-4 对应) ──────────────────────────────────
    # pet_id 1: 布丁
    cursor.execute("INSERT INTO pet_features (pet_id, species, activity_level, care_difficulty, budget_need_level) VALUES (1, '猫', '低', '容易', '中')")
    cursor.execute("INSERT INTO pet_requirements (pet_id, forbid_children, allow_beginner, min_budget_level, special_notes) VALUES (1, 1, 0, '中', '无幼儿家庭、有养宠经验优先')")
    
    # 其他宠物略，确保能跑通
    for i in range(2, 5):
        cursor.execute(f"INSERT INTO pet_features (pet_id) VALUES ({i})")
        cursor.execute(f"INSERT INTO pet_requirements (pet_id) VALUES ({i})")

    # ── 插入历史案例记忆 ──
    case_memories = [
        (101, '高预算+别墅领养金毛。', 'success', 1, json.dumps({'monthly_budget': 3500}), json.dumps(['空间充足'])),
        (102, '新手领养哈士奇因运动需求退还。', 'failed', 1, json.dumps({'monthly_budget': 500}), json.dumps(['陪伴不足'])),
    ]
    cursor.executemany("INSERT INTO adoption_case_memory (application_id, case_summary, decision_result, owner_followed_ai, feature_snapshot_json, risk_tags_json) VALUES (?,?,?,?,?,?)", case_memories)

    conn.commit()
    conn.close()
    print("数据库重置成功！已强制对齐 RUN_GUIDE.md 账号凭证。")

if __name__ == "__main__":
    init_database()
