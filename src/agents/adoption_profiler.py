"""
领养资质评估多智能体模块

五层架构：
  L1 数据输入与画像构建  → 由调用方（agents.py）负责组装上下文
  L2 规则约束与预筛     → rule_engine_prescreen()
  L3 LLM 语义推理       → get_adoption_profiler_agent（含动机分析、矛盾识别）
  L4 多智能体协同决策    → get_encyclopedia_agent / get_cohabitation_risk_agent
  L5 输出与审计         → 由 agents.py run_adoption_assessment() 统一封装
"""

from crewai import Agent
from .tools import pet_health_knowledge_search


# ==========================================
# L2：规则约束与预筛引擎（不依赖 LLM）
# ==========================================

# 各宠物品种月均最低养护成本估算（元/月）
_SPECIES_MIN_COST = {"cat": 300, "dog": 400}
# 各品种建议最低日陪伴时长（小时）
_SPECIES_MIN_COMPANION_HOURS = {"cat": 1.0, "dog": 2.0}


def rule_engine_prescreen(
    target_species: str,
    monthly_budget: float,
    daily_companion_hours: float,
    has_pet_experience: bool,
    housing_type: str,
    existing_pets: str,
    applicant_info: str,
) -> dict:
    """
    规则预筛层：识别硬约束违规与明显高风险情况。
    先让系统"稳"，再让模型"聪明"。

    返回:
        {
            "hard_block": bool,          # 是否命中绝对硬约束（直接建议驳回）
            "risk_flags": list[str],     # 风险标记列表
            "penalty_score": int,        # 评分惩罚值（0-100，越高扣分越多）
            "need_manual_review": bool,  # 是否建议人工复核
            "prescreen_summary": str     # 预筛摘要（供 LLM 层参考）
        }
    """
    risk_flags = []
    penalty_score = 0
    hard_block = False
    need_manual_review = False

    info_lower = applicant_info.lower()

    # --- 硬约束判断 ---
    # 1. 房屋明确不允许养宠
    if any(kw in applicant_info for kw in ["不允许养宠", "禁止养宠", "房东不让", "合同禁止"]):
        hard_block = True
        risk_flags.append("🔴 [硬约束] 住房合同或房东明确禁止养宠，申请无法通过")
        penalty_score += 100

    # 2. 预算明显低于最低成本
    min_cost = _SPECIES_MIN_COST.get(target_species, 350)
    if 0 < monthly_budget < min_cost * 0.6:
        risk_flags.append(f"🔴 [经济] 月预算 {monthly_budget} 元低于该品种最低月均成本 {min_cost} 元的 60%")
        penalty_score += 30
        need_manual_review = True
    elif 0 < monthly_budget < min_cost:
        risk_flags.append(f"🟡 [经济] 月预算 {monthly_budget} 元偏低，建议提高至 {min_cost} 元以上")
        penalty_score += 15

    # 3. 日陪伴时间过低
    min_hours = _SPECIES_MIN_COMPANION_HOURS.get(target_species, 1.5)
    if 0 < daily_companion_hours < min_hours:
        risk_flags.append(f"🟡 [时间] 每日陪伴时长 {daily_companion_hours} 小时低于建议值 {min_hours} 小时")
        penalty_score += 20
        if daily_companion_hours < min_hours * 0.5:
            risk_flags[-1] = risk_flags[-1].replace("🟡", "🔴")
            penalty_score += 10
            need_manual_review = True

    # 4. 新手申请高护理难度宠物（哈士奇/边牧/暹罗等）
    high_difficulty_keywords = ["哈士奇", "边牧", "萨摩耶", "暹罗", "布偶", "斗牛"]
    if not has_pet_experience:
        for kw in high_difficulty_keywords:
            if kw in applicant_info or kw in existing_pets:
                risk_flags.append(f"🟡 [经验] 无养宠经验申请高护理难度品种（{kw}），存在照护风险")
                penalty_score += 20
                need_manual_review = True
                break

    # 5. 高层未封窗（明确安全隐患）
    if any(kw in applicant_info for kw in ["高层", "楼层高", "顶层", "20层", "18层", "15层"]):
        if "封窗" not in applicant_info and "纱窗" not in applicant_info:
            risk_flags.append("🟡 [环境] 居住高层但未提及封窗/防护措施，存在宠物坠落风险")
            penalty_score += 15

    # 6. 家有婴幼儿或老人申请攻击性较强的品种
    family_risk_keywords = ["婴儿", "新生儿", "老人", "老年人", "独居老人"]
    aggressive_breeds = ["松狮", "藏獒", "比特", "德牧", "杜宾"]
    has_vulnerable = any(kw in applicant_info for kw in family_risk_keywords)
    has_aggressive = any(kw in applicant_info for kw in aggressive_breeds)
    if has_vulnerable and has_aggressive:
        risk_flags.append("🔴 [家庭] 家中有婴幼儿/老人，且目标宠物为具有攻击性倾向的品种，风险极高")
        penalty_score += 35
        need_manual_review = True

    # 7. 租房稳定性风险
    if any(kw in applicant_info for kw in ["租房", "合租", "短租", "经常搬家"]):
        risk_flags.append("🟡 [稳定性] 租房居住存在搬迁不确定性，可能影响宠物长期安置")
        penalty_score += 10

    prescreen_summary = (
        f"规则预筛结果：命中 {len(risk_flags)} 条风险项，"
        f"评分惩罚 {penalty_score} 分，"
        f"{'已触发硬约束' if hard_block else '未触发硬约束'}，"
        f"{'建议人工复核' if need_manual_review else '无需强制复核'}。\n"
        f"风险项：{'; '.join(risk_flags) if risk_flags else '无'}"
    )

    return {
        "hard_block": hard_block,
        "risk_flags": risk_flags,
        "penalty_score": min(penalty_score, 100),
        "need_manual_review": need_manual_review,
        "prescreen_summary": prescreen_summary,
    }


