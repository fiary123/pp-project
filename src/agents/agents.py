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
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from langchain_openai import ChatOpenAI # 修改：使用 OpenAI 适配器

# 导入专项 Agent 构造函数
from .audit_expert import get_audit_expert_agent
from .medical_expert import get_medical_expert_agent
from .navigator import get_navigator_agent
from .pet_expert import get_pet_expert_agent
from .pet_persona import get_pet_persona_agent
from .nutrition_expert import get_nutrition_expert_agent, get_nutrition_planner_agent, get_nutrition_optimizer_agent
from .nutrition_planner import build_nutrition_plan, render_nutrition_markdown
from .adoption_profiler import get_encyclopedia_agent, get_adoption_profiler_agent, get_cohabitation_risk_agent
from .tools import generate_followup_questions, score_pet_match

# ==========================================
# 1. 环境与模型配置 (改为 OpenAI/DeepSeek 兼容模式)
# ==========================================

# 从环境变量读取（在项目根目录 .env 文件中配置）
from dotenv import load_dotenv
load_dotenv()

_DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
_DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

_QWEN_API_KEY  = os.getenv("QWEN_API_KEY")
_QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── 模型分配策略 ────────────────────────────────────────────────────
# llm      : DeepSeek-Chat  → 所有纯文本 Agent（匹配/营养/评估/知识问答/聊天）
# llm_vision: Qwen-VL-Plus  → 仅分诊模块有图片/视频输入时的 VisionAgent
# 两者均兼容 OpenAI 接口，无需引入额外依赖
# ────────────────────────────────────────────────────────────────────

# 通用文本 LLM（DeepSeek）
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=_DEEPSEEK_API_KEY,
    openai_api_base=_DEEPSEEK_BASE_URL,
    temperature=0.3
)

# 视觉多模态 LLM（Qwen-VL，仅分诊图片分析使用）
llm_vision = ChatOpenAI(
    model="qwen-vl-plus",
    openai_api_key=_QWEN_API_KEY or _DEEPSEEK_API_KEY,  # 未配置时降级，避免启动报错
    openai_api_base=_QWEN_BASE_URL,
    temperature=0.1   # 视觉分析要求准确，温度设低
) if _QWEN_API_KEY else None

# CrewAI 原生 LLM（所有 CrewAI Agent 使用此对象）
# CrewAI 新版不再接受 langchain ChatOpenAI 对象，需使用自己的 LLM 类
crewai_llm = LLM(
    model="openai/deepseek-chat",
    api_key=_DEEPSEEK_API_KEY,
    base_url=_DEEPSEEK_BASE_URL,
    temperature=0.3
)
# 统一使用 CrewAI 原生 LLM，覆盖旧的 langchain llm 引用
llm = crewai_llm

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

