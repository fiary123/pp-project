import os
import sys
import time
import uuid
import json
import logging
from typing import List, Optional, Tuple
from src.agents.nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from src.agents.agents import run_nutrition_expert, run_nutrition_replan
from src.web.services.db_service import get_db
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIService:
    """统一的 AI 服务接口"""
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=api_key,
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
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

def get_triage_reply(symptom: str, image_bytes: bytes | None = None) -> Tuple[str, str]:
    """
    调用分诊专家 Agent，返回 (reply, trace_id)。
    image_bytes 不为空时，先由 Qwen-VL 分析图片，再交给 DeepSeek MedicalExpert 推理。
    """
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    fallback = False
    agent_name = "TriageExpert(DeepSeek)" if not image_bytes else "TriageExpert(QwenVL+DeepSeek)"

    try:
        from src.agents.agents import run_triage_expert
        reply = run_triage_expert(symptom, image_bytes=image_bytes)
    except Exception as e:
        logger.warning(f"Triage Service Error (fallback activated): {e}")
        reply = f"医生智能系统正在诊断中，针对您的症状：{symptom}，我们建议您观察 2-4 小时。"
        fallback = True

    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "triage", agent_name, symptom, reply, latency, fallback)
    return reply, trace_id

def get_match_followup_questions(user_query: str) -> List[dict]:
    """
    创新点1：需求显化 Agent（CrewAI）。
    调用 run_match_followup，由 NeedAnalyzer Agent 通过 generate_followup_questions 工具
    识别用户描述中的信息缺口，生成 2-3 个结构化追问，将模糊偏好转化为可量化维度。
    """
    try:
        from src.agents.agents import run_match_followup
        return run_match_followup(user_query)
    except Exception as e:
        logger.warning(f"run_match_followup failed, using default questions: {e}")
    return [
        {"key": "activity_level",   "question": "您更希望宠物是活泼好动还是安静乖巧的？", "options": ["活泼好动", "安静乖巧", "都可以"]},
        {"key": "living_space",     "question": "您的居住空间大概是什么情况？",             "options": ["小型公寓", "中等户型", "带院子的大户型"]},
        {"key": "time_availability","question": "平时每天能陪伴宠物大概多长时间？",          "options": ["2小时以内", "2-4小时", "4小时以上"]}
    ]