# ==========================================
# L4：多智能体协同决策层
# ==========================================

def get_encyclopedia_agent(llm):
    """
    百科知识专家：提取目标宠物品种的标准养护 Baseline。
    职责：为后续画像匹配和共处风险评估提供权威数据基础。
    """
    return Agent(
        role='宠物品种百科专家',
        goal='从知识库中精确提取目标宠物品种的标准养护需求，输出结构化 Baseline 供后续专家使用。',
        backstory=(
            '你是一名拥有 20 年从业经验的宠物行为学家与品种研究专家，\n'
            '熟悉各品种宠物的空间需求、运动量等级、陪伴依赖性、健康风险与日常养护成本。\n\n'
            '【工具调用规则】\n'
            '第一步：调用 pet_health_knowledge_search，以品种名称为关键词检索知识库。\n'
            '第二步：检查结果是否包含该品种的具体养护数据。\n'
            '  - 如果首次检索结果不相关（无品种特异性内容），换用品种的别名或英文名重新检索，最多尝试两次。\n'
            '  - 两次均无结果时，基于专业知识给出合理估算，并在 special_notes 中注明"基于专业知识估算"。\n\n'
            '你的输出必须包含以下六个维度，以 JSON 格式返回：\n'
            '{\n'
            '  "space_requirement": "适合的居住环境（公寓可/需独立院子/均可）",\n'
            '  "exercise_level": "低/中/高，每日建议运动时长（分钟）",\n'
            '  "companionship_need": "独处耐受度（高/中/低），是否有分离焦虑风险",\n'
            '  "monthly_cost_range": "月均养护成本区间（元/月），含食物/医疗/美容",\n'
            '  "beginner_friendly": true或false，以及理由说明,\n'
            '  "special_notes": "该品种特有的健康风险、行为特点或照护难点"\n'
            '}'
        ),
        llm=llm,
        tools=[pet_health_knowledge_search],
        verbose=True,
        max_iter=3,
        allow_delegation=False
    )


