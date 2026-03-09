import os
import sys
import time
import uuid
import json
from typing import List, Optional, Tuple
from src.agents.nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from src.web.services.db_service import get_db_connection

def _log_agent_trace(trace_id: str, endpoint: str, agent_name: str, input_msg: str, output_msg: str, latency_ms: int, fallback: bool = False, tool_name: str = "default"):
    """记录 AI 执行日志"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO agent_trace_logs 
               (trace_id, endpoint, agent_name, tool_name, latency_ms, fallback_used, input_msg, output_msg) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (trace_id, endpoint, agent_name, tool_name, latency_ms, 1 if fallback else 0, input_msg, output_msg)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log agent trace: {e}")

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
        print(f"AI Service Error: {e}")
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
        print(f"Triage Service Error: {e}")
        reply = f"医生智能系统正在诊断中，针对您的症状：{symptom}，我们建议您观察 2-4 小时。"
        fallback = True
    
    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "triage", agent_name, symptom, reply, latency, fallback)
    return reply, trace_id

def get_smart_match(user_query: str, pet_list: List[dict]) -> List[dict]:
    """智能宠物匹配逻辑"""
    query = user_query.lower()
    
    try:
        from src.agents.agents import run_pet_crew
        _ = run_pet_crew(user_query)
    except Exception:
        pass

    scored = []
    for pet in pet_list:
        text = f"{pet.get('name','') or ''} {pet.get('species','') or ''} {pet.get('desc','') or ''} {' '.join(pet.get('tags', []))}".lower()
        score = 0
        for word in query.replace('，', ',').split(','):
            w = word.strip()
            if w and w in text:
                score += 1
        scored.append((score, pet))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [
        {
            "id": p.get("id"),
            "reason": f"匹配度 {s}：基于您的描述，该宠物性格和特征与您的需求高度契合。",
        }
        for s, p in scored[:5]
        if p.get("id") is not None
    ]
    return matches

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO nutrition_plans (user_id, pet_name, species, plan_data) VALUES (?, ?, ?, ?)",
        (data.get("user_id"), data.get("pet_name"), data.get("species"), json.dumps(plan))
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "nutrition", "NutritionPlanner", str(data), "Initial Plan Generated", latency)
    
    return plan, markdown, trace_id, plan_id

def submit_nutrition_feedback(data: dict) -> int:
    """提交营养反馈"""
    conn = get_db_connection()
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
    conn.close()
    return feedback_id

def replan_nutrition(plan_id: int, feedback_id: int) -> Tuple[dict, str, str]:
    """基于反馈进行再规划 (闭环优化)"""
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nutrition_plans WHERE id = ?", (plan_id,))
    old_plan_row = cursor.fetchone()
    cursor.execute("SELECT * FROM nutrition_feedbacks WHERE id = ?", (feedback_id,))
    feedback_row = cursor.fetchone()
    conn.close()
    
    if not old_plan_row or not feedback_row:
        raise ValueError("Plan or Feedback not found")
        
    old_plan = json.loads(old_plan_row["plan_data"])
    feedback = dict(feedback_row)
    
    # AI 优化逻辑 (模拟闭环调整)
    new_plan = old_plan.copy()
    adjustment_reason = "基于您的反馈进行了优化。"
    
    # 简单的闭环规则引擎模拟（实际可调用 LLM 深度分析）
    if feedback["weight_change"] == "gain" and old_plan.get("goal") != "gain_weight":
        new_plan["daily_kcal"] *= 0.9
        adjustment_reason = "宠物体重增加过多，已适当调减每日卡路里摄入。"
    elif feedback["weight_change"] == "lose" and old_plan.get("goal") != "lose_weight":
        new_plan["daily_kcal"] *= 1.1
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE nutrition_plans SET is_active = 0 WHERE id = ?", (plan_id,))
    cursor.execute(
        "INSERT INTO nutrition_plans (user_id, pet_name, species, plan_data) VALUES (?, ?, ?, ?)",
        (old_plan_row["user_id"], old_plan_row["pet_name"], old_plan_row["species"], json.dumps(new_plan))
    )
    conn.commit()
    conn.close()

    latency = int((time.time() - start_time) * 1000)
    _log_agent_trace(trace_id, "nutrition_replan", "NutritionOptimizer", str(feedback), "Replanning Done", latency)
    
    return new_plan, markdown, trace_id
