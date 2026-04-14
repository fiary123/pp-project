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
        "user_profiles", "user_preferences", "pet_features", "pet_requirements",
        "recommendation_logs"
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

    cursor.execute('''CREATE TABLE user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        age_range TEXT, -- 年龄段: 18-25, 26-35, 36-50, 50+
        housing_type TEXT, -- 住房类型: 公寓, 别墅, 平房等
        has_yard INTEGER DEFAULT 0, -- 是否有院子: 1(是), 0(否)
        family_size INTEGER DEFAULT 1, -- 家庭人口数
        has_children INTEGER DEFAULT 0, -- 是否有小孩: 1(是), 0(否)
        has_other_pets INTEGER DEFAULT 0, -- 是否有其他宠物: 1(是), 0(否)
        housing_size REAL, -- 居住面积 (平米)
        rental_status TEXT, -- 租赁状态: 自购, 租房
        pet_experience TEXT, -- 养宠经验: 无, 1-3年, 3年以上
        experience_level INTEGER DEFAULT 0, -- 经验等级: 0(新手), 1(有经验), 2(专家)
        available_time REAL, -- 每日可投入时间 (小时)
        family_support INTEGER DEFAULT 1, -- 家庭是否支持: 1(是), 0(否)
        budget_level TEXT, -- 预算承受能力: 低, 中, 高
        allergy_info TEXT, -- 过敏情况说明
        preferred_pet_type TEXT, -- 偏好品种: 猫, 狗, 异宠
        preferred_size TEXT, -- 偏好体型: 小型, 中型, 大型
        preferred_temperament TEXT, -- 偏好性格标签
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        preferred_pet_type TEXT, -- 偏好品种: 猫, 狗, 鸟等
        preferred_age_range TEXT, -- 偏好年龄段: 幼年, 成年, 老年
        preferred_size TEXT, -- 偏好体型: 小型, 中型, 大型
        accept_special_care INTEGER DEFAULT 0, -- 是否接受特殊照顾宠物
        accept_high_energy INTEGER DEFAULT 1, -- 是否接受高能量/活泼宠物
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        source_post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
        owner_type TEXT DEFAULT 'personal',
        name TEXT NOT NULL,
        species TEXT,
        type TEXT, -- 冗余类型字段: 猫咪, 狗狗, 异宠
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

    cursor.execute('''CREATE TABLE pet_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER UNIQUE NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
        species TEXT,
        age_stage TEXT, -- 幼年, 成年, 老年
        size_level TEXT, -- 小型, 中型, 大型
        health_status TEXT, -- 健康, 患病, 残疾
        sterilized INTEGER DEFAULT 0, -- 是否绝育
        activity_level TEXT, -- 低, 中, 高
        temperament_tags TEXT, -- 性格标签: 活泼, 安静, 胆小等
        good_with_children INTEGER DEFAULT 1, -- 是否对儿童友好
        good_with_other_pets INTEGER DEFAULT 1, -- 是否对其他宠物友好
        care_difficulty TEXT, -- 照顾难度: 容易, 中等, 困难
        medical_needs TEXT, -- 特殊医疗需求
        companionship_need TEXT, -- 陪伴需求程度: 低, 中, 高
        budget_need_level TEXT, -- 开销水平: 低, 中, 高
        special_care_flag INTEGER DEFAULT 0, -- 是否需要特殊照顾
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE pet_requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER UNIQUE NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
        allow_beginner INTEGER DEFAULT 1, -- 是否允许新手领养
        min_budget_level TEXT DEFAULT '低', -- 最低预算要求
        min_companion_hours REAL DEFAULT 0, -- 最低陪伴时长要求
        required_housing_type TEXT, -- 要求的住房类型
        forbid_other_pets INTEGER DEFAULT 0, -- 是否禁止有其他宠物
        forbid_children INTEGER DEFAULT 0, -- 是否禁止有小孩
        require_experience TEXT, -- 经验要求: 无, 1-3年, 3年以上
        require_stable_housing INTEGER DEFAULT 1, -- 是否要求稳定住房
        require_return_visit INTEGER DEFAULT 1, -- 是否接受回访
        region_limit TEXT, -- 地区限制
        special_notes TEXT, -- 特殊说明
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE recommendation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scene TEXT NOT NULL, -- 如 pet_recommendation / applicant_ranking
        target_id INTEGER, -- 目标对象ID (如 pet_id 或 user_id)
        user_id INTEGER REFERENCES users(id),
        candidate_id INTEGER, -- 被推荐的候选项ID
        hard_filter_pass INTEGER DEFAULT 1, -- 是否通过硬约束过滤
        score_detail_json TEXT, -- 评分明细 (结构化 JSON)
        final_score REAL, -- 最终得分
        reason_text TEXT, -- 推荐理由/解释文本
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

    # ── 插入结构化画像与特征 (推荐系统核心数据) ──────────────────────────────
    # 1. 用户画像 (user_profiles)
    profiles = [
        (1, '26-35', '公寓', 0, 2, 0, 0, 60.0, '租房', '1-3年', 1, 4.0, 1, '中', '无', '猫', '中型', '安静'),
        (3, '18-25', '宿舍', 0, 1, 0, 0, 15.0, '租房', '无', 0, 1.0, 0, '低', '无', '鸟', '小型', '活泼'),
        (4, '36-50', '别墅', 1, 4, 1, 1, 200.0, '自购', '3年以上', 2, 8.0, 1, '高', '无', '狗', '大型', '粘人'),
        (5, '26-35', '平房', 0, 1, 0, 1, 45.0, '租房', '1-3年', 1, 2.0, 1, '中', '无', '猫', '中型', '独立'),
        (6, '26-35', '公寓', 0, 2, 0, 0, 85.0, '自购', '3年以上', 2, 3.0, 1, '中', '无', '狗', '小型', '聪明'),
    ]
    cursor.executemany(
        """INSERT INTO user_profiles (user_id, age_range, housing_type, has_yard, family_size, has_children, has_other_pets, 
           housing_size, rental_status, pet_experience, experience_level, available_time, family_support, budget_level, 
           allergy_info, preferred_pet_type, preferred_size, preferred_temperament) 
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        profiles
    )

    # 2. 用户偏好 (user_preferences)
    preferences = [
        (1, '猫', '成年', '中型', 0, 0),
        (3, '鸟', '幼年', '小型', 0, 1),
        (4, '狗', '成年', '大型', 1, 1),
        (5, '猫', '老年', '中型', 1, 0),
        (6, '狗', '幼年', '小型', 0, 1),
    ]
    cursor.executemany(
        "INSERT INTO user_preferences (user_id, preferred_pet_type, preferred_age_range, preferred_size, accept_special_care, accept_high_energy) VALUES (?,?,?,?,?,?)",
        preferences
    )

    # 3. 宠物特征 (pet_features)
    # pet_id 1: 布丁(猫), 2: 豆包(狗), 3: 辛巴(狗)
    features = [
        (1, '猫', '成年', '中型', '健康', 1, '中', '安静, 粘人', 1, 1, '容易', '', '中', '中', 0),
        (2, '狗', '幼年', '小型', '健康', 0, '高', '活泼, 粘人', 1, 1, '中等', '', '高', '中', 0),
        (3, '狗', '成年', '大型', '健康', 1, '高', '聪明, 护卫', 0, 0, '困难', '需要大空间', '高', '高', 0),
    ]
    cursor.executemany(
        """INSERT INTO pet_features (pet_id, species, age_stage, size_level, health_status, sterilized, activity_level, 
           temperament_tags, good_with_children, good_with_other_pets, care_difficulty, medical_needs, companionship_need, 
           budget_need_level, special_care_flag) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        features
    )

    # 4. 宠物领养要求 (pet_requirements)
    requirements = [
        (1, 1, '中', 2.0, '公寓', 0, 0, '无', 1, 1, '不限'),
        (2, 1, '中', 4.0, '不限', 0, 0, '1-3年', 1, 1, '不限'),
        (3, 0, '高', 6.0, '别墅', 1, 1, '3年以上', 1, 1, '本省'),
    ]
    cursor.executemany(
        """INSERT INTO pet_requirements (pet_id, allow_beginner, min_budget_level, min_companion_hours, required_housing_type, 
           forbid_other_pets, forbid_children, require_experience, require_stable_housing, require_return_visit, region_limit) 
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        requirements
    )

    conn.commit()
    conn.close()
    print("数据库初始化成功！已注入全场景模拟测试数据。")

if __name__ == "__main__":
    init_database()
