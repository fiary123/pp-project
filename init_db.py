# 初始化向量数据库脚本
import chromadb

def setup_database():
    print("正在初始化 ChromaDB 向量知识库...")
    # 在当前目录生成持久化数据库文件
    client = chromadb.PersistentClient(path="./chroma_data")
    
    # 创建宠物档案集合
    collection = client.get_or_create_collection(name="pet_profiles")
    
    # 录入测试宠物数据
    documents = [
        "名字：花卷。品种：英短蓝猫。特征：性格温顺黏人，极其安静不爱叫，掉毛少。非常适合居住在小户型公寓的年轻人或程序员，不需要太多室外运动。",
        "名字：大黄。品种：金毛巡回犬。特征：极其活泼，阳光亲人，精力旺盛。需要每天至少两小时的户外运动，适合家里有大院子、有时间陪伴的家庭。",
        "名字：奥利奥。品种：边境牧羊犬。特征：智商极高，会察言观色，但比较敏感。适合有一定养宠经验的主人，需要较大的活动空间。"
    ]
    metadatas = [
        {"id": 1, "name": "花卷", "breed": "猫"}, 
        {"id": 2, "name": "大黄", "breed": "狗"}, 
        {"id": 3, "name": "奥利奥", "breed": "狗"}
    ]
    ids = ["pet_1", "pet_2", "pet_3"]
    
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print("✅ 宠物数据向量化完成！")

if __name__ == "__main__":
    setup_database()