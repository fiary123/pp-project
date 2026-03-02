import sqlite3
import chromadb
import os
from .db_config import SQLITE_DB_PATH, CHROMA_DB_PATH

def sync_sqlite_to_chroma():
    # 1. 连接 SQLite
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ 错误：找不到 {SQLITE_DB_PATH}，请先运行 init_db.py")
        return

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, species, description FROM pets")
    pets = cursor.fetchall()
    
    # 2. 连接 ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    # 使用默认的 embedding 函数
    collection = chroma_client.get_or_create_collection(name="pet_profiles")

    # 3. 同步数据
    for pet in pets:
        pet_id, name, species, description = pet
        combined_text = f"名称：{name}，品种：{species}。描述：{description}"
        
        # 存入向量库
        collection.upsert(
            ids=[str(pet_id)],
            documents=[combined_text],
            metadatas=[{"name": name, "species": species}]
        )
        print(f"✅ 已同步宠物：{name}")

    conn.close()
    print("\n🚀 所有宠物数据已成功同步至向量库！")

if __name__ == "__main__":
    sync_sqlite_to_chroma()
