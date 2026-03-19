import os
import sqlite3
import requests
import chromadb
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()
try:
    from src.database.db_config import SQLITE_DB_PATH, CHROMA_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH, CHROMA_DB_PATH

# ==========================================
# 1. 领养申请提交工具 (Action Tool)
# ==========================================
@tool("submit_adoption_application")
def submit_adoption_application(pet_name: str, user_name: str, contact: str, reason: str):
    """
    当用户表达明确领养意向并提供联系方式时，调用此工具将申请记录存入数据库。
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        # 创建申请表（如果不存在）
        cursor.execute('''CREATE TABLE IF NOT EXISTS applications 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, pet_name TEXT, user_name TEXT, contact TEXT, reason TEXT, status TEXT)''')
        cursor.execute("INSERT INTO applications (pet_name, user_name, contact, reason, status) VALUES (?, ?, ?, ?, '待审核')",
                       (pet_name, user_name, contact, reason))
        conn.commit()
        conn.close()
        return f"✅ 申请已成功提交！领养中心将通过 {contact} 联系您。"
    except Exception as e:
        return f"❌ 申请提交失败: {str(e)}"

# ==========================================
# 2. 高德地图医院检索工具 (LBS Tool)
# ==========================================
@tool("nearby_hospital_search")
def nearby_hospital_search(location_coords: str):
    """
    根据经纬度坐标搜索附近5公里的宠物医院。
    参数 location_coords: 格式为 "经度,纬度" (例如: "116.4814,39.9904")
    """
    AMAP_KEY = os.getenv("AMAP_KEY", "")
    if not AMAP_KEY:
        return "地图服务未配置，请在 .env 中设置 AMAP_KEY"
    url = f"https://restapi.amap.com/v3/place/around"
    params = {
        "key": AMAP_KEY,
        "location": location_coords,
        "keywords": "宠物医院",
        "types": "090500", # 医疗保健-宠物医院
        "radius": "5000",
        "offset": "5", # 取前5条
        "page": "1",
        "extensions": "all"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data['status'] == '1' and int(data['count']) > 0:
            hospitals = []
            for poi in data['pois']:
                hospitals.append(f"🏥 {poi['name']} | 距离: {poi['distance']}米 | 地址: {poi['address']}")
            return "\n".join(hospitals)
        return "附近 5 公里内未发现宠物医院。"
    except Exception as e:
        return f"地图服务调用异常: {str(e)}"

# ==========================================
# 3. 宠物健康知识库 RAG 工具 (ChromaDB Vector Search)
# ==========================================
@tool("pet_health_knowledge_search")
def pet_health_knowledge_search(symptom_keyword: str):
    """
    在宠物健康知识库中进行语义向量检索，返回与症状最相关的护理建议和病理说明。
    参数 symptom_keyword: 症状描述，例如 "猫咪呕吐腹泻"、"犬细小病毒"
    """
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_or_create_collection(name="pet_knowledge")

        # 检查集合是否有数据
        count = collection.count()
        if count == 0:
            return _fallback_health_search(symptom_keyword)

        # 向量语义检索，取最相关的3条
        results = collection.query(
            query_texts=[symptom_keyword],
            n_results=min(3, count),
            include=["documents", "metadatas", "distances"]
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not docs:
            return _fallback_health_search(symptom_keyword)

        # 过滤相关度：distance < 1.5 视为有效匹配（ChromaDB 使用 L2 距离）
        relevant = [(doc, dist) for doc, dist in zip(docs, distances) if dist < 1.5]
        if not relevant:
            return _fallback_health_search(symptom_keyword)

        retrieved = "\n---\n".join([doc for doc, _ in relevant])
        return f"【知识库检索结果】\n{retrieved}"

    except Exception as e:
        return _fallback_health_search(symptom_keyword)


def _fallback_health_search(keyword: str) -> str:
    """ChromaDB 不可用时的兜底字典查找"""
    health_tips = {
        "呕吐": "可能原因：误食异物、寄生虫或肠胃炎。建议：禁食4-6小时，观察是否伴随腹泻。",
        "腹泻": "可能原因：饮食不当、肠道感染。建议：喂食易消化食物，补充电解质，持续超过24小时立即就医。",
        "细小": "极其危险！高传染性病毒病。症状：精神萎靡、呕血、腥臭粪便。建议：立即隔离并紧急送医。",
        "猫瘟": "传染性极强，症状：高热、呕吐、腹泻带血、精神萎靡。建议：立即隔离送医，接种猫三联疫苗可预防。",
        "皮肤瘙痒": "可能原因：真菌感染（猫癣）、体外寄生虫。建议：保持环境干燥，配合药皂洗澡，必要时就医。",
        "打喷嚏": "可能原因：猫鼻支/杯状病毒感染。建议：观察是否伴随流鼻涕、眼分泌物，症状持续需就医。",
        "不吃饭": "可能原因：应激、口腔疾病、全身性疾病。建议：超过24小时不进食需就医排查病因。",
        "抽搐": "紧急情况！可能原因：犬瘟热、低血糖、癫痫。建议：立即紧急送医，保持宠物安全不受伤。",
    }
    for key, tip in health_tips.items():
        if key in keyword:
            return f"【基础知识库】{tip}"
    return "该症状在知识库中未检索到匹配结果，建议由医疗 Agent 结合专业知识进行综合分析。"

@tool("pet_database_search")
def pet_database_search(requirement_keywords: str):
    """
    根据需求关键词在本地数据库中搜索待领养宠物。
    参数 requirement_keywords: 例如 '安静, 不掉毛'
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 将关键词拆分，进行简单的模糊查询
    keywords = [k.strip() for k in requirement_keywords.split(',')]
    query = "SELECT name, species, description FROM pets WHERE status = '待领养' AND ("
    conditions = []
    params = []
    for k in keywords:
        conditions.append("description LIKE ? OR energy_level LIKE ? OR is_shedding LIKE ?")
        params.extend([f'%{k}%', f'%{k}%', f'%{k}%'])
    
    query += " OR ".join(conditions) + ")"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "数据库中暂无完全符合条件的宠物，请尝试推荐类似的品种。"
    
    # 格式化结果给 Agent 看
    results = []
    for row in rows:
        results.append(f"名字: {row[0]}, 品种: {row[1]}, 详情: {row[2]}")
    return "\n".join(results)

@tool("calc_pet_daily_energy")
def calc_pet_daily_energy(species: str, age_months: int, weight_kg: float, neutered: bool, activity_level: str, goal: str):
    """
    计算宠物每日建议热量与喂食量，返回结构化摘要。
    """
    from .nutrition_planner import build_nutrition_plan
    plan = build_nutrition_plan(
        species=species,
        age_months=age_months,
        weight_kg=weight_kg,
        neutered=neutered,
        activity_level=activity_level,
        goal=goal,
        food_kcal_per_100g=360,
        symptoms=[]
    )
    return f"daily_kcal={plan['daily_kcal']}, daily_food_g={plan['daily_food_g']}, feedings_per_day={plan['feedings_per_day']}"


@tool("pet_food_forbidden_list")
def pet_food_forbidden_list(species: str):
    """
    获取不同宠物的常见喂养禁忌食物。
    """
    common = ['巧克力', '洋葱', '葡萄', '木糖醇', '酒精', '高盐高油剩饭']
    s = (species or '').lower()
    if s == 'cat':
        common += ['狗粮长期替代', '生鱼生肉长期单一喂食']
    if s == 'dog':
        common += ['熟骨头', '夏威夷果']
    return '\n'.join(common)
