import os
import sqlite3
import chromadb
import logging
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
try:
    from src.database.db_config import SQLITE_DB_PATH, CHROMA_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH, CHROMA_DB_PATH


def _infer_species_from_query(query: str) -> str:
    text = query or ""
    if any(token in text for token in ["狗", "小狗", "犬", "幼犬"]):
        return "dog"
    if any(token in text for token in ["猫", "小猫", "幼猫"]):
        return "cat"
    if any(token in text for token in ["龟", "陆龟", "水龟"]):
        return "reptile"
    if any(token in text for token in ["鱼", "金鱼", "热带鱼", "淡水", "水族"]):
        return "fish"
    if any(token in text for token in ["鸟", "鹦鹉", "玄凤", "文鸟"]):
        return "bird"
    if any(token in text for token in ["仓鼠", "兔", "龙猫", "刺猬", "荷兰猪"]):
        return "exotic"
    return ""


def _extract_health_terms(query: str) -> list[str]:
    text = query or ""
    alias_groups = {
        "不吃饭": ["不吃饭", "不爱吃饭", "不肯吃", "没胃口", "食欲差", "食欲下降", "食欲不振", "拒食", "食欲废绝"],
        "呕吐": ["呕吐", "吐", "反胃"],
        "腹泻": ["腹泻", "拉稀", "软便", "稀便"],
        "打喷嚏": ["打喷嚏", "喷嚏", "流鼻涕"],
        "抽搐": ["抽搐", "发抖", "癫痫", "口吐白沫"],
        "便秘": ["便秘", "拉不出", "蹲厕", "无便"],
        "皮肤瘙痒": ["皮肤瘙痒", "瘙痒", "抓挠", "脱毛", "猫癣"],
        "中暑": ["中暑", "热射病", "体温高", "喘", "流涎"],
        "外伤": ["骨折", "外伤", "出血", "受伤"],
        "泌尿": ["血尿", "尿频", "尿不出", "蹲猫砂盆"],
    }
    terms: list[str] = []
    for canonical, aliases in alias_groups.items():
        if any(alias in text for alias in aliases):
            terms.append(canonical)
    return terms


def _rank_knowledge_hits(query: str, docs: list, metadatas: list, distances: list) -> list[str]:
    species = _infer_species_from_query(query)
    terms = _extract_health_terms(query)
    ranked: list[tuple[float, str]] = []

    for doc, meta, dist in zip(docs, metadatas, distances):
        meta = meta or {}
        category = str(meta.get("category", ""))
        doc_species = str(meta.get("species", ""))
        condition = str(meta.get("condition", "")) + " " + str(meta.get("breed", ""))
        matched_term = False

        score = 0.0
        if category == "health_care":
            score += 4
        elif category == "feeding_guide":
            score += 2
        else:
            score -= 1

        if species:
            if doc_species == species:
                score += 4
            elif doc_species == "all":
                score += 2
            else:
                score -= 4

        for term in terms:
            if term in condition:
                score += 4
                matched_term = True
            if term in doc:
                score += 2
                matched_term = True

        if dist < 1.0:
            score += 3
        elif dist < 1.3:
            score += 2
        elif dist < 1.6:
            score += 1

        # 如果用户已经明确问了症状/问题词，但候选文档连核心词都没碰到，视为弱相关，直接淘汰
        if terms and not matched_term:
            continue

        # 只有在“物种一致 + 主题一致 + 相似度够强”时，才允许把知识库内容直接展示给用户
        if score >= 7:
            ranked.append((score, doc))

    ranked.sort(key=lambda item: item[0], reverse=True)
    unique_docs: list[str] = []
    for _, doc in ranked:
        if doc not in unique_docs:
            unique_docs.append(doc)
        if len(unique_docs) >= 3:
            break
    return unique_docs


