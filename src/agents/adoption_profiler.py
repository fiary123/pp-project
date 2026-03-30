"""
领养资质评估多智能体模块 - v3.5 (支持发布者个性化偏好)

五层架构：
  L1 数据输入与画像构建  → 由调用方（agents.py）负责组装上下文
  L2 规则约束与预筛     → rule_engine_prescreen()
  L3 LLM 语义推理       → get_adoption_profiler_agent（站在发布者立场审核）
  L4 多智能体协同决策    → get_encyclopedia_agent / get_cohabitation_risk_agent
  L5 输出与审计         → 由 agents.py run_adoption_assessment() 统一封装
"""

from crewai import Agent
from .tools import pet_health_knowledge_search


# ==========================================
# L2：规则约束与预筛引擎（不依赖 LLM）
# ==========================================

# 各宠物品种月均最低【生存】成本估算（大幅下调，仅保留生存底线）
_SPECIES_MIN_COST = {"cat": 150, "dog": 200}
# 各品种建议最低日陪伴时长（下调至 0.5-1小时）
_SPECIES_MIN_COMPANION_HOURS = {"cat": 0.5, "dog": 1.0}


def rule_engine_prescreen(
    target_species: str,
    monthly_budget: float,
    daily_companion_hours: float,
    has_pet_experience: bool,
    housing_type: str,
    existing_pets: str,
    applicant_info: str,
    publisher_preferences: dict = None 
) -> dict:
    """
    规则预筛层 v3.6：宽松平台底线 + 尊重发布者意愿。
    """
    risk_flags = []
    penalty_score = 0
    hard_block = False
    
    prefs = publisher_preferences or {}
    risk_tolerance = str(prefs.get("risk_tolerance", "medium")).lower()
    strict_multiplier = 1.2 if risk_tolerance == "conservative" else 0.8 if risk_tolerance == "relaxed" else 1.0

    # --- 1. 平台极简底线 (仅拦截非法或确定违规) ---
    if any(kw in applicant_info for kw in ["禁止养宠", "房东明确拒绝"]):
        hard_block = True
        risk_flags.append("🔴 [硬拦截] 住房环境明确不允许养宠")

    # --- 2. 发布者硬性要求 (这部分尊重发布者的自主权) ---
    if not prefs.get("allow_novice", True) and not has_pet_experience:
        risk_flags.append("🟡 [送养方偏好] 发布者更倾向有经验的领养人")
        penalty_score += int(15 * strict_multiplier) # 仅扣分，不直接拦截

    if not prefs.get("accept_renting", True) and housing_type == "apartment" and "租" in applicant_info:
        risk_flags.append("🟡 [送养方偏好] 发布者更倾向有自住房的领养人")
        penalty_score += int(10 * strict_multiplier)

    if prefs.get("require_stable_housing") and any(kw in applicant_info for kw in ["短租", "经常搬家", "不稳定", "暂住"]):
        risk_flags.append("🟠 [送养方硬性条件] 当前居住稳定性不足，建议补充长期安置计划")
        penalty_score += int(16 * strict_multiplier)

    if prefs.get("require_financial_capacity") and 0 < monthly_budget < (_SPECIES_MIN_COST.get(target_species, 180) + 100):
        risk_flags.append("🟠 [送养方硬性条件] 当前预算接近底线，建议补充基础开销与医疗储备说明")
        penalty_score += int(14 * strict_multiplier)

    if prefs.get("require_family_agreement") and any(kw in applicant_info for kw in ["家里有人反对", "家人犹豫", "室友不确定"]):
        risk_flags.append("🟠 [送养方硬性条件] 家庭内部尚未形成明确共识")
        penalty_score += int(14 * strict_multiplier)

    # --- 3. 弹性校验 (大幅放宽) ---
    # 财务：只要能覆盖基础开销就不算红旗
    min_cost = _SPECIES_MIN_COST.get(target_species, 180)
    if 0 < monthly_budget < min_cost:
        risk_flags.append("🟡 [建议] 预算略低于建议基准，建议未来根据宠物情况适当调整")
        penalty_score += int(5 * strict_multiplier)

    # 时间：尊重快节奏生活
    min_hours = _SPECIES_MIN_COMPANION_HOURS.get(target_species, 0.8)
    if 0 < daily_companion_hours < min_hours:
        risk_flags.append("🟡 [提醒] 陪伴时间较短，建议考虑通过智能设备或家人协作弥补")
        penalty_score += int(5 * strict_multiplier)

    if prefs.get("prefer_quiet_household") and any(kw in applicant_info for kw in ["经常聚会", "家里热闹", "噪音大"]):
        risk_flags.append("🟡 [送养方软偏好] 当前家庭环境可能与宠物需要的安静氛围不完全匹配")
        penalty_score += int(6 * strict_multiplier)

    if prefs.get("prefer_multi_pet_experience") and existing_pets.strip() and not has_pet_experience:
        risk_flags.append("🟡 [送养方软偏好] 若有原住宠物，送养方更希望申请人具备多宠磨合经验")
        penalty_score += int(6 * strict_multiplier)

    # 新手友好：鼓励学习
    if not has_pet_experience:
        risk_flags.append("🟢 [鼓励] 虽是初次养宠，系统建议领养后多参考百科知识")

    prescreen_summary = (
        f"预筛完成：系统标记了 {len(risk_flags)} 个建议点。 "
        f"平台底线校验通过，{'命中发布者特定要求' if penalty_score > 20 else '整体条件良好'}，"
        f"送养方风险偏好为{'保守型' if risk_tolerance == 'conservative' else '宽松型' if risk_tolerance == 'relaxed' else '中性'}，已提交给 AI 专家进行深度匹配分析。"
    )

    return {
        "hard_block": hard_block,
        "risk_flags": risk_flags,
        "penalty_score": min(penalty_score, 100),
        "prescreen_summary": prescreen_summary,
    }


