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
from .tools import generate_followup_questions, score_pet_match, search_mutual_aid_tasks, recall_adoption_experience, pet_health_knowledge_search
from src.web.services.adoption_contract import (
    CONTRACT_VERSION,
    normalize_confidence,
    validate_contract_list,
)

# ==========================================
# 1. 环境与模型配置 (混合模型分流架构)
# ==========================================

from dotenv import load_dotenv
load_dotenv()

# --- 1.1 厂商凭证分离 ---
# DeepSeek 凭据
DS_KEY = os.getenv("DEEPSEEK_API_KEY")
DS_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# Qwen (阿里云) 凭据
QWEN_KEY = os.getenv("QWEN_API_KEY")
QWEN_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# --- 1.2 功能分流逻辑 ---
def create_llm_instance(feature_name: str):
    """根据功能名创建对应的 LLM 实例（DeepSeek 或 Qwen）"""
    # 获取配置，例如：FEATURE_ADOPTION_PROVIDER=DEEPSEEK
    provider = os.getenv(f"FEATURE_{feature_name.upper()}_PROVIDER", "DEEPSEEK")
    model = os.getenv(f"FEATURE_{feature_name.upper()}_MODEL")
    
    if provider.upper() == "QWEN":
        return LLM(
            model=model or "qwen-plus",
            api_key=QWEN_KEY,
            base_url=QWEN_URL,
            temperature=0.3
        )
    else:
        # 默认使用 DeepSeek
        return LLM(
            model=model or "openai/deepseek-chat",
            api_key=DS_KEY,
            base_url=DS_URL,
            temperature=0.3
        )

# 1.3 为不同功能初始化对应的 LLM
# 推荐：评估用 DeepSeek (强逻辑)，聊天用 Qwen (强文学性)
adoption_llm = create_llm_instance("ADOPTION") 
chat_llm     = create_llm_instance("CHAT")
common_llm   = create_llm_instance("COMMON")

# 保持兼容性别名
llm = common_llm
crewai_llm = common_llm

# ==========================================
# 2. 辅助工具函数 (略)
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


