import os
import sys
import time
import uuid
import json
import logging
from typing import List, Optional, Tuple
from src.agents.nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from src.web.services.db_service import get_db
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIService:
    """统一的 AI 服务接口"""
    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3
        )

    async def ask(self, prompt: str) -> str:
        """简单的问答接口"""
        try:
            res = await self.llm.ainvoke(prompt)
            return res.content
        except Exception as e:
            logger.error(f"AIService error: {e}")
            return "AI 服务暂时无法响应"

# 全局单例
ai_service = AIService()

def _log_agent_trace(trace_id: str, endpoint: str, agent_name: str, input_msg: str, output_msg: str, latency_ms: int, fallback: bool = False, tool_name: str = "default"):
    """记录 AI 执行日志"""
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO agent_trace_logs
                   (trace_id, endpoint, agent_name, tool_name, latency_ms, fallback_used, input_msg, output_msg)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (trace_id, endpoint, agent_name, tool_name, latency_ms, 1 if fallback else 0, input_msg, output_msg)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log agent trace: {e}")

def get_agent_reply(user_msg: str) -> Tuple[str, str]:
    """调用知识专家 Agent 获得回复，返回 (reply, trace_id)"""
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    fallback = False
    agent_name = "KnowledgeExpert"
    
    try:
        from src.agents.agents import run_knowledge_expert
        reply = run_knowledge_expert(user_msg)
    except Exception as e:
        logger.warning(f"AI Service Error (fallback activated): {e}")
        reply = f"抱歉，我现在有点累了（{user_msg}），正在努力充电中... 请稍后再试。"
        fallback = True
    
    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "chat", agent_name, user_msg, reply, latency, fallback)
    return reply, trace_id

def get_triage_reply(symptom: str) -> Tuple[str, str]:
    """调用分诊专家 Agent，返回 (reply, trace_id)"""
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    fallback = False
    agent_name = "TriageExpert"
    
    try:
        from src.agents.agents import run_triage_expert
        reply = run_triage_expert(symptom)
    except Exception as e:
        logger.warning(f"Triage Service Error (fallback activated): {e}")
        reply = f"医生智能系统正在诊断中，针对您的症状：{symptom}，我们建议您观察 2-4 小时。"
        fallback = True
    
    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "triage", agent_name, symptom, reply, latency, fallback)
    return reply, trace_id

def get_match_followup_questions(user_query: str) -> List[dict]:
    """
    创新点1：基于用户的初始描述，由 LLM 生成 2-3 个针对性追问。
    用于将模糊的情感表达转化为结构化偏好维度（活跃度/空间/时间/经验等）。
    返回追问列表：[{"key": "activity_level", "question": "...", "options": [...]}]
    """
    try:
        import os
        from langchain_openai import ChatOpenAI
        from dotenv import load_dotenv
        load_dotenv()
        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            temperature=0.4
        )
        prompt = f"""用户正在寻找宠物，他们说："{user_query}"

基于这段描述，你需要提出 2-3 个追问，帮助更准确地了解他们的需求。
每个追问都应该针对他们描述中的模糊点或隐性偏好。

请用 JSON 数组格式输出，每个元素包含：
- key: 偏好维度标识符（如 activity_level / living_space / time_availability / experience_level / allergic）
- question: 中文追问问题（15-25字，口语化，友好）
- options: 2-4个选项的字符串数组（简洁，5字以内）

示例输出：
[
  {{"key": "activity_level", "question": "您希望这只宠物平时是活泼好动还是安静陪伴型的？", "options": ["活泼爱玩", "温和安静", "都可以"]}},
  {{"key": "living_space", "question": "您住的地方大概有多大，方便宠物活动吗？", "options": ["小公寓(60㎡以下)", "中等户型(60-120㎡)", "大户型/别墅"]}}
]

只输出 JSON 数组，不要其他文字。"""
        response = llm.invoke(prompt)
        content = response.content.strip()
        # 提取 JSON
        import re
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            questions = json.loads(json_match.group())
            return questions[:3]
    except Exception as e:
        logger.warning(f"Followup question generation failed: {e}")
    # 降级：返回默认追问
    return [
        {"key": "activity_level", "question": "您更希望宠物是活泼好动还是安静乖巧的？", "options": ["活泼好动", "安静乖巧", "都可以"]},
        {"key": "living_space", "question": "您的居住空间大概是什么情况？", "options": ["小型公寓", "中等户型", "带院子的大户型"]},
        {"key": "time_availability", "question": "平时每天能陪伴宠物大概多长时间？", "options": ["2小时以内", "2-4小时", "4小时以上"]}
    ]