def run_pet_chat(user_msg: str, pet_name: str, pet_species: str, pet_desc: str, history: list = None):
    """
    【新功能】宠物拟人化聊天 + 拟人化音色生成
    history: [{"role": "user"/"pet", "content": "..."}, ...]  最近几轮对话
    """
    persona_agent = get_pet_persona_agent(crewai_llm, pet_name, pet_species, pet_desc)

    # 将历史记录格式化为上下文提示
    history_context = ""
    if history:
        lines = []
        for h in history[-6:]:  # 最多取最近6条
            speaker = "主人" if h["role"] == "user" else pet_name
            lines.append(f"{speaker}：{h['content']}")
        history_context = "【之前的对话记录】\n" + "\n".join(lines) + "\n\n"

    task = Task(
        description=f'{history_context}用户对你说："{user_msg}"。请作为这只宠物进行回复。',
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
    """
    宠物匹配工作流：两 Agent 串联 Crew。
    - PetExpert：调用 pet_database_search 工具检索数据库，输出候选宠物列表
    - AuditExpert：对候选结果做合规性预检，过滤明显不合适的选项，输出最终推荐
    两步拆分确保推荐"有库可查 + 有规可依"。
    """
    pet_expert   = get_pet_expert_agent(llm)
    audit_expert = get_audit_expert_agent(llm)

    task_search = Task(
        description=(
            f'用户需求："{user_message}"。\n'
            f'请调用 pet_database_search 工具，将需求转化为检索关键词，查询数据库中待领养宠物，'
            f'输出完整的候选宠物列表（名称、品种、描述）。'
        ),
        expected_output='数据库检索到的候选宠物列表，含名称、品种、描述。',
        agent=pet_expert
    )

    task_audit = Task(
        description=(
            f'基于宠物检索专家提供的候选列表，结合用户需求："{user_message}"，'
            f'对每只候选宠物进行合规性预检（住房适配/时间适配/经验适配），'
            f'过滤明显不合适的选项，最终给出 1-2 个推荐，说明推荐理由和注意事项。'
        ),
        expected_output='Markdown 格式推荐报告，含推荐宠物名称、推荐理由、匹配指数、注意事项。',
        agent=audit_expert,
        context=[task_search]
    )

    crew = Crew(
        agents=[pet_expert, audit_expert],
        tasks=[task_search, task_audit],
        process=Process.sequential,
        verbose=True
    )
    return str(crew.kickoff())


def run_audit_task(applicant_info: str, pet_info: str) -> str:
    """
    领养合规性深度审计：两 Agent 串联 Crew。
    - PetExpert：调用 pet_database_search 工具查询目标宠物的详细信息作为审计依据
    - AuditExpert：基于宠物档案对申请人信息进行四维度深度合规审查
    两步拆分确保审计基于真实宠物档案，而非 LLM 凭空推断。
    """
    pet_expert   = get_pet_expert_agent(llm)
    audit_expert = get_audit_expert_agent(llm)

    task_pet_info = Task(
        description=(
            f'请调用 pet_database_search 工具，查询宠物「{pet_info}」的详细档案信息，'
            f'包括品种特征、活跃度、掉毛情况、描述，作为后续审计的参照基准。'
        ),
        expected_output='目标宠物的详细档案信息（品种/活跃度/描述等）。',
        agent=pet_expert
    )

    task_audit = Task(
        description=(
            f'根据宠物档案信息，对以下申请人进行四维度合规审查：\n\n'
            f'【申请人信息】：{applicant_info}\n\n'
            f'审查维度：\n'
            f'1. 空间品种兼容性：住房面积与宠物空间需求是否匹配\n'
            f'2. 作息陪伴平衡：日程安排与宠物陪伴依赖度是否冲突\n'
            f'3. 经验难度匹配：养宠经验与目标品种饲养难度是否合理\n'
            f'4. 语义真实性：申请描述是否存在矛盾或冲动型迹象\n\n'
            f'输出：审计结论（通过/条件通过/建议驳回）+ 风险点清单 + 改善建议。'
        ),
        expected_output='深度审计报告，含四维评分、审计结论、风险点清单、改善建议。',
        agent=audit_expert,
        context=[task_pet_info]
    )

    crew = Crew(
        agents=[pet_expert, audit_expert],
        tasks=[task_pet_info, task_audit],
        process=Process.sequential,
        verbose=True
    )
    return str(crew.kickoff())

def run_knowledge_expert(user_query: str) -> str:
    """
    知识问答：两 Agent 串联 Crew。
    - KnowledgeRetriever：先用 pet_health_knowledge_search 工具从向量库检索相关知识
    - KnowledgeAdvisor：基于检索结果综合分析，输出结构化建议
    两步拆分确保回答"有据可查"而非凭空生成。
    """
    from .tools import pet_health_knowledge_search

    retriever = Agent(
        role='宠物知识检索员',
        goal='从向量知识库中检索与用户问题最相关的宠物养护知识条目，完整输出检索结果。',
        backstory=(
            '你是知识库的检索专员，擅长将用户问题转化为精准的检索关键词。\n'
            '【工具调用规则】\n'
            '第一步：调用 pet_health_knowledge_search，用问题核心关键词检索。\n'
            '第二步：判断返回内容是否与用户问题直接相关。\n'
            '  - 如果首次结果不相关或返回"未检索到匹配结果"，\n'
            '    必须换一个更简短的关键词重新检索，最多尝试两次。\n'
            '  - 例如：首次用"小猫咪怎么换粮过渡比较好"，无结果则改用"换粮"重试。\n'
            '第三步：将最相关的检索结果完整原文输出，不做任何解读，交给下游专家使用。'
        ),
        llm=llm,
        tools=[pet_health_knowledge_search],
        verbose=True,
        max_iter=4,
        allow_delegation=False
    )

    advisor = Agent(
        role='资深宠物养护顾问',
        goal='基于知识库检索结果，为用户提供专业、易懂、结构清晰的养护建议。',
        backstory=(
            '你是一名资深宠物顾问，擅长将专业知识转化为宠主能理解的实用建议。'
            '你会综合检索员提供的知识原文，结合用户具体问题给出回答。'
            '回答须包含：核心结论、具体操作建议、注意事项，使用 Markdown 格式。'
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=False
    )

    task_retrieve = Task(
        description=f'用户问题："{user_query}"。请调用 pet_health_knowledge_search 工具检索相关知识，输出完整检索结果。',
        expected_output='从知识库检索到的原始知识条目文本（含来源标注）。',
        agent=retriever
    )

    task_advise = Task(
        description=(
            f'根据检索员提供的知识库内容，结合用户问题："{user_query}"，'
            f'输出一份结构化的养护建议报告。必须包含：核心结论、具体操作步骤、特别注意事项。'
        ),
        expected_output='Markdown 格式的专业养护建议，含核心结论、操作步骤、注意事项三部分。',
        agent=advisor,
        context=[task_retrieve]
    )

    crew = Crew(
        agents=[retriever, advisor],
        tasks=[task_retrieve, task_advise],
        process=Process.sequential,
        verbose=True
    )
    return str(crew.kickoff())


def _parse_plan_from_tool_output(tool_output: str, profile: dict) -> dict:
    """
    从 calc_pet_daily_energy 工具文本输出中解析结构化 plan dict。
    工具输出格式：daily_kcal=xxx, daily_food_g=xxx, feedings_per_day=xxx
    解析失败时降级到 build_nutrition_plan()。
    """
    import re
    plan = {}
    try:
        for key in ('daily_kcal', 'daily_food_g', 'feedings_per_day'):
            m = re.search(rf'{key}=(\d+(?:\.\d+)?)', tool_output)
            if m:
                plan[key] = int(float(m.group(1)))
    except Exception:
        pass

    # 若关键字段缺失则降级
    if not all(k in plan for k in ('daily_kcal', 'daily_food_g', 'feedings_per_day')):
        fallback = build_nutrition_plan(
            species=profile.get('species', 'cat'),
            age_months=int(profile.get('age_months', 12)),
            weight_kg=float(profile.get('weight_kg', 4.0)),
            neutered=bool(profile.get('neutered', False)),
            activity_level=profile.get('activity_level', 'medium'),
            goal=profile.get('goal', 'maintain'),
            food_kcal_per_100g=float(profile.get('food_kcal_per_100g', 360)),
            symptoms=profile.get('symptoms', []),
        )
        return fallback

    # 补充 build_nutrition_plan 中的其他字段
    weight_kg = float(profile.get('weight_kg', 4.0))
    feedings  = plan['feedings_per_day']
    per_meal_base = plan['daily_food_g'] // feedings
    per_meal = [per_meal_base] * feedings
    per_meal[-1] += plan['daily_food_g'] - sum(per_meal)

    species_norm = (profile.get('species', 'cat') or 'cat').lower()
    forbidden = ['巧克力', '洋葱', '葡萄', '木糖醇', '酒精', '高盐高油剩饭']
    if species_norm == 'cat':
        forbidden.extend(['狗粮长期替代', '生鱼生肉长期单一喂食'])
    if species_norm == 'dog':
        forbidden.extend(['熟骨头', '夏威夷果'])

    symptoms = profile.get('symptoms', [])
    risk_alerts = ['若持续24小时拒食、反复呕吐或腹泻带血，请立即就医。']
    if symptoms:
        risk_alerts.append(f'已识别到特殊情况：{"、".join(symptoms)}，建议先少量多餐并观察48小时。')

    plan.update({
        'per_meal_g': per_meal,
        'daily_water_ml': f'{round(weight_kg*50)}-{round(weight_kg*60)}',
        'forbidden_foods': forbidden,
        'transition_7days': [
            'D1-D2: 新粮25% + 旧粮75%',
            'D3-D4: 新粮50% + 旧粮50%',
            'D5-D6: 新粮75% + 旧粮25%',
            'D7: 新粮100%',
        ],
        'risk_alerts': risk_alerts,
    })
    return plan


def run_nutrition_expert(profile: dict) -> dict:
    """
    营养方案：3-Agent 顺序流水线 Crew。
    - NutritionCalculator（Agent 1）：调用 calc_pet_daily_energy + pet_food_forbidden_list
      工具，输出原始数值结果。
    - NutritionPlanner（Agent 2）：接收 Agent 1 的 context，撰写完整 Markdown 喂养方案。
    - NutritionOptimizer（Agent 3）：接收 Agent 2 的 context，输出 confidence_level 解读
      和风险注释。
    plan 结构化数据从 Agent 1 工具输出解析，确保数值可溯源，不再调用独立数学函数。
    """
    species   = profile.get('species', 'cat')
    age_months = int(profile.get('age_months', 12))
    weight_kg  = float(profile.get('weight_kg', 4.0))
    neutered   = bool(profile.get('neutered', False))
    activity   = profile.get('activity_level', 'medium')
    goal       = profile.get('goal', 'maintain')
    food_kcal  = float(profile.get('food_kcal_per_100g', 360))
    symptoms   = profile.get('symptoms', [])
    pet_name   = profile.get('pet_name', '宠物')

    # ── Agent 1：NutritionCalculator ────────────────────────────────
    calculator_agent = get_nutrition_expert_agent(llm)

    task_calculate = Task(
        description=(
            f'宠物档案：物种={species}，月龄={age_months}，体重={weight_kg}kg，'
            f'绝育={"是" if neutered else "否"}，活跃度={activity}，目标={goal}，'
            f'症状={symptoms}。\n'
            f'请严格按以下步骤执行：\n'
            f'1. 调用 calc_pet_daily_energy 工具，传入：species="{species}"，'
            f'age_months={age_months}，weight_kg={weight_kg}，neutered={"true" if neutered else "false"}，'
            f'activity_level="{activity}"，goal="{goal}"。\n'
            f'2. 调用 pet_food_forbidden_list 工具，传入 species="{species}"。\n'
            f'3. 将工具返回的所有数值和禁忌清单原文完整输出，不修改任何数字。'
        ),
        expected_output=(
            '工具调用原始结果：包含 daily_kcal、daily_food_g、feedings_per_day 的数值行，'
            '以及禁忌食物列表。'
        ),
        agent=calculator_agent
    )

    # ── Agent 2：NutritionPlanner ────────────────────────────────────
    planner_agent = get_nutrition_planner_agent(llm)

    task_plan = Task(
        description=(
            f'根据计算专员（上一步）提供的工具数值，为宠物「{pet_name}」（{species}）'
            f'生成结构化方案摘要和完整喂养报告。\n'
            f'症状备注：{symptoms if symptoms else "无异常症状"}。\n'
            f'必须引用上游工具计算的原始数值，不得自行推算热量。\n'
            f'按格式要求先输出 JSON 摘要，再输出完整 Markdown 报告。'
        ),
        expected_output=(
            '两部分内容：\n'
            '第一部分：```json 代码块，包含字段：\n'
            '  daily_kcal（整数）、daily_food_g（整数）、feedings_per_day（整数）、\n'
            '  confidence_level（0.0-1.0）、risk_flags（字符串数组）、requires_vet（布尔值）。\n'
            '第二部分：完整 Markdown 喂养报告，含每日热量、喂食量、频次、饮水量、\n'
            '7日换粮计划、禁忌食物清单、风险提示。'
        ),
        agent=planner_agent,
        context=[task_calculate]
    )

    # ── Agent 3：NutritionOptimizer ──────────────────────────────────
    optimizer_agent = get_nutrition_optimizer_agent(llm)

    task_optimize = Task(
        description=(
            f'你已收到 Planner 的输出（含 JSON 摘要和 Markdown 报告）作为 context。\n'
            f'请读取 JSON 中的 confidence_level、risk_flags、requires_vet 字段，进行针对性评审：\n'
            f'1. 审查 confidence_level 是否与 risk_flags 数量和严重程度相符。\n'
            f'2. 检查每条 risk_flag 是否有对应处理建议，若无则补充。\n'
            f'3. 结合症状={symptoms}、月龄={age_months}、活跃度={activity}，\n'
            f'   判断 requires_vet 是否应更正。\n'
            f'4. 提出 1-2 条方案优化建议。\n'
            f'不要重新计算热量数值，只做评审与注释。'
        ),
        expected_output=(
            'Markdown 格式评审报告，含：对 confidence_level 的校正意见（引用 JSON 原值）、\n'
            '各 risk_flag 的处理建议、requires_vet 最终判断及理由、优化建议。'
        ),
        agent=optimizer_agent,
        context=[task_plan]
    )

    crew = Crew(
        agents=[calculator_agent, planner_agent, optimizer_agent],
        tasks=[task_calculate, task_plan, task_optimize],
        process=Process.sequential,
        verbose=True
    )
    crew_result = crew.kickoff()

    # 从 Agent 1 工具输出解析结构化 plan（不再调用独立数学函数）
    task_outputs = crew_result.tasks_output if hasattr(crew_result, 'tasks_output') else []
    calculator_raw = str(task_outputs[0]) if task_outputs else ''
    plan = _parse_plan_from_tool_output(calculator_raw, profile)

    # Agent 2 输出作为主方案 Markdown，Agent 3 的 Optimizer 报告追加到末尾
    planner_md  = str(task_outputs[1]) if len(task_outputs) > 1 else render_nutrition_markdown(species, plan)
    optimizer_md = str(task_outputs[2]) if len(task_outputs) > 2 else ''
    explanation_markdown = planner_md
    if optimizer_md:
        explanation_markdown += f'\n\n---\n\n### NutritionOptimizer 评审报告\n\n{optimizer_md}'

    # 将 Optimizer 的置信度评审摘要写入 plan 供 API 层使用
    plan['confidence_level'] = plan.get('confidence_level', 0.95)
    plan['optimizer_notes'] = optimizer_md[:300] if optimizer_md else ''

    return {'plan': plan, 'explanation_markdown': explanation_markdown}


def run_nutrition_replan(old_plan: dict, feedback: dict, species: str, history_context: str = '') -> str:
    """
    营养再规划：NutritionPlanner → NutritionOptimizer 两 Agent 流水线。
    - NutritionPlanner（Task 1）：将调整后的数值重新组织成 JSON + Markdown 喂养方案。
    - NutritionOptimizer（Task 2）：接收 Planner context + 手动注入的历史趋势记忆，
      基于历史方案变化趋势和本次反馈做闭环评审，输出引用了历史数据的置信度校正报告。
    history_context: 从数据库提取的该宠物历史方案趋势文本（手动记忆注入）。
    """
    weight_change = feedback.get('weight_change', 'stable')
    appetite      = feedback.get('appetite_status', 'normal')
    stool         = feedback.get('stool_status', 'normal')
    activity      = feedback.get('activity_change', 'stable')

    # ── Task 1：NutritionPlanner 将新数值重新整理成方案摘要 ──────────
    planner_agent = get_nutrition_planner_agent(llm)

    task_replan = Task(
        description=(
            f'根据规则引擎调整后的最新方案数值，为宠主生成结构化 JSON 摘要和更新喂养方案：\n'
            f'- 物种：{species}\n'
            f'- 调整后每日热量：{old_plan.get("daily_kcal", "?")} kcal\n'
            f'- 每日喂食量：{old_plan.get("daily_food_g", "?")} g\n'
            f'- 喂食频次：{old_plan.get("feedings_per_day", "?")} 次/天\n'
            f'- 饮水量：{old_plan.get("daily_water_ml", "?")} ml/天\n\n'
            f'宠主本次反馈：体重变化={weight_change}，食欲={appetite}，排便={stool}，活动量={activity}。\n'
            f'按格式要求先输出 JSON 摘要，再输出完整 Markdown 方案。'
        ),
        expected_output=(
            '两部分内容：\n'
            '第一部分：```json 代码块，包含字段：\n'
            '  daily_kcal（整数）、daily_food_g（整数）、feedings_per_day（整数）、\n'
            '  confidence_level（0.0-1.0）、risk_flags（字符串数组）、requires_vet（布尔值）。\n'
            '第二部分：Markdown 格式更新方案，含调整背景说明、最新数值、喂食安排。'
        ),
        agent=planner_agent
    )

    # ── Task 2：NutritionOptimizer 读取 Planner JSON 字段做评审 ──────
    optimizer_agent = get_nutrition_optimizer_agent(llm)

    history_section = (
        f'\n\n【历史方案记忆（最近3次）】\n{history_context}\n'
        f'请结合上述历史趋势判断本次调整方向是否合理（例如：若历史记录显示连续减热量但体重仍增，\n'
        f'说明当前策略效果不佳，需在建议中指出）。\n'
        f'你的报告中必须包含 referenced_history 字段，列出你实际引用了哪些历史记录（如无历史则写"无历史数据"）。'
        if history_context else
        '\n\n【历史方案记忆】：暂无该宠物的历史方案记录，本次为首次再规划。'
    )

    task_optimize = Task(
        description=(
            f'你已收到 Planner 的输出（含 JSON 摘要和 Markdown 方案）作为 context。\n'
            f'请读取 JSON 中的 confidence_level、risk_flags、requires_vet 字段，结合以下数据进行闭环评审：\n\n'
            f'【本次反馈】\n'
            f'- 体重变化：{weight_change}（gain=增重/lose=减重/stable=稳定）\n'
            f'- 食欲状态：{appetite}（good=良好/poor=差/normal=正常）\n'
            f'- 排便质量：{stool}（normal=正常/soft=偏软/diarrhea=腹泻/hard=便秘）\n'
            f'- 活动量变化：{activity}（increase=增加/decrease=减少/stable=稳定）\n'
            f'{history_section}\n'
            f'评审要点：\n'
            f'1. confidence_level 是否与反馈严重程度 + 历史趋势相符。\n'
            f'2. risk_flags 是否已覆盖本次反馈暴露的新风险，若未覆盖则补充。\n'
            f'3. requires_vet：排便异常（soft/diarrhea）或持续体重下降时必须为 true。\n'
            f'4. 给出 2-3 条结合历史趋势的具体改善建议。'
        ),
        expected_output=(
            'Markdown 格式评审报告，包含以下部分：\n'
            '1. 对 Planner JSON 字段的校正意见（引用原值）\n'
            '2. 新增风险点（若有）\n'
            '3. requires_vet 最终判断及理由\n'
            '4. referenced_history：列出实际引用的历史记录条目（无则写"无历史数据"）\n'
            '5. 结合历史趋势的改善建议（2-3条）'
        ),
        agent=optimizer_agent,
        context=[task_replan]
    )

    crew = Crew(
        agents=[planner_agent, optimizer_agent],
        tasks=[task_replan, task_optimize],
        process=Process.sequential,
        verbose=True
    )
    crew_result = crew.kickoff()

    task_outputs = crew_result.tasks_output if hasattr(crew_result, 'tasks_output') else []
    planner_md  = str(task_outputs[0]) if task_outputs else ''
    optimizer_md = str(task_outputs[1]) if len(task_outputs) > 1 else str(crew_result)

    return f'{planner_md}\n\n---\n\n### NutritionOptimizer 评审\n\n{optimizer_md}'


def _analyze_image_with_vision(image_bytes: bytes, symptom_text: str) -> str:
    """
    用 Qwen-VL（llm_vision）分析宠物图片，返回视觉观察描述。
    若 llm_vision 未配置（QWEN_API_KEY 未设置），返回空字符串，由调用方降级处理。
    """
    if llm_vision is None:
        return ''
    try:
        import base64
        b64 = base64.b64encode(image_bytes).decode()
        # Qwen-VL 多模态消息格式（兼容 OpenAI vision 格式）
        from langchain_core.messages import HumanMessage
        msg = HumanMessage(content=[
            {"type": "text",
             "text": (
                 f'这是一张宠物照片，宠主描述的症状是："{symptom_text}"。\n'
                 f'请从视觉角度描述图中宠物的外观状态：\n'
                 f'1. 可见的异常体征（皮毛、眼睛、姿态、伤口、肿胀等）\n'
                 f'2. 精神状态（活跃/萎靡/痛苦表情等）\n'
                 f'3. 是否与宠主描述症状相符\n'
                 f'输出简洁客观的视觉观察报告，不做医疗诊断。'
             )},
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ])
        response = llm_vision.invoke([msg])
        return response.content
    except Exception as e:
        logger.warning(f"Qwen-VL 图片分析失败: {e}")
        return ''


def run_triage_expert(symptom: str, location: str | None = None, image_bytes: bytes | None = None) -> str:
    """
    医疗分诊：MedicalExpert + NavigatorAgent 两 Agent 串联 Crew。
    - 有图片时：先用 Qwen-VL（llm_vision）分析图片，将视觉描述拼入症状文本
    - MedicalExpert（DeepSeek）：调用知识库工具检索，输出结构化 JSON（risk_level/need_navigation）+ Markdown 报告
    - NavigatorAgent（DeepSeek）：读取 JSON 字段自主决定是否调用地图工具
    图片分析用 Qwen-VL，文本推理用 DeepSeek，各司其职。
    """
    # ── 图片预处理：Qwen-VL 视觉分析（若有图片且已配置） ────────────
    vision_desc = ''
    if image_bytes:
        vision_desc = _analyze_image_with_vision(image_bytes, symptom)
        if vision_desc:
            logger.info("Qwen-VL 视觉分析完成，结果已注入分诊上下文")

    # 将视觉描述拼入症状文本，供 MedicalExpert 使用
    full_symptom = symptom
    if vision_desc:
        full_symptom = (
            f'{symptom}\n\n'
            f'【图片视觉分析（Qwen-VL）】\n{vision_desc}'
        )
    medical_expert   = get_medical_expert_agent(llm)
    navigator_agent  = get_navigator_agent(llm)

    task_triage = Task(
        description=(
            f'请对以下宠物症状进行分诊：\n"{full_symptom}"\n\n'
            f'步骤：\n'
            f'1. 调用 pet_health_knowledge_search 工具，检索该症状的相关知识（可多次检索）。\n'
            f'2. 若上文包含【图片视觉分析】内容，结合视觉观察与文字症状综合判断。\n'
            f'3. 综合所有信息确定风险等级，按格式要求输出 JSON + Markdown 报告。'
        ),
        expected_output=(
            '两部分内容：\n'
            '第一部分：```json 代码块，包含字段：\n'
            '  risk_level（枚举：Low/Medium/High/Emergency）、\n'
            '  diagnosis_summary（一句话摘要）、\n'
            '  need_navigation（布尔值，High/Emergency 时为 true）。\n'
            '第二部分：完整 Markdown 分诊报告，含症状分析、护理建议、风险等级说明。'
        ),
        agent=medical_expert
    )

    task_navigate = Task(
        description=(
            f'你已收到分诊专家的报告（含 JSON 结构化字段和 Markdown 详情）作为 context。\n'
            f'请读取 JSON 中的 need_navigation 和 risk_level 字段，自主决定是否导航：\n'
            f'  - need_navigation 为 true，或 risk_level 为 "High"/"Emergency"：\n'
            f'    调用 nearby_hospital_search 工具，坐标：{location or "116.4074,39.9042"}。\n'
            f'  - 否则：直接输出"本次症状无需紧急就医，请按分诊建议居家观察或预约门诊。"'
        ),
        expected_output=(
            '若触发导诊：5公里内宠物医院列表（含名称、距离、地址）。\n'
            '若无需导诊：一句话告知用户无需立即就医。'
        ),
        agent=navigator_agent,
        context=[task_triage]
    )

    crew = Crew(
        agents=[medical_expert, navigator_agent],
        tasks=[task_triage, task_navigate],
        process=Process.sequential,
        verbose=True
    )
    result = crew.kickoff()

    # 拼合两个 Agent 的输出作为完整响应
    task_outputs = result.tasks_output if hasattr(result, 'tasks_output') else []
    triage_report  = str(task_outputs[0]) if len(task_outputs) > 0 else str(result)
    navigate_info  = str(task_outputs[1]) if len(task_outputs) > 1 else ""
    if navigate_info and "无需紧急就医" not in navigate_info:
        return f"{triage_report}\n\n---\n### 📍 附近宠物医院\n{navigate_info}"
    return triage_report


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


def run_match_followup(user_query: str) -> list:
    """
    智能匹配第一步：需求显化 Agent Crew（单 Agent + 工具）。
    - NeedAnalyzer：调用 generate_followup_questions 工具，识别用户描述中的信息缺口，
      输出结构化追问列表（2-3个，含选项），将模糊情感表达转化为可量化的偏好维度。
    返回追问列表 list[dict]，每项含 key、question、options。
    """
    need_analyzer = Agent(
        role='宠物需求分析师',
        goal='分析用户宠物需求描述中的模糊点和信息缺口，生成针对性的结构化追问。',
        backstory=(
            '你是一名专业的宠物领养顾问，擅长从用户的只言片语中识别其真实需求。'
            '你必须调用 generate_followup_questions 工具来生成结构化追问，'
            '不能凭空编造问题。输出必须是合法的 JSON 数组。'
        ),
        llm=llm,
        tools=[generate_followup_questions],
        verbose=True,
        allow_delegation=False
    )

    task = Task(
        description=(
            f'用户正在寻找宠物，他们的初始描述是："{user_query}"。\n'
            f'请调用 generate_followup_questions 工具，传入该描述，获得结构化追问列表。\n'
            f'直接输出工具返回的 JSON 数组，不要添加额外说明文字。'
        ),
        expected_output='JSON 数组字符串，每项含 key、question、options 三个字段，共 2-3 条追问。',
        agent=need_analyzer
    )

    crew = Crew(agents=[need_analyzer], tasks=[task], process=Process.sequential, verbose=True)
    result_str = str(crew.kickoff())

    # 解析输出
    import re
    json_match = re.search(r'\[[\s\S]*\]', result_str)
    if json_match:
        try:
            return json.loads(json_match.group())[:3]
        except Exception:
            pass
    # 降级兜底
    return [
        {"key": "activity_level", "question": "您更希望宠物是活泼好动还是安静乖巧的？", "options": ["活泼好动", "安静乖巧", "都可以"]},
        {"key": "living_space",   "question": "您的居住空间大概是什么情况？",             "options": ["小型公寓", "中等户型", "带院子的大户型"]},
        {"key": "time_availability", "question": "平时每天能陪伴宠物多长时间？",          "options": ["2小时以内", "2-4小时", "4小时以上"]}
    ]


def run_smart_match(user_query: str, pet_list: list, followup_answers: dict | None = None) -> list:
    """
    智能匹配第二步：两 Agent 串联 Crew（工具评分 + 语义解读）。
    - MatchScorer：调用 score_pet_match 工具，基于用户偏好画像对宠物列表进行多维度结构化评分
    - MatchAdvisor：读取评分结果，结合宠物详情生成人性化推荐理由（适配优势/潜在挑战/弥合建议）
    两个 Agent 通过 context 传递，确保推荐理由基于工具评分数据，而非 LLM 主观臆断。
    """
    # 构建用户完整画像
    profile = {"query": user_query}
    if followup_answers:
        profile.update(followup_answers)

    # 精简宠物列表（避免 token 过多）
    pet_summaries = [
        {
            "id": p.get("id"),
            "name": p.get("name", ""),
            "species": p.get("species", ""),
            "energy_level": p.get("energy_level", ""),
            "is_shedding": p.get("is_shedding", ""),
            "description": (p.get("desc") or p.get("description") or "")[:60]
        }
        for p in pet_list[:20]
    ]

    scorer_agent = Agent(
        role='宠物匹配评分专员',
        goal='基于用户偏好画像，调用评分工具对宠物列表进行多维度结构化匹配评分，输出原始评分数据。',
        backstory=(
            '你是匹配系统的数据处理专员，负责调用 score_pet_match 工具完成客观评分。'
            '你只负责调用工具并输出原始评分 JSON，不做主观解读。'
        ),
        llm=llm,
        tools=[score_pet_match],
        verbose=True,
        allow_delegation=False
    )

    advisor_agent = Agent(
        role='宠物领养推荐顾问',
        goal='基于评分专员提供的匹配数据，生成结构化、可解释的推荐报告，说明每只宠物的适配优势和潜在挑战。',
        backstory=(
            '你是一名资深宠物领养顾问，擅长将数据评分转化为宠主能理解的个性化推荐理由。'
            '你的推荐必须基于评分专员提供的匹配维度数据，每条推荐须包含：'
            '一句话理由、适配优势（2-3条）、潜在挑战（1-2条）、弥合建议。'
            '输出合法 JSON 数组。'
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=False
    )

    task_score = Task(
        description=(
            f'用户偏好画像（JSON）：{json.dumps(profile, ensure_ascii=False)}\n'
            f'宠物列表（JSON）：{json.dumps(pet_summaries, ensure_ascii=False)}\n'
            f'请调用 score_pet_match 工具，传入上述两个 JSON 字符串，输出评分结果。'
        ),
        expected_output='评分结果 JSON 数组（含 id、name、fit_score、matched_dims、mismatch_dims）。',
        agent=scorer_agent
    )

    task_advise = Task(
        description=(
            f'根据评分专员提供的匹配数据，结合用户需求："{user_query}"，'
            f'为评分最高的 5 只宠物生成推荐报告。\n'
            f'输出 JSON 数组，每项包含：\n'
            f'- id: 宠物ID（整数）\n'
            f'- fit_score: 来自评分工具的分数（不要修改）\n'
            f'- reason: 一句话推荐理由（15字内，口语化）\n'
            f'- fit_advantages: 适配优势数组（每项10-15字，列2-3条）\n'
            f'- potential_challenges: 潜在挑战数组（每项10-15字，列1-2条，无则空数组）\n'
            f'- mitigation: 弥合建议（一句话，针对挑战）\n'
            f'只输出 JSON 数组，不要其他文字。'
        ),
        expected_output='结构化推荐 JSON 数组，含 id、fit_score、reason、fit_advantages、potential_challenges、mitigation。',
        agent=advisor_agent,
        context=[task_score]
    )

    crew = Crew(
        agents=[scorer_agent, advisor_agent],
        tasks=[task_score, task_advise],
        process=Process.sequential,
        verbose=True
    )
    result = crew.kickoff()

    task_outputs = result.tasks_output if hasattr(result, 'tasks_output') else []
    advise_output = str(task_outputs[1]) if len(task_outputs) > 1 else str(result)

    import re
    json_match = re.search(r'\[[\s\S]*\]', advise_output)
    if json_match:
        try:
            matches = json.loads(json_match.group())
            return [
                {
                    "id": m.get("id"),
                    "fit_score": m.get("fit_score", 80),
                    "reason": m.get("reason", "综合推荐"),
                    "fit_advantages": m.get("fit_advantages", []),
                    "potential_challenges": m.get("potential_challenges", []),
                    "mitigation": m.get("mitigation", "")
                }
                for m in matches[:5] if m.get("id") is not None
            ]
        except Exception:
            pass

    # 降级：直接使用评分工具结果
    logger.warning("run_smart_match advisor 输出解析失败，降级为评分工具直接结果")
    return [
        {"id": p.get("id"), "fit_score": 70, "reason": "综合推荐",
         "fit_advantages": [], "potential_challenges": [], "mitigation": ""}
        for p in pet_summaries[:5] if p.get("id") is not None
    ]