# ==========================================
# L4：多智能体协同决策层
# ==========================================

def get_encyclopedia_agent(llm):
    return Agent(
        role='宠物品种百科专家',
        goal='提取目标品种的标准养护 Baseline，作为发布者决策的基础事实依据。',
        backstory='你是一名宠物研究专家，提供关于空间、运动量和成本的客观数据。',
        llm=llm,
        tools=[pet_health_knowledge_search],
        verbose=True,
        max_iter=3,
        allow_delegation=False
    )


def get_adoption_profiler_agent(llm):
    """
    领养人画像专家：在 v3.5 中进化为【送养人的决策参谋】。
    """
    return Agent(
        role='送养方专属决策参谋',
        goal='深度分析领养申请，挖掘申请人是否真正符合送养人的特定偏好，并提供针对性的决策建议。',
        backstory='''你不是中立的画像师，你是送养人（发布者）的贴身顾问。
        你的天职是：**帮送养人过滤掉不符合他个性化要求的申请，并挖掘出真正懂他爱宠的知音。**
        
        如果送养人非常看重“稳定性”，你就得去申请人的职业和居住描述里寻找蛛丝马迹；
        如果送养人担心“新手照顾不好”，你就得去分析申请人的学习热情和对应急情况的处理方案。
        
        你的输出必须包含：
        1. **偏好满足度分析**：对照送养人的每一个设置项，给出申请人的匹配程度。
        2. **潜在风险对冲**：针对送养人担心的点，提出后续面试中可以追问的具体问题。
        3. **决策倾向建议**：不要只给分数，要告诉送养人“建议通过并重点面谈陪伴细节”或“建议驳回，因稳定性存疑”。''',
        llm=llm,
        verbose=True,
        max_iter=3,
        allow_delegation=False
    )


def get_cohabitation_risk_agent(llm):
    return Agent(
        role='宠物共处环境风险评估专家',
        goal='评估居住安全与共处风险，为发布者排除环境方面的后顾之忧。',
        backstory='你是一名兽医和行为学专家，关注物理安全和宠物间的社交兼容性。',
        llm=llm,
        tools=[pet_health_knowledge_search],
        verbose=True,
        max_iter=3,
        allow_delegation=False
    )