def search_pet_knowledge_hits(query: str, limit: int = 3) -> list[dict]:
    """统一的知识库检索入口：只返回直接匹配的问题结果。"""
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = chroma_client.get_or_create_collection(name="pet_knowledge")
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(10, count),
        include=["documents", "metadatas", "distances"]
    )
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    if not docs:
        return []

    species = _infer_species_from_query(query)
    terms = _extract_health_terms(query)
    ranked_docs = _rank_knowledge_hits(query, docs, metadatas, distances)
    hits: list[dict] = []
    for ranked_doc in ranked_docs:
        for doc, meta, dist in zip(docs, metadatas, distances):
            if doc != ranked_doc:
                continue
            meta = meta or {}
            doc_species = str(meta.get("species", ""))
            if species and doc_species not in {species, "all"}:
                continue
            if terms:
                condition = str(meta.get("condition", "")) + " " + str(meta.get("breed", ""))
                if not any(term in condition or term in doc for term in terms):
                    continue
            hits.append({
                "text": doc,
                "meta": meta,
                "distance": dist,
                "similarity": round(max(0.0, 1 - dist), 3),
            })
            break
        if len(hits) >= limit:
            break
    return hits

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
# 2. 宠物健康知识库 RAG 工具 (ChromaDB Vector Search)
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
            return _fallback_health_search(symptom_keyword, "知识库尚未初始化或为空")

        relevant_hits = search_pet_knowledge_hits(symptom_keyword, limit=3)
        if not relevant_hits:
            return _fallback_health_search(symptom_keyword, "知识库没有足够相关的检索结果，或返回结果与提问物种/症状不一致")

        retrieved = "\n---\n".join(hit["text"] for hit in relevant_hits)
        return f"【知识库检索结果】\n{retrieved}"

    except Exception as e:
        logger.warning(f"pet_health_knowledge_search failed: {e}")
        return _fallback_health_search(symptom_keyword, f"知识库检索异常：{e}")


def _llm_health_fallback(keyword: str, hint: str = "") -> str:
    """知识库未命中时，使用 LLM 生成通用知识兜底回答。"""
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=api_key,
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3,
        )
        messages = [
            SystemMessage(content="你是宠物养护平台的知识兜底助手。当知识库未命中时，请基于通用宠物知识给出谨慎、简洁、可执行的建议，不要伪造知识库来源。"),
            HumanMessage(
                content=(
                    f"用户问题：{keyword}\n"
                    f"检索情况：{hint or '知识库未命中或暂时不可用。'}\n"
                    "请直接输出回答，并遵守：\n"
                    "1. 开头明确写“以下为 AI 通用知识补充，非知识库命中结果”。\n"
                    "2. 优先给出基础护理、观察要点和风险提示。\n"
                    "3. 涉及疾病、用药、持续异常、幼宠或急症时，提醒尽快咨询兽医。\n"
                    "4. 不要输出 JSON。"
                )
            ),
        ]
        response = llm.invoke(messages)
        return str(response.content).strip()
    except Exception as e:
        logger.warning(f"llm health fallback failed: {e}")
        return ""