def get_smart_match(user_query: str, pet_list: List[dict], followup_answers: Optional[dict] = None) -> List[dict]:
    """
    创新点1+3：LLM 语义匹配 + 结构化可解释推荐。
    当 followup_answers 不为空时，将追问答案合并到偏好上下文，由 LLM 生成
    结构化匹配理由（适配优势 / 潜在挑战 / 弥合建议），替代原关键词匹配。
    """
    # 构建完整的偏好描述
    context_parts = [f"用户需求：{user_query}"]
    if followup_answers:
        for key, answer in followup_answers.items():
            key_labels = {
                "activity_level": "活跃度偏好",
                "living_space": "居住空间",
                "time_availability": "可陪伴时长",
                "experience_level": "养宠经验",
                "allergic": "过敏情况"
            }
            label = key_labels.get(key, key)
            context_parts.append(f"{label}：{answer}")
    full_context = "；".join(context_parts)

    # 尝试 LLM 语义匹配
    try:
        import os
        from langchain_openai import ChatOpenAI
        from dotenv import load_dotenv
        load_dotenv()
        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3
        )
        # 构建宠物摘要列表（避免 token 过多）
        pet_summaries = []
        for p in pet_list[:30]:  # 限制数量
            tags = p.get('tags', [])
            tags_str = "、".join(tags) if isinstance(tags, list) else str(tags)
            pet_summaries.append({
                "id": p.get("id"),
                "name": p.get("name", ""),
                "species": p.get("species", ""),
                "type": p.get("type", ""),
                "tags": tags_str,
                "desc": (p.get("desc") or "")[:50]
            })

        prompt = f"""你是一个宠物匹配专家。用户画像：{full_context}

以下是可选宠物列表（JSON）：
{json.dumps(pet_summaries, ensure_ascii=False)}

请从中挑选最合适的 5 只，为每只生成结构化的个性化推荐理由。

输出 JSON 数组，每个元素：
- id: 宠物ID（整数）
- fit_score: 契合度分数（0-100整数）
- reason: 一句话推荐理由（20字内，口语化）
- fit_advantages: 适配优势（数组，每项10-15字，列2-3条）
- potential_challenges: 潜在挑战（数组，每项10-15字，列1-2条，没有则为空数组）
- mitigation: 弥合建议（一句话，针对挑战，没挑战可不填，为空字符串）

只输出 JSON 数组，不要其他文字。"""

        response = llm.invoke(prompt)
        content = response.content.strip()
        import re
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            matches = json.loads(json_match.group())
            # 验证并清洗结果
            result = []
            for m in matches[:5]:
                if m.get("id") is not None:
                    result.append({
                        "id": m["id"],
                        "fit_score": m.get("fit_score", 80),
                        "reason": m.get("reason", "综合推荐"),
                        "fit_advantages": m.get("fit_advantages", []),
                        "potential_challenges": m.get("potential_challenges", []),
                        "mitigation": m.get("mitigation", "")
                    })
            if result:
                return result
    except Exception as e:
        logger.warning(f"LLM smart match failed, falling back to keyword match: {e}")

    # 降级：关键词匹配（兜底）
    WEIGHTS = {"species": 3, "tags": 2, "desc": 1, "name": 1}
    keywords = [w.strip() for w in full_context.replace('，', ',').replace(' ', ',').split(',') if w.strip()]

    scored = []
    for pet in pet_list:
        score = 0
        matched_reasons = []
        species_text = (pet.get('species') or '').lower()
        for kw in keywords:
            if kw in species_text:
                score += WEIGHTS["species"]
                matched_reasons.append(f'物种匹配"{kw}"')
        for tag in (pet.get('tags') or []):
            for kw in keywords:
                if kw in str(tag).lower():
                    score += WEIGHTS["tags"]
                    matched_reasons.append(f'标签匹配"{kw}"')
        desc_text = (pet.get('desc') or '').lower()
        for kw in keywords:
            if kw in desc_text:
                score += WEIGHTS["desc"]
                matched_reasons.append(f'描述匹配"{kw}"')
        reason_str = "、".join(matched_reasons[:3]) if matched_reasons else "综合推荐"
        scored.append((score, pet, reason_str))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": p.get("id"),
            "fit_score": min(95, 60 + s * 5),
            "reason": f"与您的需求高度契合（{r}）",
            "fit_advantages": [r] if r != "综合推荐" else ["综合条件匹配"],
            "potential_challenges": [],
            "mitigation": ""
        }
        for s, p, r in scored[:5]
        if p.get("id") is not None
    ]


