from crewai import Agent
from .tools import pet_database_search

def get_pet_expert_agent(llm):
    return Agent(
        role='首席宠物匹配专家',
        goal='通过多维度分析为用户提供精准匹配',
        backstory='''你是一名资深专家。在匹配时，你必须遵循以下 SOP 流程：
        1. 需求解析：从用户输入中提取住房、加班、预算、偏好。
        2. 风险预判：如果用户住高层但没有封窗，必须给出警告。
        3. 数据库检索：调用 pet_database_search 寻找真实宠物。
        4. 最终方案：给出 1-2 个推荐，并解释为什么它们适合。
        你的回复必须使用 Markdown 格式，且包含“匹配指数”这一项。''',
        llm=llm,
        tools=[pet_database_search],
        verbose=True,
        # 增加思考深度：允许 Agent 内部进行自我修正
        max_iter=3,  
        allow_delegation=False
    )