def _fallback_health_search(keyword: str, reason: str = "") -> str:
    """ChromaDB 未命中或不可用时的兜底：优先 LLM 通用知识补充。"""
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
    llm_answer = _llm_health_fallback(keyword, reason or "知识库未检索到直接匹配结果")
    if llm_answer:
        return llm_answer

    for key, tip in health_tips.items():
        if key in keyword:
            return f"以下为 AI 通用知识补充，非知识库命中结果。\n{tip}\n如持续超过24小时、伴随呕吐腹泻、精神萎靡或年龄过小，请尽快咨询兽医。"
    return "以下为 AI 通用知识补充，非知识库命中结果。当前库中没有检索到直接匹配内容；如果涉及疾病、用药或持续异常，建议尽快咨询专业兽医。"

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
    import json as _json

    raw_query = user_query or ""
    q = raw_query.lower()

    def contains_any(text: str, keywords: list[str]) -> bool:
        return any(k in text for k in keywords)

    species = "unknown"
    if contains_any(raw_query, ["猫", "猫咪", "狸花", "英短", "布偶", "橘猫"]):
        species = "cat"
    elif contains_any(raw_query, ["狗", "狗狗", "小狗", "柯基", "金毛", "比熊", "柴犬"]):
        species = "dog"
    elif contains_any(raw_query, ["兔", "仓鼠", "龙猫", "鹦鹉", "异宠"]):
        species = "other"

    has_age = contains_any(raw_query, ["幼", "成", "老年", "几个月", "岁", "月", "奶猫", "幼犬"])
    has_breed = contains_any(raw_query, [
        "狸花", "英短", "美短", "布偶", "金渐层", "橘猫", "奶牛猫",
        "柯基", "金毛", "边牧", "柴犬", "比熊", "拉布拉多", "哈士奇"
    ])
    has_temperament = contains_any(raw_query, [
        "粘人", "亲人", "安静", "活泼", "高冷", "聪明", "温顺", "不粘人", "独立"
    ])
    has_space = contains_any(raw_query, ["公寓", "别墅", "院子", "平方", "㎡", "出租屋"])
    has_time = contains_any(raw_query, ["时间", "陪伴", "上班", "在家", "出差", "加班"])
    has_experience = contains_any(raw_query, ["经验", "养过", "第一次", "新手", "老手"])
    has_size = contains_any(raw_query, ["小型", "中型", "大型", "体型"])
    has_hair = contains_any(raw_query, ["掉毛", "长毛", "短毛", "毛少", "毛多"])

    questions = []

    if species == "unknown":
        questions.append({
            "key": "species_preference",
            "question": "您现在更偏向哪一类宠物？我可以按这个方向继续细化推荐。",
            "options": ["猫咪优先", "狗狗优先", "其他宠物也可以"]
        })

    if species == "cat":
        if not has_age:
            questions.append({
                "key": "cat_age_preference",
                "question": "您更想要什么年龄段的猫咪？粘人感和适应速度通常会和年龄有关。",
                "options": ["幼猫更好", "成猫更合适", "年龄不是重点"]
            })
        if not has_breed:
            questions.append({
                "key": "cat_breed_preference",
                "question": "您对猫咪品种有偏好吗？还是更看重性格合适就行？",
                "options": ["指定品种", "田园猫也可以", "只看性格合适"]
            })
        if not has_hair:
            questions.append({
                "key": "cat_hair_preference",
                "question": "在毛发和打理上，您更偏向哪种类型的猫咪？",
                "options": ["短毛省心", "长毛颜值高", "都可以接受"]
            })

    if species == "dog":
        if not has_size:
            questions.append({
                "key": "dog_size_preference",
                "question": "您更想养什么体型的狗狗？这会直接影响空间和运动需求。",
                "options": ["小型犬", "中型犬", "大型犬也可以"]
            })
        if not has_age:
            questions.append({
                "key": "dog_age_preference",
                "question": "您更倾向幼犬、成犬，还是只要脾气合适都可以？",
                "options": ["幼犬", "成犬", "年龄不是重点"]
            })
        if not has_breed:
            questions.append({
                "key": "dog_breed_preference",
                "question": "您是有明确想要的品种，还是先从性格和生活习惯来匹配？",
                "options": ["已有想要的品种", "先看性格匹配", "都可以"]
            })

    if species == "other" and not has_experience:
        questions.append({
            "key": "experience_level",
            "question": "异宠的饲养差异比较大，想先确认一下，您之前有相关经验吗？",
            "options": ["完全没有", "有一点经验", "养过类似宠物"]
        })

    if has_temperament and not has_age:
        questions.append({
            "key": "temperament_age_balance",
            "question": "您刚才提到了性格偏好，那您更在意性格稳定，还是愿意慢慢陪它建立亲密感？",
            "options": ["更看重现成的稳定性格", "可以慢慢培养感情", "都可以"]
        })

    if not has_space:
        questions.append({
            "key": "living_space",
            "question": "您平时的居住空间大概是什么情况？我会避开明显不适合的类型。",
            "options": ["小型公寓(60㎡以下)", "中等户型(60-120㎡)", "大户型/有院子"]
        })
    if not has_time:
        questions.append({
            "key": "time_availability",
            "question": "平时每天大概能陪伴宠物多久？这会影响我对陪伴型宠物的推荐。",
            "options": ["2小时以内", "2-4小时", "4小时以上"]
        })
    if not has_experience:
        questions.append({
            "key": "experience_level",
            "question": "最后再确认一下，您是第一次养宠，还是已经有一些经验了？",
            "options": ["完全没有", "有一些经验", "资深宠主"]
        })

    if not questions:
        questions = [
            {
                "key": "primary_priority",
                "question": "如果只能优先满足一个条件，您最看重的是性格、品种，还是饲养难度？",
                "options": ["性格最重要", "品种最重要", "省心好养最重要"]
            },
            {
                "key": "living_space",
                "question": "您的居住空间大概是什么情况？我会据此避开不适合的小伙伴。",
                "options": ["小型公寓(60㎡以下)", "中等户型(60-120㎡)", "大户型/有院子"]
            },
            {
                "key": "time_availability",
                "question": "平时每天大概能陪伴宠物多久？",
                "options": ["2小时以内", "2-4小时", "4小时以上"]
            }
        ]

    deduped = []
    seen_keys = set()
    for item in questions:
        if item["key"] in seen_keys:
            continue
        seen_keys.add(item["key"])
        deduped.append(item)

    return _json.dumps(deduped[:3], ensure_ascii=False)