def get_adoption_profiler_agent(llm):
    """
    领养画像专家（L3 LLM 语义推理层核心）：
    对比申请人条件与品种 Baseline，同时进行语义动机分析和矛盾识别。
    输出准备度评分、成功倾向、风险等级和个性化建议。
    """
    return Agent(
        role='领养申请深度画像分析师',
        goal=(
            '综合规则预筛结果、品种 Baseline 和申请人文本，进行全维度领养准备度评估，'
            '识别隐性风险与申请动机，输出量化评分和个性化建议。'
        ),
        backstory='''你是一名兼具社会学背景和动物福利专业知识的领养评估专家，
        曾参与审核超过 3000 份领养申请，深谙人与宠物之间的匹配规律。

        你的分析必须覆盖以下五个层次：

        **一、四维条件评分**（各维度给出 0-25 分和绿灯/黄灯/红灯状态）：
        1. 居住条件：住房面积/类型/楼层安全性 vs 品种空间需求
        2. 时间投入：工作时长/出差频率/家庭成员陪伴 vs 品种陪伴需求
        3. 经验储备：过往养宠经历/专业知识 vs 品种护理难度
        4. 经济能力：月预算 vs 品种月均养护成本（含应急医疗储备评估）

        **二、语义动机分析**（LLM 核心价值所在）：
        - 判断是否为"长期规划型"还是"冲动型"领养
        - 识别表达中的矛盾（如：表单填"时间充足"但描述中提到"经常出差"）
        - 识别隐性风险：情绪化领养、外貌导向、忽视长期成本、对行为的理想化预期
        - 评估动机稳定性得分（0-10）

        **三、综合评分计算**：
        readiness_score = 四维总分（0-100） - 规则预筛惩罚分
        success_probability = readiness_score / 100 × 动机稳定性系数（0.6-1.2）
        confidence_level = 0.95（充分信息时）, 0.75（信息不足时）

        **四、风险因子提取**：
        列出所有识别到的风险点，每条注明维度和严重程度（low/medium/high）。

        **五、个性化建议生成**（必须具体可操作，不能是泛泛而谈）：
        - 针对每条 medium/high 风险给出对应的补救措施
        - 给出 decision：pass / conditional_pass / review_required / reject
        - 给出管理员审核备注（review_note）

        你的最终输出必须为结构化 Markdown 报告，语气专业有温度，避免冷酷拒绝式表达。''',
        llm=llm,
        verbose=True,
        max_iter=3,
        allow_delegation=False
    )


def get_cohabitation_risk_agent(llm):
    """
    共处环境风险专家：评估新旧宠物健康兼容性及居住环境物理安全性。
    如无原住宠物，聚焦于环境安全隐患排查。
    """
    return Agent(
        role='宠物共处环境风险评估专家',
        goal='全面评估新领养宠物进入现有家庭环境后的健康风险、行为冲突风险和物理安全隐患，给出可操作的防护方案。',
        backstory='''你是一名兽医公共卫生专家，同时具备动物行为学背景，
        专注于多宠家庭的共处兼容性评估和新宠融入方案设计。

        你的评估报告必须包含以下四个部分：

        **一、疾病传播风险**（若无原住宠物则标注"不适用"）：
        - 新旧宠物之间的主要传染病风险（猫瘟、犬细小、真菌感染等）
        - 建议隔离期：X 天（给出具体数字）
        - 建议检疫项目清单（疫苗、粪便检测等）
        - 风险等级：低/中/高

        **二、行为冲突风险**：
        - 物种间兼容性（猫犬、同种不同性格等）
        - 年龄差异引发的行为冲突预判（幼年 vs 老年）
        - 领地争夺风险与缓解方案
        - 风险等级：低/中/高

        **三、居住环境物理安全隐患**：
        根据申请人描述排查以下风险：
        - 高层坠落风险（未封窗/阳台无防护）
        - 有毒植物（绿萝、百合等对猫咪高毒）
        - 危险物品暴露（电线、清洁剂、细小零件）
        - 逃跑风险（门缝、纱窗破损等）
        逐项标注是否存在，并给出改造建议。

        **四、综合防护建议**：
        给出新宠物进家前需完成的具体准备清单（格式为可勾选的 Checklist）。

        以结构化 Markdown 报告输出，每个风险项明确标注 ✅/⚠️/🚨 状态。''',
        llm=llm,
        tools=[pet_health_knowledge_search],
        verbose=True,
        max_iter=3,
        allow_delegation=False
    )
