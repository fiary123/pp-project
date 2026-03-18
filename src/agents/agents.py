# 多智能体 CrewAI 核心逻辑
import os
import json
import logging
import chromadb
import asyncio
import edge_tts
import base64
from io import BytesIO

logger = logging.getLogger(__name__)
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_openai import ChatOpenAI # 修改：使用 OpenAI 适配器

# 导入专项 Agent 构造函数
from .audit_expert import get_audit_expert_agent
from .medical_expert import get_medical_expert_agent
from .navigator import get_navigator_agent
from .pet_expert import get_pet_expert_agent
from .pet_persona import get_pet_persona_agent
from .nutrition_expert import get_nutrition_expert_agent
from .nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from .adoption_profiler import get_encyclopedia_agent, get_adoption_profiler_agent, get_cohabitation_risk_agent

# ==========================================
# 1. 环境与模型配置 (改为 OpenAI/DeepSeek 兼容模式)
# ==========================================

# 从环境变量读取（在项目根目录 .env 文件中配置）
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")

# 初始化通用 LLM 驱动
llm = ChatOpenAI(
    model="deepseek-chat", 
    openai_api_key=OPENAI_API_KEY,
    openai_api_base=OPENAI_BASE_URL,
    temperature=0.3
)

# 连接本地向量库
try:
    from src.database.db_config import CHROMA_DB_PATH
except ImportError:
    from ..database.db_config import CHROMA_DB_PATH

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
knowledge_collection = chroma_client.get_or_create_collection(name="pet_knowledge")

# ==========================================
# 2. 核心运行工作流 (升级版 Edge-TTS 语音对话)
# ==========================================

async def generate_edge_voice(text: str, pet_species: str):
    """异步生成 Edge-TTS 语音字节流"""
    # 动态选择音色：猫咪/小型犬用晓伊(童声)，大型犬用云希(少年)，其他用晓晓
    voice = "zh-CN-XiaoyiNeural" # 默认萌萌童声
    if "狗" in pet_species or "犬" in pet_species:
        voice = "zh-CN-YunxiNeural"
    elif "猫" in pet_species:
        voice = "zh-CN-XiaoxiaoNeural"
    
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

def run_pet_chat(user_msg: str, pet_name: str, pet_species: str, pet_desc: str):
    """
    【新功能】宠物拟人化聊天 + 拟人化音色生成
    """
    persona_agent = get_pet_persona_agent(llm, pet_name, pet_species, pet_desc)
    
    task = Task(
        description=f'用户对你说："{user_msg}"。请作为这只宠物进行回复。',
        expected_output='一段简短、软萌的宠物回复文字。',
        agent=persona_agent
    )
    
    crew = Crew(agents=[persona_agent], tasks=[task])
    response_text = str(crew.kickoff())
    
    # 驱动 Edge-TTS 生成语音 (处理异步)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(generate_edge_voice(response_text, pet_species))
        loop.close()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        return response_text, audio_base64
    except Exception as e:
        logger.warning(f"Edge-TTS 语音生成失败: {e}")
        return response_text, None

def run_pet_crew(user_message: str) -> str:
    """运行领养匹配工作流"""
    pet_expert = get_pet_expert_agent(llm)
    task = Task(description=f'匹配需求："{user_message}"', expected_output='推荐报告', agent=pet_expert)
    crew = Crew(agents=[pet_expert], tasks=[task])
    return str(crew.kickoff())

def run_audit_task(applicant_info: str, pet_info: str) -> str:
    """运行合规性审计"""
    audit_expert = get_audit_expert_agent(llm)
    task = Task(description=f'审计：{applicant_info} 领养 {pet_info}', expected_output='深度审计报告', agent=audit_expert)
    crew = Crew(agents=[audit_expert], tasks=[task])
    return str(crew.kickoff())

def run_knowledge_expert(user_query: str) -> str:
    """运行百科专家"""
    # ... (保持原有逻辑)
    fact_finder = Agent(role='百科百事通', goal='提供建议', llm=llm)
    task = Task(description=f'回答：{user_query}', expected_output='养宠建议', agent=fact_finder)
    return str(Crew(agents=[fact_finder], tasks=[task]).kickoff())