# ==========================================
# 8. 宠物语义匹配评分工具（智能匹配第二步）
# ==========================================
@tool("score_pet_match")
def score_pet_match(user_profile_json: str, pet_list_json: str) -> str:
    """
    基于用户完整偏好画像（含追问答案），对宠物列表进行多维度结构化匹配评分。
    参数 user_profile_json: JSON 字符串，必须包含 query 字段
    参数 pet_list_json: JSON 字符串，宠物列表数据
    返回评分结果 JSON 字符串。
    """
    import json as _json
    try:
        if not user_profile_json or not pet_list_json or "Missing" in user_profile_json:
            return "ERROR: 缺少必要匹配数据。请确保已通过分析工具获取用户档案和宠物列表。"
            
        profile = _json.loads(user_profile_json)
        pets    = _json.loads(pet_list_json)
        
        if not isinstance(pets, list) or len(pets) == 0:
            return "ERROR: 宠物列表为空，无法进行评分。"
    except Exception as e:
        return f"ERROR: 参数解析失败: {str(e)}"

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
        pet_species = (pet.get("species") or "").lower()
        pet_desc   = (pet.get("description") or "").lower()

        # 1. 活跃度匹配
        if desired_activity == "高" and any(k in pet_energy for k in ["高", "极高", "high"]):
            score += 15; matched.append("活跃度契合")
        elif desired_activity == "低" and any(k in pet_energy for k in ["低", "安静", "low", "quiet"]):
            score += 15; matched.append("性格文静")

        # 2. 空间适配
        if desired_space == "low" and any(k in pet_energy for k in ["高", "极高"]):
            score -= 15; mismatch.append("活动空间需求大")

        # 3. 关键词命中
        if query:
            for kw in query.replace(","," ").split():
                if len(kw) > 1 and (kw in pet_species or kw in pet_desc):
                    score += 10; matched.append(f"命中偏好:{kw}")

        results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "fit_score": min(98, max(20, score)),
            "matched_dims": matched[:3],
            "mismatch_dims": mismatch[:2]
        })

    results.sort(key=lambda x: x["fit_score"], reverse=True)
    return _json.dumps(results[:5], ensure_ascii=False)

# ==========================================
# 9. 领养经验召回工具 (Feedback Memory Layer)
# ==========================================
@tool("recall_adoption_experience")
def recall_adoption_experience(applicant_profile_tags: str):
    """
    根据申请人的特征标签（如：租房, 新手, 边牧, 预算低），从历史领养回访经验库中检索相似案例。
    返回历史案例的真实满意度、遇到的挑战和建议，帮助本次审核进行“先例参考”。
    参数 applicant_profile_tags: 描述申请人特征的关键词字符串。
    """
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_or_create_collection(name="adoption_experience")

        if collection.count() == 0:
            return "【经验库】目前尚无历史案例积累，请基于通用准则评估。"

        results = collection.query(
            query_texts=[applicant_profile_tags],
            n_results=2,
            include=["documents", "metadatas"]
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return "【经验库】未找到高度相似的历史案例。"

        experience_reports = []
        for doc, meta in zip(docs, metas):
            report = (
                f"- 相似历史案例：{doc}\n"
                f"  * 满意度：{meta.get('satisfaction', '?')}/5\n"
                f"  * 挑战：{meta.get('challenges', '无')}\n"
                f"  * 建议：{meta.get('recommendation', '继续观察')}"
            )
            experience_reports.append(report)

        return "【历史先例参考】\n" + "\n---\n".join(experience_reports)

    except Exception as e:
        return f"经验库调用异常: {str(e)}"
