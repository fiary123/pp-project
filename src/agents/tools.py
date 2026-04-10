import os
import sqlite3
import chromadb
import logging
import json
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
    if any(token in text for token in ["猫", "猫咪", "狸花", "英短", "布偶", "橘猫"]):
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

        if terms and not matched_term:
            continue

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
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = chroma_client.get_or_create_collection(name="pet_knowledge")
    count = collection.count()
    if count == 0: return []

    results = collection.query(
        query_texts=[query],
        n_results=min(10, count),
        include=["documents", "metadatas", "distances"]
    )
    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    if not docs: return []

    species = _infer_species_from_query(query)
    terms = _extract_health_terms(query)
    ranked_docs = _rank_knowledge_hits(query, docs, metadatas, distances)
    hits: list[dict] = []
    for ranked_doc in ranked_docs:
        for doc, meta, dist in zip(docs, metadatas, distances):
            if doc != ranked_doc: continue
            meta = meta or {}
            doc_species = str(meta.get("species", ""))
            if species and doc_species not in {species, "all"}: continue
            if terms:
                condition = str(meta.get("condition", "")) + " " + str(meta.get("breed", ""))
                if not any(term in condition or term in doc for term in terms): continue
            hits.append({"text": doc, "meta": meta, "distance": dist, "similarity": round(max(0.0, 1 - dist), 3)})
            break
        if len(hits) >= limit: break
    return hits

@tool("submit_adoption_application")
def submit_adoption_application(pet_name: str, user_name: str, contact: str, reason: str):
    """
    提交宠物领养申请。
    参数:
        pet_name: 宠物名称
        user_name: 领养人姓名
        contact: 联系方式（电话或微信）
        reason: 领养理由
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, pet_name TEXT, user_name TEXT, contact TEXT, reason TEXT, status TEXT)''')
        cursor.execute("INSERT INTO applications (pet_name, user_name, contact, reason, status) VALUES (?, ?, ?, ?, '待审核')", (pet_name, user_name, contact, reason))
        conn.commit()
        conn.close()
        return f"✅ 申请已成功提交！领养中心将通过 {contact} 联系您。"
    except Exception as e:
        return f"❌ 申请提交失败: {str(e)}"

@tool("pet_health_knowledge_search")
def pet_health_knowledge_search(symptom_keyword: str):
    """
    在宠物健康知识库中搜索相关症状和护理建议。
    参数:
        symptom_keyword: 症状关键词（如：呕吐、腹泻）
    """
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_or_create_collection(name="pet_knowledge")
        if collection.count() == 0: return _fallback_health_search(symptom_keyword, "知识库为空")
        relevant_hits = search_pet_knowledge_hits(symptom_keyword, limit=3)
        if not relevant_hits: return _fallback_health_search(symptom_keyword, "无匹配结果")
        retrieved = "\n---\n".join(hit["text"] for hit in relevant_hits)
        return f"【知识库检索结果】\n{retrieved}"
    except Exception as e:
        return _fallback_health_search(symptom_keyword, str(e))

def _fallback_health_search(keyword: str, reason: str = "") -> str:
    health_tips = {"呕吐": "禁食4-6小时", "腹泻": "补充电解质", "细小": "立即送医", "猫瘟": "立即送医"}
    for key, tip in health_tips.items():
        if key in keyword: return f"AI 建议：{tip} (非库命中)"
    return "请咨询专业兽医。"

@tool("pet_database_search")
def pet_database_search(requirement_keywords: str):
    """
    根据需求关键词搜索待领养宠物数据库。
    参数:
        requirement_keywords: 逗号分隔的关键词（如：温顺, 小型犬, 橘猫）
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    keywords = [k.strip() for k in requirement_keywords.split(',')]
    query = "SELECT name, species, description, energy_level FROM pets WHERE status = '待领养' AND ("
    conditions = []
    params = []
    for k in keywords:
        conditions.append("description LIKE ? OR species LIKE ? OR energy_level LIKE ?")
        params.extend([f'%{k}%', f'%{k}%', f'%{k}%'])
    query += " OR ".join(conditions) + ")"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    if not rows: return "暂无直接符合条件的宠物。"
    results = []
    for r in rows:
        results.append({"id": 0, "name": r[0], "species": r[1], "description": r[2], "energy_level": r[3]})
    return json.dumps(results, ensure_ascii=False)