def submit_adoption_feedback(
    user_id: int,
    pet_id: int,
    pet_name: str,
    overall_satisfaction: int,
    bond_level: str,
    unexpected_challenges: str,
    would_recommend: bool,
    free_feedback: str
) -> int:
    """
    创新点3：领养后回访反馈存储。
    将真实领养质量标注写入数据库，作为后续匹配模型的监督信号（数据飞轮闭环）。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        # 确保表存在（首次调用时自动创建）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adoption_feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                pet_id INTEGER,
                pet_name TEXT,
                overall_satisfaction INTEGER,
                bond_level TEXT,
                unexpected_challenges TEXT,
                would_recommend INTEGER,
                free_feedback TEXT,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            """INSERT INTO adoption_feedbacks
               (user_id, pet_id, pet_name, overall_satisfaction, bond_level,
                unexpected_challenges, would_recommend, free_feedback)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, pet_id, pet_name, overall_satisfaction, bond_level,
             unexpected_challenges, 1 if would_recommend else 0, free_feedback)
        )
        feedback_id = cursor.lastrowid
        conn.commit()
    return feedback_id

def generate_nutrition_plan(data: dict) -> Tuple[dict, str, str, int]:
    """生成初始营养方案，并存入数据库"""
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 过滤掉 build_nutrition_plan 不支持的业务字段
    logic_data = {k: v for k, v in data.items() if k not in ["user_id", "pet_name"]}
    plan = build_nutrition_plan(**logic_data)
    
    # 增加精细化字段
    plan["confidence_level"] = 0.95
    plan["recheck_in_days"] = 14
    plan["requires_vet"] = False
    
    markdown = render_nutrition_markdown(data.get('species', 'cat'), plan)
    
    # 持久化到数据库
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO nutrition_plans (user_id, pet_name, species, plan_data) VALUES (?, ?, ?, ?)",
            (data.get("user_id"), data.get("pet_name"), data.get("species"), json.dumps(plan))
        )
        plan_id = cursor.lastrowid
        conn.commit()
    
    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "nutrition", "NutritionPlanner", str(data), "Initial Plan Generated", latency)
    
    return plan, markdown, trace_id, plan_id

def submit_nutrition_feedback(data: dict) -> int:
    """提交营养反馈"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO nutrition_feedbacks
               (plan_id, weight_change, appetite_status, stool_status, activity_change)
               VALUES (?, ?, ?, ?, ?)""",
            (data.get("plan_id"), data.get("weight_change"), data.get("appetite_status"),
             data.get("stool_status"), data.get("activity_change"))
        )
        feedback_id = cursor.lastrowid
        conn.commit()
    return feedback_id

def run_adoption_assessment_service(
    applicant_info: str,
    target_species: str,
    target_pet_name: str,
    monthly_budget: float = 0,
    daily_companion_hours: float = 0,
    has_pet_experience: bool = False,
    housing_type: str = "apartment",
    application_reason: str = "",
    existing_pets: str = ""
) -> Tuple[dict, str]:
    """
    领养资质多智能体评估服务入口。

    L2 规则预筛在 agents 层执行（命中硬约束可跳过 LLM）。
    Fallback 规则引擎在 AI 完全不可用时兜底，保证接口不崩溃。
    返回 (result_dict, trace_id)。
    """
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    fallback = False

    try:
        from src.agents.agents import run_adoption_assessment
        result = run_adoption_assessment(
            applicant_info=applicant_info,
            target_species=target_species,
            target_pet_name=target_pet_name,
            monthly_budget=monthly_budget,
            daily_companion_hours=daily_companion_hours,
            has_pet_experience=has_pet_experience,
            housing_type=housing_type,
            application_reason=application_reason,
            existing_pets=existing_pets,
        )
    except Exception as e:
        logger.warning(f"Adoption Assessment AI Error (fallback activated): {e}")
        fallback = True
        # Fallback：单独运行规则预筛引擎，给出基础评估
        from src.agents.adoption_profiler import rule_engine_prescreen
        prescreen = rule_engine_prescreen(
            target_species=target_species,
            monthly_budget=monthly_budget,
            daily_companion_hours=daily_companion_hours,
            has_pet_experience=has_pet_experience,
            housing_type=housing_type,
            existing_pets=existing_pets,
            applicant_info=applicant_info,
        )
        risk_level = "High" if prescreen["hard_block"] else ("High" if prescreen["penalty_score"] >= 40 else "Medium")
        decision = "reject" if prescreen["hard_block"] else "review_required"
        readiness_score = max(0, 60 - prescreen["penalty_score"])
        risk_factors = [
            {"dimension": "规则预筛", "description": flag.lstrip("🔴🟡 "), "severity": "high" if "🔴" in flag else "medium"}
            for flag in prescreen["risk_flags"]
        ]
        summary = (
            f"## 领养资质评估报告（规则引擎降级版）\n\n"
            f"| 指标 | 结果 |\n|------|------|\n"
            f"| 目标宠物 | {target_pet_name}（{target_species}） |\n"
            f"| 准备度评分 | {readiness_score} / 100（规则引擎估算） |\n"
            f"| 综合风险等级 | {risk_level} |\n"
            f"| 系统建议决策 | {decision} |\n\n"
            f"> AI 专家系统暂时不可用，已启用规则引擎基础评估。建议管理员进行人工审核。\n\n"
            f"**规则预筛摘要**：{prescreen['prescreen_summary']}"
        )
        result = {
            "readiness_score": readiness_score,
            "success_probability": round(readiness_score / 100 * 0.7, 2),
            "confidence_level": 0.60,
            "risk_level": risk_level,
            "decision": decision,
            "need_manual_review": True,
            "risk_factors": risk_factors,
            "recommendations": ["AI 专家系统暂不可用，请管理员进行人工审核。"],
            "review_note": f"系统降级（Fallback），规则预筛惩罚分：{prescreen['penalty_score']}",
            "baseline_report": "AI 服务暂不可用",
            "profile_report": "AI 服务暂不可用，建议人工审核",
            "cohabitation_report": "AI 服务暂不可用",
            "final_summary": summary,
        }

    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(
        trace_id, "adoption_assessment",
        "AdoptionProfilerCrew",
        f"{applicant_info[:200]} | {target_species}/{target_pet_name}",
        result.get("risk_level", "unknown"),
        latency, fallback,
        tool_name="rule_prescreen+encyclopedia+profiler+cohabitation"
    )
    return result, trace_id


