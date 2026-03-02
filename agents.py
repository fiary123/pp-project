# 多智能体 CrewAI 核心逻辑
import os
import json
import chromadb
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# ⚠️ 注意：这里必须填入你的大模型 API Key（例如 OpenAI）
os.environ["gemini"] = "AIzaSyCDQabIpN9Au-z8Fji9MsybM8eeLPhI4Fw"

# 连接刚才生成的本地向量库
chroma_client = chromadb.PersistentClient(path="./chroma_data")
pet_collection = chroma_client.get_collection(name="pet_profiles")

# 定义提供给智能体的检索工具
@tool("Search Pet Database")
def search_pet_tool(query: str) -> str:
    """
    当需要根据用户偏好匹配宠物时调用此工具。
    输入应为凝练的搜索关键词（如："适合小户型、安静"）。
    """
    results = pet_collection.query(query_texts=[query], n_results=2)
    if not results['documents'][0]:
        return "未找到匹配的宠物。"
    return f"检索到的候选宠物档案：\n{json.dumps(results['documents'][0], ensure_ascii=False)}"

def run_pet_crew(user_message: str) -> str:
    """运行多智能体工作流"""
    
    # 1. 定义智能体
    recommender = Agent(
        role='资深宠物匹配专家',
        goal='从知识库检索并推荐最符合用户需求的宠物。',
        backstory='你曾在顶级动物救助站工作，擅长根据用户居住空间和作息进行科学匹配。',
        tools=[search_pet_tool],
        verbose=True,
        allow_delegation=False
    )

    health_advisor = Agent(
        role='首席宠物医疗顾问',
        goal='解答用户的宠物健康疑问。',
        backstory='你是拥有15年经验的兽医。如果用户的话语中没有提到健康问题，你可以忽略并回复"无需健康建议"。',
        verbose=True,
        allow_delegation=False
    )

    dialogue_officer = Agent(
        role='首席用户沟通官',
        goal='汇总匹配结果和医疗建议，用温暖的语言回复用户。',
        backstory='你是平台的前台，语气温暖充满同理心。请直接输出面向用户的回复。',
        verbose=True,
        allow_delegation=False
    )

    # 2. 分解任务
    task1 = Task(
        description=f'分析用户需求："{user_message}"。提取适合的宠物。',
        expected_output='推荐的宠物名单。',
        agent=recommender
    )
    
    task2 = Task(
        description=f'分析："{user_message}" 中是否包含宠物健康疾病问题。有则解答，无则跳过。',
        expected_output='健康建议或确认无异常。',
        agent=health_advisor
    )
    
    task3 = Task(
        description='汇总前两个任务的结论，组织一段连贯、亲切的最终回复。',
        expected_output='发给用户的最终纯文本回复。',
        agent=dialogue_officer
    )

    # 3. 组建团队并顺序执行
    crew = Crew(
        agents=[recommender, health_advisor, dialogue_officer],
        tasks=[task1, task2, task3],
        process=Process.sequential
    )
    
    result = crew.kickoff()
    return str(result)