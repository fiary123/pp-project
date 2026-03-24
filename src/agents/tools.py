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


# ==========================================
# 6. 互助任务检索工具
# ==========================================
@tool("search_mutual_aid_tasks")
def search_mutual_aid_tasks(task_type: str = "", location_keyword: str = "", pet_species: str = "") -> str:
    """
    检索当前开放中的互助任务列表。
    参数 task_type: 任务类型关键词，例如 "上门喂养"、"代遛狗"，为空则不过滤
    参数 location_keyword: 地点关键词，例如 "浦东"，为空则不过滤
    参数 pet_species: 宠物种类，例如 "猫"、"狗"，为空则不过滤
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mutual_aid_tasks'")
        if not cursor.fetchone():
            conn.close()
            return "互助任务表尚未初始化，暂无数据。"

        conditions = ["status = 'open'"]
        params = []
        if task_type:
            conditions.append("task_type LIKE ?")
            params.append(f"%{task_type}%")
        if location_keyword:
            conditions.append("location LIKE ?")
            params.append(f"%{location_keyword}%")
        if pet_species:
            conditions.append("pet_species LIKE ?")
            params.append(f"%{pet_species}%")

        query = f"SELECT id, task_type, pet_name, pet_species, start_time, end_time, location, description FROM mutual_aid_tasks WHERE {' AND '.join(conditions)} ORDER BY create_time DESC LIMIT 10"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "当前暂无符合条件的互助任务。"

        result = []
        for r in rows:
            result.append(
                f"任务ID:{r[0]} | 类型:{r[1]} | 宠物:{r[2]}({r[3]}) | "
                f"时间:{r[4]}~{r[5] or '待定'} | 地点:{r[6]}" +
                (f" | 说明:{r[7]}" if r[7] else "")
            )
        return "\n".join(result)
    except Exception as e:
        return f"检索互助任务失败: {str(e)}"


# ==========================================
# 7. 宠物偏好追问生成工具（智能匹配第一步）
# ==========================================
@tool("generate_followup_questions")
def generate_followup_questions(user_query: str) -> str:
    """
    分析用户的初始宠物需求描述，识别其中的信息缺口（活跃度/居住空间/陪伴时长/经验/过敏等），
    生成 2-3 个结构化追问，帮助用户将模糊偏好转化为可量化的匹配维度。
    参数 user_query: 用户的原始需求描述，例如"想养一只适合公寓的宠物"
    返回 JSON 数组字符串，每项含 key、question、options 三个字段。
    """
    # 基于关键词启发式生成追问，作为 LLM 的结构化输入补充
    questions = []
    q = user_query.lower()

    if not any(k in q for k in ['活跃', '安静', '好动', '懒']):
        questions.append({
            "key": "activity_level",
            "question": "您希望宠物平时是活泼好动还是安静陪伴型的？",
            "options": ["活泼爱玩", "温和安静", "都可以"]
        })
    if not any(k in q for k in ['公寓', '别墅', '院子', '平方', '㎡']):
        questions.append({
            "key": "living_space",
            "question": "您的居住空间大概是什么情况？",
            "options": ["小型公寓(60㎡以下)", "中等户型(60-120㎡)", "大户型/有院子"]
        })
    if not any(k in q for k in ['时间', '陪伴', '上班', '在家']):
        questions.append({
            "key": "time_availability",
            "question": "平时每天能陪伴宠物大概多长时间？",
            "options": ["2小时以内", "2-4小时", "4小时以上"]
        })
    if not any(k in q for k in ['经验', '养过', '第一次', '新手']):
        questions.append({
            "key": "experience_level",
            "question": "您之前有养宠物的经验吗？",
            "options": ["完全没有", "有一些经验", "资深宠主"]
        })

    import json as _json
    return _json.dumps(questions[:3], ensure_ascii=False)


# ==========================================
# 8. 宠物语义匹配评分工具（智能匹配第二步）
# ==========================================
@tool("score_pet_match")
def score_pet_match(user_profile_json: str, pet_list_json: str) -> str:
    """
    基于用户完整偏好画像（含追问答案），对宠物列表进行多维度结构化匹配评分。
    参数 user_profile_json: JSON 字符串，含 query、activity_level、living_space 等字段
    参数 pet_list_json: JSON 字符串，宠物列表（含 id、name、species、energy_level、is_shedding、description）
    返回评分结果 JSON 字符串，每项含 id、fit_score、matched_dims、mismatch_dims。
    """
    import json as _json
    try:
        profile = _json.loads(user_profile_json)
        pets    = _json.loads(pet_list_json)
    except Exception as e:
        return f"参数解析失败: {e}"

    activity_map = {"活泼爱玩": "高", "温和安静": "低", "都可以": None}
    space_map    = {"小型公寓(60㎡以下)": "low", "中等户型(60-120㎡)": "medium", "大户型/有院子": "high"}

    desired_activity = activity_map.get(profile.get("activity_level", ""), None)
    desired_space    = space_map.get(profile.get("living_space", ""), None)
    time_avail       = profile.get("time_availability", "")
    experience       = profile.get("experience_level", "")
    query            = profile.get("query", "")

    results = []
    for pet in pets[:20]:
        score = 60
        matched, mismatch = [], []

        pet_energy = (pet.get("energy_level") or "").lower()
        pet_shed   = (pet.get("is_shedding") or "").lower()
        pet_species = (pet.get("species") or "").lower()
        pet_desc   = (pet.get("description") or "").lower()

        # 活跃度匹配
        if desired_activity == "高" and pet_energy in ["高", "极高", "high"]:
            score += 15; matched.append("活跃度匹配")
        elif desired_activity == "低" and pet_energy in ["低", "安静", "low", "quiet"]:
            score += 15; matched.append("活跃度匹配")
        elif desired_activity and pet_energy:
            score -= 10; mismatch.append("活跃度不匹配")

        # 空间适配
        if desired_space == "low" and pet_energy in ["低", "安静", "medium"]:
            score += 10; matched.append("适合小空间")
        elif desired_space == "low" and pet_energy in ["高", "极高"]:
            score -= 15; mismatch.append("空间需求过大")

        # 经验匹配
        if experience == "完全没有" and any(k in pet_desc for k in ["温和", "乖巧", "友善", "新手"]):
            score += 10; matched.append("适合新手")
        elif experience == "完全没有" and any(k in (pet.get("species","")) for k in ["边境", "哈士奇", "柯基"]):
            score -= 10; mismatch.append("品种难度较高")

        # 时间匹配
        if "2小时以内" in time_avail and pet_energy in ["安静", "低"]:
            score += 5; matched.append("低陪伴需求")

        # 关键词命中
        for kw in query.split()[:5]:
            if len(kw) > 1 and (kw in pet_species or kw in pet_desc):
                score += 5; matched.append(f"关键词匹配:{kw}")

        results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "fit_score": min(98, max(30, score)),
            "matched_dims": matched[:3],
            "mismatch_dims": mismatch[:2]
        })

    results.sort(key=lambda x: x["fit_score"], reverse=True)
    return _json.dumps(results[:5], ensure_ascii=False)
