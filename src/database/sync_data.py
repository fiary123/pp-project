import sqlite3
import chromadb
import os
import re
from .db_config import SQLITE_DB_PATH, CHROMA_DB_PATH, BASE_DIR

def sync_all_data():
    # 1. 同步 SQLite 宠物数据到 ChromaDB
    sync_sqlite_to_chroma()
    
    # 2. 同步知识库 TXT 文件到 ChromaDB
    sync_knowledge_to_chroma()

def sync_sqlite_to_chroma():
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ 错误：找不到 {SQLITE_DB_PATH}，请先运行 init_db.py")
        return

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, species, description FROM pets")
    pets = cursor.fetchall()
    
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = chroma_client.get_or_create_collection(name="pet_profiles")

    for pet in pets:
        pet_id, name, species, description = pet
        combined_text = f"名称：{name}，品种：{species}。描述：{description}"
        collection.upsert(
            ids=[f"pet_{pet_id}"],
            documents=[combined_text],
            metadatas=[{"source": "sqlite_db", "name": name}]
        )
        print(f"✅ 已同步宠物数据：{name}")
    conn.close()

def sync_knowledge_to_chroma():
    knowledge_dir = os.path.join(BASE_DIR, "src", "database", "data", "knowledge")
    if not os.path.exists(knowledge_dir):
        print(f"⚠️ 知识库目录不存在: {knowledge_dir}")
        return

    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = chroma_client.get_or_create_collection(name="pet_knowledge")

    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(knowledge_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 按照段落或长度拆分内容 (简单的 RAG 策略)
                chunks = re.split(r'\n\s*\n', content) # 按空行拆分
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) < 10: continue # 跳过太短的
                    
                    doc_id = f"kb_{filename}_{i}"
                    collection.upsert(
                        ids=[doc_id],
                        documents=[chunk.strip()],
                        metadatas=[{"source": filename, "chunk": i}]
                    )
                print(f"📚 已索引知识库文件: {filename} ({len(chunks)} 个数据块)")

if __name__ == "__main__":
    sync_all_data()
    print("\n🚀 所有数据已成功同步至向量库！")
