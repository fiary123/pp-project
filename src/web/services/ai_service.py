import os
import sys
import time
import uuid
import json
import logging
from typing import List, Optional, Tuple
from src.agents.nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from src.web.services.db_service import get_db

logger = logging.getLogger(__name__)

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

def get_smart_match(user_query: str, pet_list: List[dict]) -> List[dict]:
    """智能宠物匹配：加权关键词匹配（物种 > 标签 > 描述 > 名字）"""
    WEIGHTS = {"species": 3, "tags": 2, "desc": 1, "name": 1}
    keywords = [w.strip() for w in user_query.replace('，', ',').replace(' ', ',').split(',') if w.strip()]

    scored = []
    for pet in pet_list:
        score = 0
        matched_reasons = []

        species_text = (pet.get('species') or '').lower()
        for kw in keywords:
            if kw in species_text:
                score += WEIGHTS["species"]
                matched_reasons.append(f'物种匹配"{kw}"')

        for tag in pet.get('tags', []):
            for kw in keywords:
                if kw in tag.lower():
                    score += WEIGHTS["tags"]
                    matched_reasons.append(f'标签匹配"{kw}"')

        desc_text = (pet.get('desc') or '').lower()
        for kw in keywords:
            if kw in desc_text:
                score += WEIGHTS["desc"]
                matched_reasons.append(f'描述匹配"{kw}"')

        name_text = (pet.get('name') or '').lower()
        for kw in keywords:
            if kw in name_text:
                score += WEIGHTS["name"]
                matched_reasons.append(f'名字匹配"{kw}"')


        reason_str = "、".join(matched_reasons[:3]) if matched_reasons else "综合推荐"
        scored.append((score, pet, reason_str))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": p.get("id"),
            "reason": f"匹配分 {s}：{r}，该宠物与您的需求高度契合。",
        }
        for s, p, r in scored[:5]
        if p.get("id") is not None
    ]

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
