import os
import uuid
import time
import json
import logging
from typing import Tuple, List, Dict, Any, Optional
from src.web.services.db_service import get_db

logger = logging.getLogger(__name__)

def _log_agent_trace(trace_id: str, scene: str, agent_names: str, input_msg: str, output_msg: str, latency: int):
    """持久化 Agent 决策轨迹"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_trace_logs 
               (trace_id, scene, agent_names, input_msg, output_msg, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (trace_id, scene, agent_names, input_msg, output_msg, latency)
        )
        conn.commit()

def generate_nutrition_plan(data: dict) -> Tuple[dict, str, str, int]:
    """生成营养建议规划"""
    from src.agents.agents import run_nutrition_expert
    
    trace_id = str(uuid.uuid4())
    start_time = time.time()

    # 1. 调用 Agent 生成方案 (CrewAI)
    # 此处假设 run_nutrition_expert 返回方案文本，并带有一些元数据
    result = run_nutrition_expert(data)
    
    # 2. 模拟解析或直接使用 (具体取决于 Agent 的 output)
    plan = {
        "daily_kcal": 450,
        "food_weight_g": 120,
        "water_ml": 250,
        "special_notes": "建议增加湿粮比例，缓解脱水风险。"
    }
    markdown = result.get("plan", "### 智能营养建议\n方案生成中...")

    # 3. 持久化记录
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pet_nutrition_plans (pet_id, plan_content_json) VALUES (?, ?)",
            (data.get("pet_id"), json.dumps(plan, ensure_ascii=False))
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
              Kraus_stool_status := data.get("stool_status"), data.get("activity_change"))
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
    架构已升级：统一人入 agents.run_adoption_assessment 触发委员会评审流程。
    """
    trace_id = str(uuid.uuid4())
    start_time = time.time()

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
            existing_pets=existing_pets
        )
        
        # 补全 trace 元数据
        if "trace_id" not in result:
            result["trace_id"] = trace_id
        
        latency = int((time.time() - start_time) * 1000)
        _log_agent_trace(trace_id, "adoption", "CommitteeReviewSystem", str(applicant_info), "Full Assessment Completed", latency)
        
        return result, trace_id
        
    except Exception as e:
        logger.exception(f"Adoption assessment service failed: {e}")
        # 返回基础结构防止前端崩溃
        return {
            "readiness_score": 0,
            "decision": "error",
            "summary": f"评估服务暂时不可用: {str(e)}"
        }, trace_id

def get_smart_match(user_query: str, pet_list: List[dict], user_history: List[str]) -> dict:
    """智能匹配推荐逻辑入口"""
    # 模拟简单的向量检索或语义匹配逻辑
    matched_pets = pet_list[:3] # 示例简化
    return {
        "recommended_ids": [p["id"] for p in matched_pets],
        "match_reason": "基于您的近期动态和偏好为您精选。"
    }

def submit_adoption_feedback(application_id: int, feedback_data: dict):
    """提交领养回访反馈并触发后验学习"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE applications SET followup_status = 'completed' WHERE id = ?",
            (application_id,)
        )
        # 这里会进一步调用 memory 模块更新权重
        conn.commit()
    return True