def run_nutrition_expert(profile: dict) -> dict:
    """运行营养喂养专家并返回结构化建议。"""
    plan = build_nutrition_plan(
        species=profile.get('species', 'cat'),
        age_months=int(profile.get('age_months', 12)),
        weight_kg=float(profile.get('weight_kg', 4.0)),
        neutered=bool(profile.get('neutered', False)),
        activity_level=profile.get('activity_level', 'medium'),
        goal=profile.get('goal', 'maintain'),
        food_kcal_per_100g=float(profile.get('food_kcal_per_100g', 360)),
        symptoms=profile.get('symptoms', [])
    )
    markdown = render_nutrition_markdown(profile.get('species', 'cat'), plan)

    # 保留多智能体扩展位：可切换为 Crew 调度输出
    _ = get_nutrition_expert_agent(llm)
    return {'plan': plan, 'explanation_markdown': markdown}


def run_triage_expert(symptom: str, location: str | None = None) -> str:
    """运行医疗分诊专家，必要时可扩展到导航专家联动。"""
    medical_expert = get_medical_expert_agent(llm)
    task = Task(
        description=f'请对以下症状做分诊并给出风险等级：{symptom}。位置信息：{location or "未知"}',
        expected_output='结构化分诊报告（含风险等级与是否紧急就医）。',
        agent=medical_expert
    )
    crew = Crew(agents=[medical_expert], tasks=[task])
    return str(crew.kickoff())


