import sqlite3
from .db_config import SQLITE_DB_PATH

def init_database():
    # 连接数据库
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # 1. 创建用户表 (增加 email 唯一约束)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, 
            password TEXT NOT NULL,
            role TEXT DEFAULT 'individual', -- 'individual', 'org_admin', 'root'
            occupation TEXT,
            living_env TEXT,
            preference TEXT,
            contact TEXT
        )
    ''')

    # 2. 宠物表 (区分发布者)
    cursor.execute("DROP TABLE IF EXISTS pets")
    cursor.execute('''
        CREATE TABLE pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            name TEXT NOT NULL,
            species TEXT,
            age INTEGER,
            is_shedding TEXT,
            energy_level TEXT,
            description TEXT,
            status TEXT DEFAULT '待领养', 
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    ''')

    # 3. 领养申请表
    cursor.execute("DROP TABLE IF EXISTS applications")
    cursor.execute('''
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER,
            applicant_id INTEGER,
            user_name TEXT,
            contact TEXT,
            reason TEXT,
            ai_opinion TEXT,
            status TEXT DEFAULT '待审核',
            apply_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pet_id) REFERENCES pets (id),
            FOREIGN KEY (applicant_id) REFERENCES users (id)
        )
    ''')

    # 4. 插入初始测试账号
    test_users = [
        ('用户A', 'user@test.com', '123', 'individual', '程序员', '公寓', '猫', '13800000001'),
        ('阳光救助站', 'admin@test.com', '123', 'org_admin', '站长', '救助中心', '狗', '13800000002'),
        ('系统管理员', 'root@test.com', '123', 'root', 'IT', '总部', '所有', '13800000003')
    ]
    cursor.executemany("INSERT INTO users (username, email, password, role, occupation, living_env, preference, contact) VALUES (?,?,?,?,?,?,?,?)", test_users)

    # 5. 插入初始宠物 (由 admin 发布)
    cursor.execute("INSERT INTO pets (owner_id, name, species, age, is_shedding, energy_level, description) VALUES (?,?,?,?,?,?,?)",
                   (2, '布丁', '英国短毛猫', 2, '极少', '安静', '性格温和，喜欢陪伴工作中的主人'))
    cursor.execute("INSERT INTO pets (owner_id, name, species, age, is_shedding, energy_level, description) VALUES (?,?,?,?,?,?,?)",
                   (2, '豆包', '比熊犬', 1, '不掉毛', '中等', '体型小，聪明，不掉毛，适合公寓'))

    conn.commit()
    conn.close()
    print("✅ 数据库重置成功！邮箱唯一约束已生效。")

if __name__ == "__main__":
    init_database()
