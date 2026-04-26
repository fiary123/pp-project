import os
import json
import uuid
import time
import base64
import logging
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from .tools import pet_health_knowledge_search, recall_adoption_experience
from .pet_persona import _build_local_pet_reply, generate_edge_voice
from .pet_expert import get_pet_expert_agent
from .audit_expert import get_audit_expert_agent
from .nutrition_expert import get_nutrition_expert_agent, get_nutrition_planner_agent, get_nutrition_optimizer_agent

logger = logging.getLogger(__name__)

# --- 创新点：工业级 Robust JSON 解析器 (Self-Healing Structured Output) ---

def safe_parse_json(raw: str, fallback_dict: dict = None) -> dict:
    """
    具备自愈能力的结构化输出解析器。
    1. 剥离 Markdown 围栏
    2. 自动修正尾部逗号
    3. 提取最外层大括号
    """
    import re
    if not raw: return fallback_dict or {}
    
    cleaned = raw.strip()
    # A. 提取 JSON 代码块
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.S)
    if fenced: cleaned = fenced.group(1)
    else:
        # B. 查找第一个 { 和最后一个 }
        brace = re.search(r"(\{.*\})", cleaned, re.S)
        if brace: cleaned = brace.group(1)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            # C. 尝试修复常见 JSON 语法错误 (简单版自愈)
            # 移除键值对末尾多余的逗号
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
            return json.loads(cleaned)
        except:
            logger.warning(f"JSON Parsing failed even after healing. Raw preview: {raw[:100]}...")
            return fallback_dict or {}

# --- 初始化 LLM ---
def _init_llm(temperature=0.7):
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("LLM API Key not found, using placeholder.")
        api_key = "sk-placeholder"
    
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=api_key,
        openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=temperature
    )

common_llm = _init_llm(temperature=0.7)
adoption_llm = _init_llm(temperature=0.3)  # 评估需要更严谨

# --- 业务函数 ---

async def run_pet_chat(user_msg: str, pet_name: str, pet_species: str, pet_desc: str, history: List[dict], observer_profile: dict) -> Tuple[str, Optional[str]]:
    from .pet_persona import get_pet_persona_agent
    persona_agent = get_pet_persona_agent(common_llm, pet_name, pet_species, pet_desc)
    
    history_str = "\n".join([f"{'用户' if m['role']=='user' else '宠物'}: {m['content']}" for m in history[-5:]])
    task = Task(
        description=(
            f"作为宠物 {pet_name}，回复领养人的话。用户说：{user_msg}\n"
            f"历史对话：{history_str}\n"
            f"领养人背景：{observer_profile}\n"
            f"保持性格一致性，不要透露你是AI。"
        ),
        expected_output="一句话回复，带有宠物的语气和情感。",
        agent=persona_agent
    )
    try:
        response_text = await asyncio.to_thread(lambda: str(Crew(agents=[persona_agent], tasks=[task]).kickoff()))
    except Exception:
        logger.exception("pet_chat llm kickoff failed")
        response_text = _build_local_pet_reply(user_msg, pet_name, pet_species, pet_desc, observer_profile)
    
    try:
        audio_bytes = await generate_edge_voice(response_text, pet_species)
        return response_text, base64.b64encode(audio_bytes).decode()
    except Exception:
        return response_text, None

async def analyze_pet_interview(user_msg: str, pet_name: str, pet_species: str, pet_desc: str) -> dict:
    """轻量级单智能体初审评估入口 (用于自适应路由扫描)"""
    from .audit_expert import get_audit_expert_agent
    audit_agent = get_audit_expert_agent(adoption_llm)
    
    task = Task(
        description=f"评估以下领养对话/背景：{user_msg}。针对宠物：{pet_name}({pet_species})。背景：{pet_desc}",
        expected_output="结构化 JSON，包含 readiness_score, risk_flags, summary。",
        agent=audit_agent
    )
    try:
        raw_res = await asyncio.to_thread(lambda: str(Crew(agents=[audit_agent], tasks=[task]).kickoff()))
        return safe_parse_json(raw_res, fallback_dict={"readiness_score": 60, "risk_flags": [], "summary": "初审执行异常"})
    except Exception as e:
        logger.error(f"analyze_pet_interview failed: {e}")
        return {"readiness_score": 60, "risk_flags": [], "summary": "评估引擎繁忙"}

def run_pet_crew(user_message: str) -> str:
    p, a = get_pet_expert_agent(common_llm), get_audit_expert_agent(common_llm)
    t1 = Task(description=f'查询宠物需求："{user_message}"。', expected_output='列表。', agent=p)
    t2 = Task(description='进行匹配分析。', expected_output='报告。', agent=a, context=[t1])
    return str(Crew(agents=[p, a], tasks=[t1, t2], process=Process.sequential).kickoff())

# =================================================================
# 统一主评估架构：统一人入委员会评审逻辑
# =================================================================

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
    """
    领养资质评估的统一人入口。
    统一切换为基于‘委员会评审委员会’的共识评估模型(Phase 1-3)。
    """
    from .committee_review import run_committee_assessment
    logger.info(f"Starting Unified Committee Assessment for {target_pet_name}")
    return run_committee_assessment(
        adoption_llm,
        applicant_info=applicant_info,
        target_species=target_species,
        target_pet_name=target_pet_name,
        monthly_budget=monthly_budget,
        daily_companion_hours=daily_companion_hours,
        has_pet_experience=has_pet_experience,
        housing_type=housing_type,
        application_reason=application_reason,
        existing_pets=existing_pets,
        publisher_preferences=publisher_preferences,
        knowledge_context=knowledge_context,
        memory_context=memory_context
    )

def run_knowledge_expert(user_query: str) -> str:
    r = Agent(role='知识检索员', goal='优先从宠物知识库中检索相关内容。', backstory='擅长提炼用户问题中的核心关键词并检索知识库。', llm=common_llm, tools=[pet_health_knowledge_search], verbose=True, allow_delegation=False)
    a = Agent(role='百科顾问', goal='基于检索结果组织清晰回答。', backstory='资深宠物养护顾问，能够区分知识库命中与模型常识补充。', llm=common_llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(description=f'针对用户问题“{user_query}”调用 pet_health_knowledge_search 检索相关内容。', expected_output='检索摘要。', agent=r)
    t2 = Task(description='根据检索结果生成最终回答。', expected_output='Markdown。', agent=a, context=[t1])
    try:
        result = str(Crew(agents=[r, a], tasks=[t1, t2]).kickoff())
        return result
    except Exception:
        return "知识库访问异常，请咨询兽医。"

def run_nutrition_expert(profile: dict) -> dict:
    c = get_nutrition_expert_agent(common_llm)
    p = get_nutrition_planner_agent(common_llm)
    o = get_nutrition_optimizer_agent(common_llm)
    t1 = Task(description='计算。', expected_output='数值。', agent=c)
    t2 = Task(description='规划。', expected_output='Markdown。', agent=p, context=[t1])
    t3 = Task(description='评审。', expected_output='报告。', agent=o, context=[t2])
    return {"plan": str(Crew(agents=[c, p, o], tasks=[t1, t2, t3]).kickoff())}
