# 多智能体 CrewAI 核心逻辑
import os
import json
import logging
import chromadb
import asyncio
import edge_tts
import base64
import time
import re
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# 导入专项 Agent 构造函数
from .audit_expert import get_audit_expert_agent
from .pet_expert import get_pet_expert_agent
from .pet_persona import get_pet_persona_agent
from .nutrition_expert import get_nutrition_expert_agent, get_nutrition_planner_agent, get_nutrition_optimizer_agent
from .nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from .adoption_profiler import get_encyclopedia_agent, get_adoption_profiler_agent, get_cohabitation_risk_agent
from .tools import generate_followup_questions, score_pet_match, search_mutual_aid_tasks, recall_adoption_experience

# ==========================================
# 1. 环境与模型配置
# ==========================================

from dotenv import load_dotenv
load_dotenv()

_DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
_DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

crewai_llm = LLM(
    model="openai/deepseek-chat",
    api_key=_DEEPSEEK_API_KEY,
    base_url=_DEEPSEEK_BASE_URL,
    temperature=0.3
)
llm = crewai_llm

# ==========================================
# 2. 辅助工具函数
# ==========================================

def _extract_json_payload(raw_text: str) -> Dict[str, Any]:
    if not raw_text: return {}
    cleaned = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.S)
    if fenced: cleaned = fenced.group(1)
    else:
        brace = re.search(r"(\{.*\})", cleaned, re.S)
        if brace: cleaned = brace.group(1)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except: return {}

def _merge_unique(existing: Optional[List[str]], incoming: Optional[List[str]], limit: int = 6) -> List[str]:
    merged: List[str] = []
    for item in (existing or []) + (incoming or []):
        text = str(item).strip()
        if text and text not in merged: merged.append(text)
        if len(merged) >= limit: break
    return merged

def _build_local_pet_reply(user_msg: str, pet_name: str, pet_species: str, pet_desc: str, observer_profile: Optional[Dict[str, Any]] = None) -> str:
    prompt = (observer_profile or {}).get("next_probe") or "你平时会怎么照顾我呀？"
    missing_topics = (observer_profile or {}).get("missing_topics") or []
    if missing_topics:
        prompt = f"我还想知道一下{missing_topics[0]}，这样我会更安心一点。"

    if "猫" in pet_species:
        opener = "喵呜，我有认真听你说哦。"
    elif "狗" in pet_species or "犬" in pet_species:
        opener = "汪，我在认真了解你呢。"
    else:
        opener = "我有在认真听你说。"

    desc_hint = f"我平时{pet_desc[:22]}。" if pet_desc else ""
    if any(word in user_msg for word in ["上班", "加班", "出差"]):
        care_hint = "如果白天要独处，我会更希望你回家后能多陪陪我。"
    elif any(word in user_msg for word in ["预算", "花费", "看病"]):
        care_hint = "如果我偶尔生病或者需要护理，你愿意继续照顾我吗？"
    else:
        care_hint = "我会想知道你是不是愿意长期稳定地照顾我。"

    return f"{opener}{desc_hint}{care_hint}{prompt}"

# ==========================================
# 3. 核心运行工作流 (语音、访谈与匹配)
# ==========================================

async def generate_edge_voice(text: str, pet_species: str):
    """异步生成 Edge-TTS 语音字节流"""
    voice = "zh-CN-XiaoyiNeural"
    if "狗" in pet_species or "犬" in pet_species:
        voice = "zh-CN-YunxiNeural"
    elif "猫" in pet_species:
        voice = "zh-CN-XiaoxiaoNeural"
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data += chunk["data"]
    return audio_data

