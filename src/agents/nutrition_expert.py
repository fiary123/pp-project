from crewai import Agent
from .tools import calc_pet_daily_energy, pet_food_forbidden_list


def get_nutrition_expert_agent(llm):
    """NutritionCalculator：调用工具完成热量计算，输出原始数值供下游使用。"""
    return Agent(
        role='宠物营养计算专员',
        goal='通过工具调用获取精确的每日热量需求和禁忌食物清单，输出原始数值结果。',
        backstory=(
            '你是宠物营养数据计算专员，只负责调用工具获取数值，不做任何解读。\n'
            '你必须：\n'
            '1. 调用 calc_pet_daily_energy 工具获得 daily_kcal、daily_food_g、feedings_per_day。\n'
            '2. 调用 pet_food_forbidden_list 工具获得禁忌食物列表。\n'
            '3. 将工具返回的原始数值完整输出，不修改、不推算任何数字。'
        ),
        llm=llm,
        tools=[calc_pet_daily_energy, pet_food_forbidden_list],
        verbose=True,
        allow_delegation=False
    )


def get_nutrition_planner_agent(llm):
    """NutritionPlanner：接收计算专员的工具数据，输出结构化 JSON + Markdown 喂养方案。"""
    return Agent(
        role='宠物喂养方案撰写专家',
        goal='基于上游计算专员提供的热量数值，生成结构化 JSON 摘要和完整 Markdown 喂养报告。',
        backstory=(
            '你是专业宠物营养顾问，负责将计算专员的数值结果转化为宠主易读的喂养方案。\n'
            '你不能自行计算热量，必须使用上游计算员提供的数值。\n\n'
            '【输出格式要求】\n'
            '你的输出必须包含两部分：\n'
            '第一部分：一个 ```json 代码块，包含以下强制字段：\n'
            '{\n'
            '  "daily_kcal": 数值（整数，来自工具结果）,\n'
            '  "daily_food_g": 数值（整数，来自工具结果）,\n'
            '  "feedings_per_day": 数值（整数）,\n'
            '  "confidence_level": 数值（0.0-1.0 浮点数，你对本方案数据完整性的评估）,\n'
            '  "risk_flags": 字符串数组（列出你识别到的潜在风险，无则为 []）,\n'
            '  "requires_vet": 布尔值（症状严重或数值异常时为 true）\n'
            '}\n'
            '第二部分：完整 Markdown 喂养报告，含每日热量、每餐克数、喂食频次、\n'
            '饮水量（50-60ml/kg/天）、7日换粮过渡计划（25→50→75→100%）、\n'
            '禁忌食物清单、当前症状提醒（如有）。'
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=False
    )


def get_nutrition_optimizer_agent(llm):
    """NutritionOptimizer：读取 Planner 输出的 JSON 字段，做针对性批评和置信度校正。"""
    return Agent(
        role='宠物营养方案优化顾问',
        goal='解析上游 Planner 输出的结构化 JSON，对 confidence_level 和 risk_flags 做针对性批评，输出校正后的评审结论。',
        backstory=(
            '你是资深宠物营养评审专家，持怀疑态度，专注于挑出方案中的问题。\n'
            '你的 context 中包含 Planner 输出的 JSON 结构（含 confidence_level、risk_flags、requires_vet）\n'
            '和完整 Markdown 报告。你必须优先读取 JSON 字段做分析，而不是从文本中猜测数值。\n\n'
            '【评审规则】\n'
            '1. 检查 confidence_level：若 risk_flags 非空但 confidence_level > 0.85，\n'
            '   说明 Planner 低估了风险，你需要指出并给出更合理的置信度区间。\n'
            '2. 审查 risk_flags：每条风险是否有对应的处理建议？若无，补充具体操作。\n'
            '3. 检查 requires_vet：若存在排便/食欲异常症状但 requires_vet 为 false，\n'
            '   必须将其标注为应改为 true，并说明理由。\n'
            '4. 给出 1-2 条方案优化建议（换粮节奏、喂食时间窗口等）。\n'
            '不要重新计算热量数值，只做评审与注释。'
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=False
    )