def replan_nutrition(plan_id: int, feedback_id: int) -> Tuple[dict, str, str]:
    """基于反馈进行再规划 (闭环优化)"""
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nutrition_plans WHERE id = ?", (plan_id,))
        old_plan_row = cursor.fetchone()
        cursor.execute("SELECT * FROM nutrition_feedbacks WHERE id = ?", (feedback_id,))
        feedback_row = cursor.fetchone()

    if not old_plan_row or not feedback_row:
        raise ValueError("Plan or Feedback not found")

    try:
        old_plan = json.loads(old_plan_row["plan_data"])
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"方案数据损坏，无法解析: {e}")
    feedback = dict(feedback_row)
    
    # AI 优化逻辑 (模拟闭环调整)
    new_plan = old_plan.copy()
    adjustment_reason = "基于您的反馈进行了优化。"
    
    # 简单的闭环规则引擎模拟（实际可调用 LLM 深度分析）
    if feedback["weight_change"] == "gain" and old_plan.get("goal") != "gain_weight":
        new_plan["daily_kcal"] = max(200, new_plan["daily_kcal"] * 0.9)
        adjustment_reason = "宠物体重增加过多，已适当调减每日卡路里摄入。"
    elif feedback["weight_change"] == "lose" and old_plan.get("goal") != "lose_weight":
        new_plan["daily_kcal"] = min(5000, new_plan["daily_kcal"] * 1.1)
        adjustment_reason = "宠物体重下降，已增加营养摄入。"
        
    if feedback["stool_status"] in ["soft", "diarrhea"]:
        new_plan["requires_vet"] = True
        new_plan["confidence_level"] = 0.7
        adjustment_reason += " 观察到排便异常，建议咨询兽医。"
    else:
        new_plan["recheck_in_days"] = 30
        new_plan["confidence_level"] = 0.98

    new_plan["adjustment_summary"] = adjustment_reason
    
    markdown = render_nutrition_markdown(old_plan_row["species"], new_plan)
    markdown = f"### 🔄 再规划方案报告\n\n**调整原因**: {adjustment_reason}\n\n" + markdown
    
    # 保存新方案
    with get_db() as conn:
        conn.execute("UPDATE nutrition_plans SET is_active = 0 WHERE id = ?", (plan_id,))
        conn.execute(
            "INSERT INTO nutrition_plans (user_id, pet_name, species, plan_data) VALUES (?, ?, ?, ?)",
            (old_plan_row["user_id"], old_plan_row["pet_name"], old_plan_row["species"], json.dumps(new_plan))
        )
        conn.commit()

    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "nutrition_replan", "NutritionOptimizer", str(feedback), "Replanning Done", latency)
    
    return new_plan, markdown, trace_id