async def analyze_pet_interview(user_msg: str, pet_name: str, pet_species: str, pet_desc: str, history: Optional[List[dict]] = None, previous_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    observer_agent = Agent(
        role="领养访谈观察员",
        goal="从自然对话中提取领养人的真实画像，并设计下一轮测试点。",
        backstory="你是一名数字分身背后的观察员，识别责任感、稳定性等信号。",
        llm=crewai_llm,
        verbose=True,
        allow_delegation=False,
    )
    history_lines = [f"{('领养人' if i.get('role') == 'user' else pet_name)}：{i.get('content', '')}" for i in (history or [])[-6:]]
    history_context = "\n".join(history_lines) if history_lines else "暂无"
    task = Task(
        description=(f"观察对话。宠物：{pet_name}({pet_species})。历史：\n{history_context}\n用户输入：{user_msg}\n画像：{json.dumps(previous_profile or {}, ensure_ascii=False)}\n请输出 JSON 包含 user_traits, strengths, risk_flags, missing_topics, next_probe, interview_stage, summary。"),
        expected_output="严格 JSON 对象。",
        agent=observer_agent,
    )
    try:
        raw = await asyncio.to_thread(lambda: str(Crew(agents=[observer_agent], tasks=[task]).kickoff()))
        parsed = _extract_json_payload(raw)
    except: parsed = {}
    return {
        "user_traits": _merge_unique((previous_profile or {}).get("user_traits"), parsed.get("user_traits")),
        "strengths": _merge_unique((previous_profile or {}).get("strengths"), parsed.get("strengths")),
        "risk_flags": _merge_unique((previous_profile or {}).get("risk_flags"), parsed.get("risk_flags")),
        "missing_topics": _merge_unique(parsed.get("missing_topics"), (previous_profile or {}).get("missing_topics"), limit=4),
        "next_probe": str(parsed.get("next_probe") or (previous_profile or {}).get("next_probe") or "继续了解对方").strip(),
        "interview_stage": str(parsed.get("interview_stage") or (previous_profile or {}).get("interview_stage") or "early"),
        "summary": str(parsed.get("summary") or (previous_profile or {}).get("summary") or "持续更新画像中").strip(),
    }

async def run_pet_chat(user_msg: str, pet_name: str, pet_species: str, pet_desc: str, history: list = None, observer_profile: Optional[Dict[str, Any]] = None):
    persona_agent = get_pet_persona_agent(crewai_llm, pet_name, pet_species, pet_desc)
    history_context = "\n".join([f"{('主人' if h['role'] == 'user' else pet_name)}：{h['content']}" for h in history[-6:]]) if history else ""
    observer_context = f"画像参考：{json.dumps(observer_profile or {}, ensure_ascii=False)}\n" if observer_profile else ""
    task = Task(description=f'{observer_context}{history_context}\n用户说："{user_msg}"。请回复并自然带出一句轻量追问。', expected_output='一段简短回复。', agent=persona_agent)
    try:
        response_text = await asyncio.to_thread(lambda: str(Crew(agents=[persona_agent], tasks=[task]).kickoff()))
    except Exception:
        logger.exception("pet_chat llm kickoff failed")
        response_text = _build_local_pet_reply(
            user_msg=user_msg,
            pet_name=pet_name,
            pet_species=pet_species,
            pet_desc=pet_desc,
            observer_profile=observer_profile,
        )
    try:
        audio_bytes = await generate_edge_voice(response_text, pet_species)
        return response_text, base64.b64encode(audio_bytes).decode()
    except Exception:
        logger.exception("pet_chat voice generation failed")
        return response_text, None

def run_pet_crew(user_message: str) -> str:
    p, a = get_pet_expert_agent(llm), get_audit_expert_agent(llm)
    t1 = Task(description=f'查询宠物需求："{user_message}"。', expected_output='列表。', agent=p)
    t2 = Task(description='进行匹配分析。', expected_output='报告。', agent=a, context=[t1])
    return str(Crew(agents=[p, a], tasks=[t1, t2], process=Process.sequential).kickoff())

def get_consensus_coordinator_agent(llm):
    return Agent(role='领养评估共识协调员', goal='给出最终共识报告。', backstory='资深动物福利主席，客观平衡。', llm=llm, verbose=True, max_iter=3, allow_delegation=False)

# ─── 创新点：领养评估 3.8 (DAG并发 + 历史经验记忆) ───

def run_adoption_assessment(
    applicant_info: str,
    target_species: str,
    target_pet_name: str,
    monthly_budget: float = 0,
    daily_companion_hours: float = 0,
    has_pet_experience: bool = False,
    housing_type: str = "apartment",
    application_reason: str = "",
    existing_pets: str = "",
    publisher_preferences: dict = None,
    knowledge_context: str = "",
    memory_context: str = "",
) -> dict:
    start_time = time.time()
    from .adoption_profiler import rule_engine_prescreen, get_encyclopedia_agent, get_adoption_profiler_agent, get_cohabitation_risk_agent
    from .audit_expert import get_audit_expert_agent
    prescreen = rule_engine_prescreen(target_species, monthly_budget, daily_companion_hours, has_pet_experience, housing_type, existing_pets, applicant_info, publisher_preferences)
    if prescreen["hard_block"]:
        return {"readiness_score": 0, "success_probability": 0.0, "decision": "reject", "risk_level": "High", "risk_factors": [], "recommendations": ["解决硬拦截后重试"], "final_summary": f"## 拦截\n原因：{prescreen['prescreen_summary']}"}
    
    e_agent, p_agent, a_agent, c_agent, ch_agent = get_encyclopedia_agent(llm), get_adoption_profiler_agent(llm), get_audit_expert_agent(llm), get_consensus_coordinator_agent(llm), get_cohabitation_risk_agent(llm)
    h_expert = Agent(role='历史复盘专家', goal='召回相似案例。', backstory='管理长期记忆。', llm=llm, tools=[recall_adoption_experience], verbose=True, allow_delegation=False)
    
    t_recall = Task(description=f'检索画像相似反馈。可参考记忆上下文：{memory_context}', expected_output='复盘报告。', agent=h_expert, async_execution=True)
    t_ency = Task(description=f'提取【{target_species}】基准。可参考知识上下文：{knowledge_context}', expected_output='JSON。', agent=e_agent, async_execution=True)
    t_cohab = Task(description=f'评估环境风险。申请人信息：{applicant_info}\n住房类型：{housing_type}\n原住宠物：{existing_pets}', expected_output='报告。', agent=ch_agent, context=[t_ency], async_execution=True)
    t_prop = Task(description=f'提出适配提议。申请理由：{application_reason}\n发布者偏好：{json.dumps(publisher_preferences or {}, ensure_ascii=False)}\n知识上下文：{knowledge_context}\n记忆上下文：{memory_context}', expected_output='提议书。', agent=p_agent, context=[t_ency, t_recall])
    t_audit = Task(description='审计质疑。', expected_output='质疑报告。', agent=a_agent, context=[t_prop, t_recall])
    t_cons = Task(description='终审裁决报告（含 readiness_score）。', expected_output='最终报告。', agent=c_agent, context=[t_prop, t_audit, t_cohab])
    
    try:
        res = str(Crew(agents=[h_expert, e_agent, p_agent, a_agent, c_agent, ch_agent], tasks=[t_recall, t_ency, t_cohab, t_prop, t_audit, t_cons], process=Process.hierarchical, manager_llm=llm, memory=True).kickoff())
        latency = round(time.time() - start_time, 2)
    except: res, latency = "评估中断", 0
    
    score = 65
    for p in [r'readiness[_\s]*score[：:\s]*(\d+)', r'评分[：:\s]*(\d+)', r'分数[：:\s]*(\d+)', r'(\d+)\s*/\s*100']:
        m = re.search(p, res, re.IGNORECASE)
        if m: score = int(m.group(1)); break
    
    decision = "pass"
    if any(k in res.lower() for k in ["驳回", "reject", "拒绝"]): decision = "reject"
    elif any(k in res.lower() for k in ["审核", "review", "人工"]): decision = "review_required"
    elif score < 50: decision = "reject"
    elif score < 75: decision = "review_required"
    
    return {"readiness_score": score, "success_probability": round(score/100*0.95, 2), "decision": decision, "risk_level": "Low" if score > 80 else ("High" if score < 50 else "Medium"), "risk_factors": [], "recommendations": ["AI 已复盘历史记忆。"], "final_summary": f"## 资质评估报告 v3.8\n**决策：{decision} (评分：{score}/100)**\n**耗时：{latency}s**\n\n### 裁决书\n{res}"}

# ─────────────────────────────────────────────────────────────

def run_knowledge_expert(user_query: str) -> str:
    r = Agent(role='检索员', goal='检索知识。', backstory='擅长检索。', llm=llm, tools=[recall_adoption_experience], verbose=True, allow_delegation=False)
    a = Agent(role='顾问', goal='给出建议。', backstory='资深顾问。', llm=llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(description=f'查询："{user_query}"。', expected_output='原文。', agent=r)
    t2 = Task(description='生成报告。', expected_output='Markdown。', agent=a, context=[t1])
    return str(Crew(agents=[r, a], tasks=[t1, t2]).kickoff())

def _parse_plan_from_tool_output(tool_output: str, profile: dict) -> dict:
    plan = {}
    try:
        for k in ('daily_kcal', 'daily_food_g', 'feedings_per_day'):
            m = re.search(rf'{k}=(\d+(?:\.\d+)?)', tool_output)
            if m: plan[k] = int(float(m.group(1)))
    except: pass
    if not all(k in plan for k in ('daily_kcal', 'daily_food_g', 'feedings_per_day')):
        from .nutrition_planner import build_nutrition_plan
        return build_nutrition_plan(species=profile.get('species','cat'), age_months=int(profile.get('age_months',12)), weight_kg=float(profile.get('weight_kg',4.0)), neutered=bool(profile.get('neutered',False)), activity_level=profile.get('activity_level','medium'), goal=profile.get('goal','maintain'), food_kcal_per_100g=float(profile.get('food_kcal_per_100g',360)), symptoms=profile.get('symptoms',[]))
    plan.update({'per_meal_g': [plan['daily_food_g']//plan['feedings_per_day']]*plan['feedings_per_day'], 'daily_water_ml': f'{round(float(profile.get("weight_kg",4.0))*50)}-{round(float(profile.get("weight_kg",4.0))*60)}', 'forbidden_foods': ['巧克力','洋葱'], 'transition_7days': ['D1-D2: 25%','D3-D4: 50%','D5-D6: 75%','D7: 100%'], 'risk_alerts': ['呕吐请就医']})
    return plan

def run_nutrition_expert(profile: dict) -> dict:
    c = get_nutrition_expert_agent(llm)
    p = get_nutrition_planner_agent(llm)
    o = get_nutrition_optimizer_agent(llm)
    t1 = Task(description='计算。', expected_output='数值。', agent=c)
    t2 = Task(description='规划。', expected_output='Markdown。', agent=p, context=[t1])
    t3 = Task(description='评审。', expected_output='报告。', agent=o, context=[t2])
    res = Crew(agents=[c, p, o], tasks=[t1, t2, t3]).kickoff()
    return {'plan': _parse_plan_from_tool_output(str(res), profile), 'explanation_markdown': str(res)}

def run_nutrition_replan(old_plan: dict, feedback: dict, species: str, history_context: str = '') -> str:
    p, o = get_nutrition_planner_agent(llm), get_nutrition_optimizer_agent(llm)
    t1 = Task(description='再规划。', expected_output='方案。', agent=p)
    t2 = Task(description='评审反馈。', expected_output='报告。', agent=o, context=[t1])
    return str(Crew(agents=[p, o], tasks=[t1, t2]).kickoff())

def run_match_followup(user_query: str) -> list:
    n = Agent(role='需求分析师', goal='生成追问。', backstory='分析需求。', llm=llm, tools=[generate_followup_questions], verbose=True, allow_delegation=False)
    task = Task(description=f'分析需求："{user_query}"。', expected_output='JSON追问。', agent=n)
    try:
        raw = str(Crew(agents=[n], tasks=[task]).kickoff())
        return json.loads(re.search(r'\[[\s\S]*\]', raw).group())[:3]
    except: return [{"key": "activity", "question": "活泼还是安静？", "options": ["活泼", "安静"]}]

def run_smart_match(user_query: str, pet_list: list, followup_answers: dict | None = None) -> list:
    s = Agent(role='评分员', goal='调用工具。', backstory='数据专员。', llm=llm, tools=[score_pet_match], verbose=True, allow_delegation=False)
    a = Agent(role='顾问', goal='生成理由。', backstory='资深顾问。', llm=llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(description='评分。', expected_output='JSON。', agent=s)
    t2 = Task(description='理由。', expected_output='推荐。', agent=a, context=[t1])
    try:
        raw = str(Crew(agents=[s, a], tasks=[t1, t2]).kickoff())
        return json.loads(re.search(r'\[[\s\S]*\]', raw).group())[:5]
    except: return [{"id": 1, "fit_score": 80, "reason": "推荐"}]

def run_mutual_aid_match(user_query: str) -> str:
    a, m = Agent(role='解析员', goal='检索。', backstory='分析员。', llm=llm, tools=[search_mutual_aid_tasks], verbose=True, allow_delegation=False), Agent(role='专家', goal='生成。', backstory='推荐专家。', llm=llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(description=f'解析："{user_query}"。', expected_output='摘要。', agent=a)
    t2 = Task(description='生成报告。', expected_output='Markdown。', agent=m, context=[t1])
    return str(Crew(agents=[a, m], tasks=[t1, t2]).kickoff())