def run_adoption_assessment(
    applicant_info: str,
    target_species: str,
    target_pet_name: str,
    monthly_budget: float = 0,
    daily_companion_hours: float = 0,
    has_pet_experience: bool = False,
    housing_type: str = "apartment",
    application_reason: str = "",
    existing_pets: str = ""
) -> dict:
    """
    领养资质评估：五层架构多智能体协同流程

    L2 规则预筛  → 识别硬约束与明显风险，输出惩罚分
    L3 LLM 画像  → 语义动机分析 + 四维评分 + 矛盾识别
    L4 多专家协同 → 百科Baseline + 共处风险评估
    L5 结构化输出 → 符合需求文档的完整评估结果

    返回 dict 包含：readiness_score, success_probability, confidence_level,
                    risk_level, decision, need_manual_review,
                    risk_factors, recommendations, review_note,
                    baseline_report, profile_report, cohabitation_report,
                    final_summary
    """
    from .adoption_profiler import (
        rule_engine_prescreen,
        get_encyclopedia_agent,
        get_adoption_profiler_agent,
        get_cohabitation_risk_agent,
    )

    # ── L2：规则约束与预筛 ──────────────────────────────────────────
    prescreen = rule_engine_prescreen(
        target_species=target_species,
        monthly_budget=monthly_budget,
        daily_companion_hours=daily_companion_hours,
        has_pet_experience=has_pet_experience,
        housing_type=housing_type,
        existing_pets=existing_pets,
        applicant_info=applicant_info,
    )

    # 命中硬约束直接返回，不进入 LLM 层（节省 API 调用）
    if prescreen["hard_block"]:
        risk_factors = [
            {"dimension": "硬约束", "description": flag, "severity": "high"}
            for flag in prescreen["risk_flags"]
        ]
        return {
            "readiness_score": 0,
            "success_probability": 0.0,
            "confidence_level": 0.99,
            "risk_level": "High",
            "decision": "reject",
            "need_manual_review": False,
            "risk_factors": risk_factors,
            "recommendations": ["请先解决住房条件限制（如与房东沟通或更换住所）后重新申请。"],
            "review_note": "命中硬约束（住房禁止养宠），系统建议直接驳回，无需人工复核。",
            "baseline_report": "因命中硬约束，未执行品种分析。",
            "profile_report": "因命中硬约束，未执行画像分析。",
            "cohabitation_report": "因命中硬约束，未执行共处风险评估。",
            "final_summary": (
                f"## 领养资质评估报告\n\n"
                f"**决策结果**：建议驳回\n"
                f"**原因**：{prescreen['prescreen_summary']}"
            ),
        }

    # ── L4：多智能体协同决策 ────────────────────────────────────────
    encyclopedia_agent   = get_encyclopedia_agent(llm)
    profiler_agent       = get_adoption_profiler_agent(llm)
    cohabitation_agent   = get_cohabitation_risk_agent(llm)

    # Task 1: 百科专家提取品种 Baseline（L4 首节点）
    task_encyclopedia = Task(
        description=(
            f'请从知识库中检索并提取【{target_species}】（目标宠物名称：{target_pet_name}）的完整养护标准 Baseline。\n'
            f'重点提取：空间需求、运动量等级（含每日建议时长）、陪伴依赖性、'
            f'月均养护成本区间、新手友好度（含理由）、特殊健康风险与行为特点。\n'
            f'如知识库无结果，请基于专业知识估算并注明。'
        ),
        expected_output=(
            '结构化 JSON Baseline，包含字段：'
            'space_requirement, exercise_level, companionship_need, '
            'monthly_cost_range, beginner_friendly, special_notes。'
        ),
        agent=encyclopedia_agent
    )

    # Task 2: 画像专家 - L3 LLM 语义推理核心（依赖 Task 1）
    budget_text = f"月均养宠预算：{monthly_budget} 元/月" if monthly_budget > 0 else "预算未填写"
    hours_text  = f"工作日每日可陪伴时长：{daily_companion_hours} 小时" if daily_companion_hours > 0 else "陪伴时长未填写"
    reason_text = f"\n【申请理由（自由文本）】：{application_reason}" if application_reason.strip() else ""

    task_profiler = Task(
        description=(
            f'你已获得品种养护 Baseline（来自百科专家），现在请对以下申请人进行全维度画像分析：\n\n'
            f'【申请人基本情况】：{applicant_info}\n'
            f'【量化条件】：{budget_text}；{hours_text}；'
            f'养宠经验：{"有" if has_pet_experience else "无"}；住房类型：{housing_type}'
            f'{reason_text}\n\n'
            f'【规则预筛结果（已识别的硬性风险，请在分析中引用）】：\n{prescreen["prescreen_summary"]}\n\n'
            f'请按以下步骤完成分析：\n'
            f'1. 四维评分（居住/时间/经验/经济，各25分，结合 Baseline 给出分数和绿/黄/红灯）\n'
            f'2. 语义动机分析（判断是否冲动型领养、是否存在表达矛盾、隐性风险识别）\n'
            f'3. 计算 readiness_score = 四维总分 - {prescreen["penalty_score"]}（规则惩罚分）\n'
            f'4. 计算 success_probability（0-1，结合动机稳定性系数）\n'
            f'5. 列出所有风险因子（含维度和严重程度）\n'
            f'6. 给出 decision（pass/conditional_pass/review_required/reject）\n'
            f'7. 生成针对性的个性化建议（至少3条，具体可操作）\n'
            f'8. 给管理员写审核备注（review_note）'
        ),
        expected_output=(
            '结构化 Markdown 画像报告，包含：四维评分表格、动机分析段落、'
            'readiness_score 和 success_probability 数值、风险因子列表、'
            'decision 结论、recommendations 列表（至少3条）、review_note。'
        ),
        agent=profiler_agent,
        context=[task_encyclopedia]
    )

    # Task 3: 共处环境风险评估（依赖 Task 1）
    existing_pets_desc = existing_pets.strip() if existing_pets.strip() else "无原住宠物"
    task_cohabitation = Task(
        description=(
            f'基于品种 Baseline，评估以下家庭环境接纳新宠物的综合风险：\n\n'
            f'【居住环境描述】：{applicant_info}\n'
            f'【原住宠物情况】：{existing_pets_desc}\n'
            f'【新领养宠物】：{target_species}（{target_pet_name}）\n\n'
            f'请逐项评估：\n'
            f'1. 疾病传播风险（含建议隔离期天数和检疫清单）\n'
            f'2. 行为冲突风险（物种/年龄/性格兼容性）\n'
            f'3. 居住环境物理安全隐患排查（高层坠落/有毒植物/逃跑风险等）\n'
            f'4. 给出进家前的具体准备 Checklist'
        ),
        expected_output=(
            '结构化 Markdown 报告，包含：疾病风险（含隔离天数）、行为冲突、'
            '环境安全隐患（✅/⚠️/🚨 标注）、进家准备 Checklist。'
        ),
        agent=cohabitation_agent,
        context=[task_encyclopedia]
    )

    # 串联执行
    crew = Crew(
        agents=[encyclopedia_agent, profiler_agent, cohabitation_agent],
        tasks=[task_encyclopedia, task_profiler, task_cohabitation],
        process=Process.sequential,
        verbose=True
    )
    crew_result = crew.kickoff()

    # ── L5：解析输出，构建结构化结果 ────────────────────────────────
    task_outputs = crew_result.tasks_output if hasattr(crew_result, 'tasks_output') else []
    baseline_report     = str(task_outputs[0]) if len(task_outputs) > 0 else "品种基准数据获取失败"
    profile_report      = str(task_outputs[1]) if len(task_outputs) > 1 else "画像分析失败"
    cohabitation_report = str(task_outputs[2]) if len(task_outputs) > 2 else "共处风险评估失败"

    # 从画像报告中解析关键指标（LLM 输出文本提取）
    profile_lower = profile_report.lower()

    # 风险等级
    if "high" in profile_lower or "高风险" in profile_report:
        risk_level = "High"
    elif "low" in profile_lower and "风险" in profile_report and "高风险" not in profile_report:
        risk_level = "Low"
    else:
        risk_level = "Medium"

    # 决策
    if "reject" in profile_lower or "建议驳回" in profile_report:
        decision = "reject"
    elif "review_required" in profile_lower or "人工复核" in profile_report or "二次核验" in profile_report:
        decision = "review_required"
    elif "conditional_pass" in profile_lower or "条件通过" in profile_report:
        decision = "conditional_pass"
    else:
        decision = "pass"

    need_manual_review = prescreen["need_manual_review"] or decision in ("review_required", "reject")

    # 从预筛中提取风险因子基础，LLM 报告中的风险由 profile_report 正文承载
    risk_factors = [
        {"dimension": "规则预筛", "description": flag.lstrip("🔴🟡 "), "severity": "high" if "🔴" in flag else "medium"}
        for flag in prescreen["risk_flags"]
    ]

    # 简单数值提取（正则）
    import re
    score_match = re.search(r'readiness[_\s]*score[：:\s]*(\d+)', profile_report, re.IGNORECASE)
    readiness_score = max(0, min(100, int(score_match.group(1)) if score_match else max(0, 60 - prescreen["penalty_score"])))

    prob_match = re.search(r'success[_\s]*probability[：:\s]*(0\.\d+)', profile_report, re.IGNORECASE)
    success_probability = float(prob_match.group(1)) if prob_match else round(readiness_score / 100 * 0.85, 2)

    final_summary = (
        f"## 领养资质综合评估报告\n\n"
        f"| 指标 | 结果 |\n|------|------|\n"
        f"| 目标宠物 | {target_pet_name}（{target_species}） |\n"
        f"| 准备度评分 | {readiness_score} / 100 |\n"
        f"| 成功倾向 | {success_probability:.0%} |\n"
        f"| 综合风险等级 | {risk_level} |\n"
        f"| 系统建议决策 | {decision} |\n"
        f"| 是否需要人工复核 | {'是' if need_manual_review else '否'} |\n\n"
        f"---\n\n"
        f"### 一、品种养护基准（百科专家）\n{baseline_report}\n\n"
        f"### 二、申请人画像匹配分析（画像专家）\n{profile_report}\n\n"
        f"### 三、共处环境风险评估（共处专家）\n{cohabitation_report}"
    )

    return {
        "readiness_score": readiness_score,
        "success_probability": success_probability,
        "confidence_level": 0.95 if len(applicant_info) > 50 else 0.75,
        "risk_level": risk_level,
        "decision": decision,
        "need_manual_review": need_manual_review,
        "risk_factors": risk_factors,
        "recommendations": [],  # 由 profile_report 正文承载，API 层直接返回报告
        "review_note": f"规则预筛惩罚分：{prescreen['penalty_score']}，{prescreen['prescreen_summary'][:100]}",
        "baseline_report": baseline_report,
        "profile_report": profile_report,
        "cohabitation_report": cohabitation_report,
        "final_summary": final_summary,
    }
