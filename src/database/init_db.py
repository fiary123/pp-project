import sqlite3
from .db_config import SQLITE_DB_PATH

def init_database():
    # 连接数据库（不存在则自动创建）
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # 1. 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            occupation TEXT,        -- 职业
            living_env TEXT,        -- 居住环境
            preference TEXT         -- 宠物偏好
        )
    ''')

    # 2. 创建宠物表（Agent 将从中筛选）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT,           -- 品种
            age INTEGER,
            is_shedding TEXT,       -- 是否掉毛
            energy_level TEXT,      -- 活跃程度 (安静/活泼)
            description TEXT,       -- 详细描述
            status TEXT DEFAULT '待领养'
        )
    ''')

    # 3. 创建领养/匹配记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adopt_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            pet_id INTEGER,
            match_score INTEGER,    -- 匹配度分值
            ai_advice TEXT,         -- Agent 给出的推荐理由
            apply_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (pet_id) REFERENCES pets (id)
        )
    ''')

    # 插入一些初始宠物数据供 Agent 筛选
    cursor.execute("INSERT INTO pets (name, species, age, is_shedding, energy_level, description) VALUES (?, ?, ?, ?, ?, ?)",
                   ('布丁', '英国短毛猫', 2, '极少', '安静', '性格温和，喜欢陪伴工作中的主人'))
    
    cursor.execute("INSERT INTO pets (name, species, age, is_shedding, energy_level, description) VALUES (?, ?, ?, ?, ?, ?)",
                   ('豆包', '比熊犬', 1, '不掉毛', '中等', '体型小，聪明，不掉毛，适合公寓'))

    conn.commit()
    conn.close()
    print("✅ 数据库 pet_adoption.db 已创建并初始化成功！")

if __name__ == "__main__":
    init_database()