def get_smart_match(user_query: str, pet_list: List[dict], followup_answers: Optional[dict] = None) -> List[dict]:
    """
    创新点1+3：两 Agent 串联 CrewAI（工具评分 + 语义解读）。
    - MatchScorer Agent：调用 score_pet_match 工具，基于用户偏好画像进行多维结构化评分
    - MatchAdvisor Agent：读取评分数据，生成人性化推荐理由（适配优势/潜在挑战/弥合建议）
    LLM 不能自行决定分数，评分结果来自工具，推荐理由基于工具数据生成，保证可解释性。
    """
    try:
        from src.agents.agents import run_smart_match
        return run_smart_match(user_query, pet_list, followup_answers)
    except Exception as e:
        logger.warning(f"run_smart_match failed, falling back to keyword match: {e}")

    # 降级：关键词匹配（兜底）
    context_parts = [user_query]
    if followup_answers:
        context_parts.extend(str(v) for v in followup_answers.values())
    keywords = [w.strip() for w in "，".join(context_parts).replace(" ", "，").split("，") if w.strip()]

    scored = []
    for pet in pet_list:
        score = sum(
            3 if kw in (pet.get("species") or "") else
            1 if kw in (pet.get("desc") or pet.get("description") or "") else 0
            for kw in keywords
        )
        scored.append((score, pet))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"id": p.get("id"), "fit_score": min(95, 60 + s * 5),
         "reason": "综合条件推荐", "fit_advantages": [], "potential_challenges": [], "mitigation": ""}
        for s, p in scored[:5] if p.get("id") is not None
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
    """生成初始营养方案（2-Agent 流水线：NutritionCalculator → NutritionPlanner），并存入数据库"""
    trace_id = str(uuid.uuid4())
    start_time = time.time()

    # 调用 2-Agent CrewAI 流水线：
    #   Agent1 NutritionCalculator 调用工具计算热量+禁忌清单
    #   Agent2 NutritionPlanner    接收 context，输出解读 Markdown
    try:
        result = run_nutrition_expert(data)
        plan = result["plan"]
        markdown = result["explanation_markdown"]
    except Exception as e:
        logger.warning(f"run_nutrition_expert failed, fallback to math: {e}")
        logic_data = {k: v for k, v in data.items() if k not in ["user_id", "pet_name"]}
        plan = build_nutrition_plan(**logic_data)
        markdown = render_nutrition_markdown(data.get('species', 'cat'), plan)

    # 增加精细化字段
    plan.setdefault("confidence_level", 0.95)
    plan.setdefault("recheck_in_days", 14)
    plan.setdefault("requires_vet", False)

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
    _log_agent_trace(trace_id, "nutrition", "NutritionCalculator+NutritionPlanner", str(data), "Initial Plan Generated", latency)

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
    
    # 规则引擎调整数值（保证数值可溯源）
    new_plan = old_plan.copy()
    if feedback["weight_change"] == "gain" and old_plan.get("goal") != "gain_weight":
        new_plan["daily_kcal"] = max(200, int(new_plan["daily_kcal"] * 0.9))
    elif feedback["weight_change"] == "lose" and old_plan.get("goal") != "lose_weight":
        new_plan["daily_kcal"] = min(5000, int(new_plan["daily_kcal"] * 1.1))

    if feedback["stool_status"] in ["soft", "diarrhea"]:
        new_plan["requires_vet"] = True
        new_plan["confidence_level"] = 0.7
    else:
        new_plan["recheck_in_days"] = 30
        new_plan["confidence_level"] = 0.98

    # ── 第三层：手动记忆注入 ────────────────────────────────────────
    # 查询该宠物最近 3 次历史方案（含对应反馈），拼成趋势文本注入 Optimizer context
    history_context = ''
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # 取同一 pet_name 最近 3 条已归档方案（排除当前激活方案）
            cursor.execute(
                """SELECT np.id, np.plan_data, np.create_time,
                          nf.weight_change, nf.appetite_status, nf.stool_status
                   FROM nutrition_plans np
                   LEFT JOIN nutrition_feedbacks nf ON nf.plan_id = np.id
                   WHERE np.pet_name = ? AND np.user_id = ? AND np.is_active = 0
                   ORDER BY np.create_time DESC LIMIT 3""",
                (old_plan_row["pet_name"], old_plan_row["user_id"])
            )
            history_rows = cursor.fetchall()

        if history_rows:
            lines = []
            for i, row in enumerate(history_rows, 1):
                try:
                    p = json.loads(row["plan_data"])
                    kcal = p.get("daily_kcal", "?")
                except Exception:
                    kcal = "?"
                wc   = row["weight_change"] or "未记录"
                apt  = row["appetite_status"] or "未记录"
                st   = row["stool_status"] or "未记录"
                ts   = row["create_time"] or ""
                lines.append(
                    f'第{i}次（{ts[:10]}）：daily_kcal={kcal} kcal，'
                    f'反馈：体重变化={wc}，食欲={apt}，排便={st}'
                )
            history_context = '\n'.join(lines)
    except Exception as e:
        logger.warning(f"历史方案查询失败，跳过记忆注入: {e}")

    # NutritionOptimizer Agent：基于反馈 + 历史趋势生成闭环评审
    try:
        optimizer_markdown = run_nutrition_replan(new_plan, feedback, old_plan_row["species"], history_context)
    except Exception as e:
        logger.warning(f"run_nutrition_replan failed, fallback: {e}")
        optimizer_markdown = render_nutrition_markdown(old_plan_row["species"], new_plan)

    new_plan["adjustment_summary"] = optimizer_markdown[:200]  # 摘要存入 plan 供前端展示

    markdown = f"### 🔄 再规划方案报告（NutritionOptimizer Agent 解读）\n\n{optimizer_markdown}"
    
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