def _build_agent_contract(
    agent_name: str,
    *,
    score: int = 0,
    recommendation: str = "publisher_review",
    evidence: Optional[List[str]] = None,
    risk_tags: Optional[List[str]] = None,
    missing_fields: Optional[List[str]] = None,
    confidence: float = 0.72,
    dimension_scores: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return validate_contract_list([{
        "agent_name": agent_name,
        "dimension_scores": dimension_scores or {},
        "risk_tags": _merge_unique([], risk_tags or []),
        "missing_fields": _merge_unique([], missing_fields or []),
        "confidence": normalize_confidence(confidence),
        "recommendation": recommendation,
        "evidence": _merge_unique([], evidence or []),
        "score": max(0, min(100, int(score))),
    }], fallback_name_prefix=agent_name)[0]


def _build_adoption_result_from_raw(raw_text: str, latency: float, target_species: str, publisher_preferences: Optional[dict]) -> dict:
    structured = _extract_json_payload(raw_text)
    score = 65
    if structured.get("readiness_score") is not None:
        try:
            score = int(float(structured.get("readiness_score")))
        except Exception:
            score = 65
    else:
        for pattern in [r'readiness[_\s]*score[：:\s]*(\d+)', r'评分[：:\s]*(\d+)', r'分数[：:\s]*(\d+)', r'(\d+)\s*/\s*100']:
            matched = re.search(pattern, raw_text, re.IGNORECASE)
            if matched:
                score = int(matched.group(1))
                break

    decision = str(structured.get("decision") or "").lower()
    if not decision:
        lowered = raw_text.lower()
        if any(k in lowered for k in ["驳回", "reject", "拒绝"]):
            decision = "reject"
        elif any(k in lowered for k in ["审核", "review", "人工"]):
            decision = "review_required"
        elif score < 50:
            decision = "reject"
        elif score < 75:
            decision = "review_required"
        else:
            decision = "pass"

    risk_level = str(structured.get("risk_level") or ("Low" if score > 80 else ("High" if score < 50 else "Medium")))
    confidence_level = normalize_confidence(structured.get("confidence") or structured.get("confidence_level") or 0.74)
    recommendations = _merge_unique(["AI 已复盘历史记忆。"], structured.get("recommendations"))
    followup_questions = _merge_unique([], structured.get("followup_questions"), limit=4)
    conflict_notes = _merge_unique([], structured.get("conflict_notes"), limit=4)

    risk_factors = []
    for factor in structured.get("risk_factors") or []:
        if isinstance(factor, dict):
            risk_factors.append(factor)

    structured_outputs = validate_contract_list([
        _build_agent_contract(
            "MemoryRecallAgent",
            score=min(100, score + 3),
            recommendation="publisher_review",
            evidence=["已将历史案例和回访信息纳入本次推理上下文。"],
            risk_tags=["memory_referenced"],
            confidence=0.76,
        ),
        _build_agent_contract(
            "PreferenceMatchAgent",
            score=score,
            recommendation="followup" if followup_questions else ("manual_review" if decision == "review_required" else "publisher_review"),
            evidence=[f"已结合 {target_species} 物种特征与发布者偏好进行适配评估。"],
            risk_tags=[risk_level.lower()],
            missing_fields=followup_questions,
            confidence=confidence_level,
        ),
        _build_agent_contract(
            "ConsensusCoordinatorAgent",
            score=score,
            recommendation="reject_candidate" if decision == "reject" else ("manual_review" if decision == "review_required" else "publisher_review"),
            evidence=[structured.get("summary") or f"终审裁决已生成，耗时 {latency}s。"],
            risk_tags=[factor.get("dimension") or factor.get("description") or "" for factor in risk_factors],
            missing_fields=followup_questions,
            confidence=confidence_level,
        ),
    ], fallback_name_prefix="AdoptionAgent")

    return {
        "readiness_score": score,
        "success_probability": round(float(structured.get("success_probability") or (score / 100 * 0.95)), 2),
        "decision": decision,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "recommendations": recommendations,
        "followup_questions": followup_questions,
        "conflict_notes": conflict_notes,
        "confidence_level": confidence_level,
        "structured_agent_contracts": structured_outputs,
        "output_contract_version": CONTRACT_VERSION,
        "final_summary": (
            f"## 资质评估报告 v3.9\n"
            f"**决策：{decision} (评分：{score}/100)**\n"
            f"**耗时：{latency}s**\n\n"
            f"### 裁决书\n{raw_text}"
        ),
    }

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


def _looks_like_knowledge_miss(text: str) -> bool:
    miss_markers = [
        "未检索到匹配结果",
        "知识库尚未初始化",
        "暂无高度相关",
        "知识库为空",
        "基础知识库",
        "建议由医疗 agent",
        "检索失败",
    ]
    lowered = (text or "").lower()
    return any(marker in (text or "") for marker in miss_markers) or "无匹配" in lowered


def _run_llm_knowledge_fallback(user_query: str, retrieval_hint: str = "") -> str:
    fallback_agent = Agent(
        role='宠物百科兜底顾问',
        goal='在知识库未命中时，基于通用宠物知识给出谨慎、友好的补充回答。',
        backstory='你擅长在缺少知识库命中时提供清晰的常识型解释，并主动提示不确定性与风险边界。',
        llm=common_llm,
        verbose=True,
        allow_delegation=False,
    )
    task = Task(
        description=(
            f'用户问题："{user_query}"\n'
            f'检索情况：{retrieval_hint or "知识库未命中或暂不可用。"}\n'
            '请直接输出简洁回答，并遵守：\n'
            '1. 开头明确说明“以下为 AI 通用知识补充，非知识库命中结果”。\n'
            '2. 不要伪造来源，不要说自己查到了知识库里不存在的内容。\n'
            '3. 优先给出可执行建议；若涉及疾病、急性风险、用药或持续异常，提醒尽快咨询兽医。\n'
            '4. 语气自然，不要只回复“无法回答”。'
        ),
        expected_output='一段简洁、可直接展示给用户的回答。',
        agent=fallback_agent,
    )
    return str(Crew(agents=[fallback_agent], tasks=[task]).kickoff())

# ==========================================
# 3. 核心运行工作流 (语音、访谈与匹配)
# ==========================================

async def analyze_user_portrait(user_id: int, bio: str, preference_text: str = "") -> Dict[str, Any]:
    """
    用户画像提取专家：从用户自我介绍和偏好描述中自动提取结构化推荐特征。
    用于冷启动：将非结构化文本转换为推荐系统可用的画像。
    """
    portrait_agent = Agent(
        role="资深领养资格分析师",
        goal="从用户的文字描述中，精准推断其生活方式、住房条件、经济基础和养宠经验。",
        backstory="你擅长通过语义分析识别隐性特征。例如，提到'带它在院子跑'暗示有院子；提到'加班晚'暗示可用时间少。你的输出将直接驱动宠物匹配算法。",
        llm=common_llm,
        verbose=True,
        allow_delegation=False,
    )
    
    task = Task(
        description=(
            f"深度分析以下领养人信息：\n"
            f"自我介绍：{bio}\n"
            f"偏好补充：{preference_text}\n\n"
            "请输出严格 JSON 对象，包含以下字段：\n"
            "1. housing_type: '公寓', '别墅', '平房'\n"
            "2. has_yard: 1 (是) / 0 (否)\n"
            "3. experience_level: 0 (新手), 1 (有经验), 2 (专家)\n"
            "4. available_time: 每日可投入小时数 (数字)\n"
            "5. budget_level: '低', '中', '高'\n"
            "6. rental_status: '自购', '租房'\n"
            "7. has_children: 1 / 0\n"
            "8. has_other_pets: 1 / 0\n"
            "9. preferred_pet_type: '猫', '狗', '异宠'\n"
            "10. preferred_size: '小型', '中型', '大型'\n"
            "11. allergy_info: 过敏情况描述"
        ),
        expected_output="严格的 JSON 对象。",
        agent=portrait_agent,
    )
    
    try:
        raw = await asyncio.to_thread(lambda: str(Crew(agents=[portrait_agent], tasks=[task]).kickoff()))
        parsed = _extract_json_payload(raw)
        return parsed
    except Exception as e:
        logger.error(f"用户画像提取失败: {str(e)}")
        return {}

async def analyze_pet_features(pet_name: str, pet_species: str, description: str) -> Dict[str, Any]:
    """
    宠物属性提取专家：从描述文本中自动提取结构化推荐特征。
    用于对齐数据库字段：pet_features & pet_requirements
    """
    extractor_agent = Agent(
        role="资深宠物行为学分析师",
        goal="从感性描述中识别宠物的基础属性、健康状态及深层行为模式。",
        backstory="你是一名具备临床兽医背景的行为学专家，擅长从字里行间捕捉宠物的疫苗情况、排泄习惯、社交兼容性及潜在行为风险。",
        llm=common_llm,
        verbose=True,
        allow_delegation=False,
    )
    
    task = Task(
        description=(
            f"深度分析以下宠物信息：\n"
            f"名称：{pet_name}\n"
            f"物种：{pet_species}\n"
            f"描述：{description}\n\n"
            "请输出严格 JSON 对象，包含以下字段：\n"
            "1. age_stage: '幼年', '成年', '老年'\n"
            "2. size_level: '小型', '中型', '大型'\n"
            "3. activity_level: '低', '中', '高'\n"
            "4. care_difficulty: '容易', '中等', '困难'\n"
            "5. good_with_children: 1 / 0\n"
            "6. good_with_other_pets: 1 / 0\n"
            "7. companionship_need: '低', '中', '高'\n"
            "8. budget_need_level: '低', '中', '高'\n"
            "9. sterilized: 1 / 0\n"
            "10. temperament_tags: 性格标签字符串(逗号分隔)\n"
            "11. allow_beginner: 1 / 0 (是否适合新手)\n"
            "12. min_companion_hours: 最低陪伴时长要求 (小时)\n"
            "13. required_housing_type: '公寓', '别墅', '不限'"
        ),
        expected_output="严格的 JSON 对象。",
        agent=extractor_agent,
    )
    
    try:
        raw = await asyncio.to_thread(lambda: str(Crew(agents=[extractor_agent], tasks=[task]).kickoff()))
        parsed = _extract_json_payload(raw)
        return parsed
    except Exception as e:
        logger.error(f"宠物特征提取失败: {str(e)}")
        return {
            "age_stage": "成年", "size_level": "中型", "activity_level": "中",
            "care_difficulty": "容易", "good_with_children": 1, "good_with_other_pets": 1,
            "companionship_need": "中", "budget_need_level": "中", "sterilized": 0,
            "temperament_tags": "温顺", "allow_beginner": 1, "min_companion_hours": 2.0,
            "required_housing_type": "不限"
        }

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
        llm=common_llm,
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
    persona_agent = get_pet_persona_agent(chat_llm, pet_name, pet_species, pet_desc)
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
    p, a = get_pet_expert_agent(common_llm), get_audit_expert_agent(common_llm)
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
        return {
            "readiness_score": 0,
            "success_probability": 0.0,
            "decision": "reject",
            "risk_level": "High",
            "risk_factors": [],
            "recommendations": ["解决硬拦截后重试"],
            "followup_questions": [],
            "conflict_notes": [],
            "confidence_level": 0.98,
            "structured_agent_contracts": validate_contract_list([
                _build_agent_contract(
                    "RulePrescreenAgent",
                    score=0,
                    recommendation="reject_candidate",
                    evidence=[prescreen["prescreen_summary"]],
                    risk_tags=["hard_block"],
                    confidence=0.98,
                )
            ], fallback_name_prefix="AdoptionAgent"),
            "output_contract_version": CONTRACT_VERSION,
            "final_summary": f"## 拦截\n原因：{prescreen['prescreen_summary']}",
        }
    
    e_agent, p_agent, a_agent, c_agent, ch_agent = get_encyclopedia_agent(adoption_llm), get_adoption_profiler_agent(adoption_llm), get_audit_expert_agent(adoption_llm), get_consensus_coordinator_agent(adoption_llm), get_cohabitation_risk_agent(adoption_llm)
    h_expert = Agent(role='历史复盘专家', goal='召回相似案例。', backstory='管理长期记忆。', llm=adoption_llm, tools=[recall_adoption_experience], verbose=True, allow_delegation=False)
    
    t_recall = Task(description=f'检索画像相似反馈。可参考记忆上下文：{memory_context}', expected_output='复盘报告。', agent=h_expert, async_execution=True)
    t_ency = Task(description=f'提取【{target_species}】基准。可参考知识上下文：{knowledge_context}', expected_output='JSON。', agent=e_agent, async_execution=True)
    t_cohab = Task(description=f'评估环境风险。申请人信息：{applicant_info}\n住房类型：{housing_type}\n原住宠物：{existing_pets}', expected_output='报告。', agent=ch_agent, context=[t_ency], async_execution=True)
    t_prop = Task(description=f'提出适配提议。申请理由：{application_reason}\n发布者偏好：{json.dumps(publisher_preferences or {}, ensure_ascii=False)}\n知识上下文：{knowledge_context}\n记忆上下文：{memory_context}', expected_output='提议书。', agent=p_agent, context=[t_ency, t_recall])
    t_audit = Task(description='审计质疑。', expected_output='质疑报告。', agent=a_agent, context=[t_prop, t_recall])
    t_cons = Task(
        description=(
            "终审裁决。请输出严格 JSON 对象，不要输出额外说明。"
            "字段包含：readiness_score, decision, risk_level, confidence, "
            "risk_factors(数组，元素含 dimension/description/severity), "
            "recommendations(数组), followup_questions(数组), conflict_notes(数组), summary。"
        ),
        expected_output='严格 JSON 对象。',
        agent=c_agent,
        context=[t_prop, t_audit, t_cohab],
    )
    
    try:
        res = str(Crew(agents=[h_expert, e_agent, p_agent, a_agent, c_agent, ch_agent], tasks=[t_recall, t_ency, t_cohab, t_prop, t_audit, t_cons], process=Process.hierarchical, manager_llm=adoption_llm, memory=True).kickoff())
        latency = round(time.time() - start_time, 2)
    except: res, latency = "评估中断", 0
    
    result = _build_adoption_result_from_raw(res, latency, target_species, publisher_preferences)
    result["baseline_report"] = str(prescreen.get("prescreen_summary") or "")
    return result

# ─────────────────────────────────────────────────────────────

def run_knowledge_expert(user_query: str) -> str:
    r = Agent(role='知识检索员', goal='优先从宠物知识库中检索相关内容。', backstory='擅长提炼用户问题中的核心关键词并检索知识库。', llm=common_llm, tools=[pet_health_knowledge_search], verbose=True, allow_delegation=False)
    a = Agent(role='百科顾问', goal='基于检索结果组织清晰回答。', backstory='资深宠物养护顾问，能够区分知识库命中与模型常识补充。', llm=common_llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(
        description=f'针对用户问题“{user_query}”调用 pet_health_knowledge_search 检索相关内容；若没有命中也要如实返回。',
        expected_output='检索摘要。',
        agent=r
    )
    t2 = Task(
        description=(
            '根据检索结果生成最终回答。\n'
            '如果检索结果明确表示未命中、库未初始化、检索失败或只有弱相关内容，'
            '不要报错，也不要只回复“没有结果”；请改为给出“AI 通用知识补充”式回答，'
            '并主动提示这不是知识库命中结果。若问题涉及医疗风险，请加入尽快咨询兽医的提醒。'
        ),
        expected_output='Markdown。',
        agent=a,
        context=[t1]
    )
    try:
        result = str(Crew(agents=[r, a], tasks=[t1, t2]).kickoff())
        if _looks_like_knowledge_miss(result):
            return _run_llm_knowledge_fallback(user_query, result)
        return result
    except Exception as e:
        logger.exception("run_knowledge_expert failed")
        return _run_llm_knowledge_fallback(user_query, str(e))

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
    c = get_nutrition_expert_agent(common_llm)
    p = get_nutrition_planner_agent(common_llm)
    o = get_nutrition_optimizer_agent(common_llm)
    t1 = Task(description='计算。', expected_output='数值。', agent=c)
    t2 = Task(description='规划。', expected_output='Markdown。', agent=p, context=[t1])
    t3 = Task(description='评审。', expected_output='报告。', agent=o, context=[t2])
    res = Crew(agents=[c, p, o], tasks=[t1, t2, t3]).kickoff()
    return {'plan': _parse_plan_from_tool_output(str(res), profile), 'explanation_markdown': str(res)}

def run_nutrition_replan(old_plan: dict, feedback: dict, species: str, history_context: str = '') -> str:
    p, o = get_nutrition_planner_agent(common_llm), get_nutrition_optimizer_agent(common_llm)
    t1 = Task(description='再规划。', expected_output='方案。', agent=p)
    t2 = Task(description='评审反馈。', expected_output='报告。', agent=o, context=[t1])
    return str(Crew(agents=[p, o], tasks=[t1, t2]).kickoff())

def run_match_followup(user_query: str) -> list:
    n = Agent(role='需求分析师', goal='生成追问。', backstory='分析需求。', llm=common_llm, tools=[generate_followup_questions], verbose=True, allow_delegation=False)
    task = Task(description=f'分析需求："{user_query}"。', expected_output='JSON追问。', agent=n)
    try:
        raw = str(Crew(agents=[n], tasks=[task]).kickoff())
        return json.loads(re.search(r'\[[\s\S]*\]', raw).group())[:3]
    except: return [{"key": "activity", "question": "活泼还是安静？", "options": ["活泼", "安静"]}]

def run_smart_match(user_query: str, pet_list: list, followup_answers: dict | None = None) -> list:
    s = Agent(role='评分员', goal='调用工具。', backstory='数据专员。', llm=common_llm, tools=[score_pet_match], verbose=True, allow_delegation=False)
    a = Agent(role='顾问', goal='生成理由。', backstory='资深顾问。', llm=common_llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(description='评分。', expected_output='JSON。', agent=s)
    t2 = Task(description='理由。', expected_output='推荐。', agent=a, context=[t1])
    try:
        raw = str(Crew(agents=[s, a], tasks=[t1, t2]).kickoff())
        return json.loads(re.search(r'\[[\s\S]*\]', raw).group())[:5]
    except: return [{"id": 1, "fit_score": 80, "reason": "推荐"}]

def run_mutual_aid_match(user_query: str) -> str:
    a, m = Agent(role='解析员', goal='检索。', backstory='分析员。', llm=common_llm, tools=[search_mutual_aid_tasks], verbose=True, allow_delegation=False), Agent(role='专家', goal='生成。', backstory='推荐专家。', llm=common_llm, tools=[], verbose=True, allow_delegation=False)
    t1 = Task(description=f'解析："{user_query}"。', expected_output='摘要。', agent=a)
    t2 = Task(description='生成报告。', expected_output='Markdown。', agent=m, context=[t1])
    return str(Crew(agents=[a, m], tasks=[t1, t2]).kickoff())
