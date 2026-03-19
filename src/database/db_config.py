import os

# 获取项目根目录 (D:\2026毕业设计\project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据库选型说明：
# 本系统使用 SQLite 作为持久化存储，原因如下：
# 1. 原型/教学场景：单节点部署，无高并发需求，SQLite 零配置、易于演示
# 2. 架构可扩展性：数据库访问已通过 db_service 层完全隔离，
#    如需升级至 PostgreSQL，仅需修改此配置文件和连接函数，业务层无需改动

# 数据库文件路径
SQLITE_DB_PATH = os.path.join(BASE_DIR, "src", "database", "data", "pet_adoption.db")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "src", "database", "data", "chroma_data")

# 打印调试信息（可选）
if __name__ == "__main__":
    print(f"Base Dir: {BASE_DIR}")
    print(f"SQLite Path: {SQLITE_DB_PATH}")
    print(f"Chroma Path: {CHROMA_DB_PATH}")
