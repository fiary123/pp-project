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
    # 连接数据库
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # 1. 创建用户表 (增加 status 字段)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, 
            password TEXT NOT NULL,
            role TEXT DEFAULT 'individual', 
            occupation TEXT,
            living_env TEXT,
            preference TEXT,
            contact TEXT,
            status TEXT DEFAULT 'active' -- active, muted, banned
        )
    ''')

    # ... (中间 pets, applications, announcements, moderation_logs 保持不变)

    # 6. 用户处罚存证表 (新增)
    cursor.execute("DROP TABLE IF EXISTS user_sanctions")
    cursor.execute('''
        CREATE TABLE user_sanctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            admin_id INTEGER,
            type TEXT NOT NULL, -- MUTE, BAN
            reason TEXT NOT NULL,
            evidence_url TEXT,
            expire_date DATETIME, -- 处罚截止时间，NULL 表示永久
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. 宠物表 (扩展：增加 owner_type 区分个人/机构)
    cursor.execute("DROP TABLE IF EXISTS pets")
    cursor.execute('''
        CREATE TABLE pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            owner_type TEXT DEFAULT 'org', -- 'org' (救助站) or 'personal' (个人送养)
            name TEXT NOT NULL,
            species TEXT,
            age INTEGER,
            is_shedding TEXT,
            energy_level TEXT,
            description TEXT,
            image_url TEXT,
            lng REAL,
            lat REAL,
            status TEXT DEFAULT '待领养', 
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    ''')

    # 7. 社区动态表
    cursor.execute("DROP TABLE IF EXISTS posts")
    cursor.execute('''
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT NOT NULL,
            image_url TEXT,
            type TEXT DEFAULT 'daily', -- daily, experience, adopt_help (个人送养), seek_help (求收养)
            likes INTEGER DEFAULT 0,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 8. 评论表 (支持盖楼)
    cursor.execute("DROP TABLE IF EXISTS comments")
    cursor.execute('''
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            parent_id INTEGER DEFAULT NULL, -- 新增：指向父评论 ID
            content TEXT NOT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (parent_id) REFERENCES comments (id)
        )
    ''')

    # 9. 私信表 (新增)
    cursor.execute("DROP TABLE IF EXISTS messages")
    cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    ''')

    # ... (保持 applications, announcements, moderation_logs, user_sanctions 结构不变)

    # 3. 领养申请表
    cursor.execute("DROP TABLE IF EXISTS applications")
    # ... (保持 applications 表结构不变)

    # 4. 公告表
    cursor.execute("DROP TABLE IF EXISTS announcements")
    cursor.execute('''
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_hot INTEGER DEFAULT 0
        )
    ''')

    # 5. 内容审核存证表 (新增)
    cursor.execute("DROP TABLE IF EXISTS moderation_logs")
    cursor.execute('''
        CREATE TABLE moderation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER, -- 被删除的宠物或帖子 ID
            admin_id INTEGER,
            reason TEXT NOT NULL, -- 删除理由
            evidence_url TEXT, -- 证据截图链接
            delete_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. 插入初始公告数据
    notices = [
        ('关于本周末在中心公园举办线下领养日的通知', '请参加活动的领养人携带好身份证件...', '2026-03-05', 1),
        ('新上线：AI 宠物行为翻译官功能说明', '通过上传视频，AI 可以分析宠物的肢体语言...', '2026-03-02', 0),
        ('救助站物资捐赠感谢名单公示（二月）', '感谢社会各界对流浪动物的支持...', '2026-02-28', 0)
    ]
    cursor.executemany("INSERT INTO announcements (title, content, date, is_hot) VALUES (?,?,?,?)", notices)

    # 4. 插入初始测试账号
    _h = _pwd_context.hash
    test_users = [
        ('用户A', 'user@test.com', _h('123'), 'individual', '程序员', '公寓', '猫', '13800000001'),
        ('阳光救助站', 'admin@test.com', _h('123'), 'org_admin', '站长', '救助中心', '狗', '13800000002'),
        ('系统管理员', 'root@test.com', _h('123'), 'root', 'IT', '总部', '所有', '13800000003')
    ]
    cursor.executemany("INSERT INTO users (username, email, password, role, occupation, living_env, preference, contact) VALUES (?,?,?,?,?,?,?,?)", test_users)

    # 5. 插入丰富的高清宠物测试数据 (支持瀑布流展示)
    pets_data = [
        (2, '布丁', '英国短毛猫', 2, '极少', '安静', '性格温和，喜欢陪伴工作中的主人。它有一双大大的金黄色眼睛，非常治愈。', 
         'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?q=80&w=1000&auto=format&fit=crop'),
        (2, '豆包', '比熊犬', 1, '不掉毛', '中等', '体型小，聪明，不掉毛，适合公寓居住。非常粘人，是绝佳的伴侣犬。', 
         'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?q=80&w=1000&auto=format&fit=crop'),
        (2, '辛巴', '金毛寻回犬', 3, '较多', '高', '典型的大暖男，对人非常友好，适合有院子的家庭。喜欢玩水和接球。', 
         'https://images.unsplash.com/photo-1552053831-71594a27632d?q=80&w=1000&auto=format&fit=crop'),
        (2, '年糕', '萨摩耶', 1, '非常多', '高', '微笑天使，虽然爱掉毛，但颜值极高，性格活泼。需要主人有足够的耐心打理毛发。', 
         'https://images.unsplash.com/photo-1529429617329-8a79e088c02c?q=80&w=1000&auto=format&fit=crop'),
        (2, '奥利奥', '边境牧羊犬', 2, '中等', '极高', '智商天花板，能够听懂许多复杂的指令。需要大量运动和智力挑战。', 
         'https://images.unsplash.com/photo-1503256207526-0df5d6342a00?q=80&w=1000&auto=format&fit=crop'),
        (2, '奶油', '布偶猫', 1, '中等', '安静', '颜值超高，像洋娃娃一样。性格极好，任抱任摸。', 
         'https://images.unsplash.com/photo-1533738363-b7f9aef128ce?q=80&w=1000&auto=format&fit=crop')
    ]
    cursor.executemany("INSERT INTO pets (owner_id, name, species, age, is_shedding, energy_level, description, image_url) VALUES (?,?,?,?,?,?,?,?)", pets_data)

    conn.commit()
    conn.close()
    print("数据库初始化成功！已增加图片 URL 以支持瀑布流。")

if __name__ == "__main__":
    init_database()
