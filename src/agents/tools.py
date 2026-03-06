import sqlite3
import requests
from crewai.tools import tool
try:
    from src.database.db_config import SQLITE_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH

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
    AMAP_KEY = "966b3f41682127d765517a06be14953a"  # 记得去高德控制台申请
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
# 3. 宠物健康知识库 RAG 工具 (Knowledge Tool)
# ==========================================
@tool("pet_health_knowledge_search")
def pet_health_knowledge_search(symptom_keyword: str):
    """
    在宠物健康百科中搜索相关症状的护理建议和病理说明。
    """
    # 这里在毕设中可以升级为 ChromaDB 向量检索
    # 目前我们先用一个简单的字典或 SQL 模拟 RAG 效果
    health_tips = {
        "呕吐": "可能原因：误食异物、寄生虫或肠胃炎。建议：禁食4-6小时，观察是否伴随腹泻。",
        "细小": "极其危险！高传染性。症状：精神萎靡、呕血、腥臭粪便。建议：立即隔离并送医。",
        "皮肤瘙痒": "可能原因：真菌感染（猫癣）、体外寄生虫。建议：保持环境干燥，配合药皂洗澡。"
    }
    
    # 模糊匹配
    for key in health_tips:
        if key in symptom_keyword:
            return health_tips[key]
    return "该症状在基础库中未记录，建议由医疗 Agent 进行深度逻辑分析。"

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