@tool("calc_pet_daily_energy")
def calc_pet_daily_energy(species: str, age_months: int, weight_kg: float, neutered: bool, activity_level: str, goal: str):
    """
    计算宠物的每日所需热量和建议喂食量。
    参数:
        species: 物种（猫/狗）
        age_months: 月龄
        weight_kg: 体重(kg)
        neutered: 是否绝育
        activity_level: 活跃程度
        goal: 增重/减重/保持
    """
    from .nutrition_planner import build_nutrition_plan
    plan = build_nutrition_plan(species=species, age_months=age_months, weight_kg=weight_kg, neutered=neutered, activity_level=activity_level, goal=goal, food_kcal_per_100g=360, symptoms=[])
    return f"daily_kcal={plan['daily_kcal']}, daily_food_g={plan['daily_food_g']}, feedings_per_day={plan['feedings_per_day']}"

@tool("pet_food_forbidden_list")
def pet_food_forbidden_list(species: str):
    """
    查询该物种绝对不能吃的食物清单。
    参数:
        species: 宠物物种
    """
    return "巧克力, 洋葱, 葡萄, 木糖醇"

@tool("search_mutual_aid_tasks")
def search_mutual_aid_tasks(task_type: str = "", location_keyword: str = "", pet_species: str = "") -> str:
    """
    搜索宠物互助任务（如遛狗、寄养、寻找走失宠物）。
    参数:
        task_type: 任务类型
        location_keyword: 地点关键词
        pet_species: 宠物物种
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        conditions = ["status = 'open'"]
        params = []
        if task_type: conditions.append("task_type LIKE ?"); params.append(f"%{task_type}%")
        query = f"SELECT id, task_type, pet_name FROM mutual_aid_tasks WHERE {' AND '.join(conditions)}"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return "\n".join([f"ID:{r[0]} | 类型:{r[1]}" for r in rows]) if rows else "暂无任务"
    except Exception as e: return str(e)

@tool("generate_followup_questions")
def generate_followup_questions(user_query: str) -> str:
    """
    为领养评估生成针对性的追问问题。
    参数:
        user_query: 用户的领养倾向或咨询内容
    """
    # 模拟追问逻辑
    questions = [{"key": "living_space", "question": "您的居住空间？", "options": ["公寓", "别墅"]}]
    return json.dumps(questions, ensure_ascii=False)

# 阶梯权重算法实现
@tool("score_pet_match")
def score_pet_match(user_profile_json: str, pet_list_json: str) -> str:
    """
    基于用户偏好画像，采用阶梯权重算法评分：
    1. 品种命中 (Hard Match): +35分
    2. 性格标签命中 (Soft Match): 每个关键词 +15分
    3. 降级补偿: 若品种不匹配但性格契合度高，补偿 +10分
    """
    try:
        profile = json.loads(user_profile_json)
        pets = json.loads(pet_list_json)
        if not pets: return "[]"
    except: return "ERROR"

    query = profile.get("query", "").replace("，", " ").replace(",", " ")
    keywords = [k.strip() for k in query.split() if len(k.strip()) > 1]
    
    # 品种库（可扩充）
    breed_bank = ["狸花", "英短", "美短", "布偶", "金毛", "柯基", "柴犬", "田园", "三花", "橘猫"]
    desired_breeds = [k for k in keywords if any(b in k for b in breed_bank)]
    desired_traits = [k for k in keywords if k not in desired_breeds]

    results = []
    for pet in pets:
        score = 50
        breed_hit = False
        trait_hits = 0
        pet_species = str(pet.get("species", ""))
        pet_desc = str(pet.get("description", ""))
        
        for b in desired_breeds:
            if b in pet_species or b in pet_desc:
                score += 35; breed_hit = True; break
        
        for t in desired_traits:
            if t in pet_desc or t in pet_species:
                score += 15; trait_hits += 1
        
        # 阶梯降级逻辑：品种没中，但性格命中了 2 个及以上，视为优质候选
        if not breed_hit and trait_hits >= 2:
            score += 10
            
        results.append({
            "id": pet.get("id"),
            "name": pet.get("name"),
            "fit_score": min(99, score),
            "is_degraded": not breed_hit,
            "breed_match": breed_hit,
            "trait_count": trait_hits
        })

    results.sort(key=lambda x: x["fit_score"], reverse=True)
    return json.dumps(results[:6], ensure_ascii=False)

@tool("recall_adoption_experience")
def recall_adoption_experience(applicant_profile_tags: str):
    """
    回顾以往的领养案例以获取参考。
    参数:
        applicant_profile_tags: 申请人的画像标签
    """
    return "暂无相似历史先例参考。"
