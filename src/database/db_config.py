import os

# 获取项目根目录 (D:\2026毕业设计\project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据库文件路径
SQLITE_DB_PATH = os.path.join(BASE_DIR, "src", "database", "data", "pet_adoption.db")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "src", "database", "data", "chroma_data")

# 打印调试信息（可选）
if __name__ == "__main__":
    print(f"Base Dir: {BASE_DIR}")
    print(f"SQLite Path: {SQLITE_DB_PATH}")
    print(f"Chroma Path: {CHROMA_DB_PATH}")
