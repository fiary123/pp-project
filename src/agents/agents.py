# 多智能体 CrewAI 核心逻辑
import os
import json
import chromadb
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# 导入专项 Agent 构造函数
from .audit_expert import get_audit_expert_agent
from .medical_expert import get_medical_expert_agent
from .navigator import get_navigator_agent
from .pet_expert import get_pet_expert_agent

# ==========================================
# 1. 环境与模型配置
# ==========================================
# 设置代理
os.environ["http_proxy"] = "socks5h://127.0.0.1:10812"
os.environ["https_proxy"] = "socks5h://127.0.0.1:10812"

# Gemini API Key
api_key = "AIzaSyD-jPyLAHNUGEtYjiZC_BjqVUTlyI0eFHQ"
os.environ["GOOGLE_API_KEY"] = api_key

# 初始化 Gemini 模型
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    verbose=True,
    temperature=0.3,
    google_api_key=api_key
)

# 连接本地向量库
try:
    from src.database.db_config import CHROMA_DB_PATH
except ImportError:
    from ..database.db_config import CHROMA_DB_PATH

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
knowledge_collection = chroma_client.get_or_create_collection(name="pet_knowledge")

# ==========================================
# 2. 定义公共检索工具
# ==========================================

@tool("Search Pet Knowledge Base")
def search_knowledge_tool(query: str) -> str:
    """
    当用户询问关于宠物喂养、健康、疾病护理或日常训练等百科知识时调用。
    """
    results = knowledge_collection.query(query_texts=[query], n_results=3)
    if not results['documents'][0]:
        return "在百科手册中未找到直接相关的知识点，请根据通用常识回答。"
    
    combined_docs = "\n\n".join(results['documents'][0])
    return f"从《宠物百科手册》中找到的相关参考资料：\n\n{combined_docs}"

# ==========================================
# 3. 核心运行工作流
# ==========================================

def run_pet_crew(user_message: str) -> str:
    """
    运行宠物领养匹配工作流 (整合 Pet Expert)
    """
    pet_expert = get_pet_expert_agent(llm)
    
    task = Task(
        description=f'分析用户需求："{user_message}"。从数据库中匹配合适的宠物并生成推荐报告。',
        expected_output='一份专业的 Markdown 格式宠物推荐报告，包含匹配指数。',
        agent=pet_expert
    )

    crew = Crew(agents=[pet_expert], tasks=[task], process=Process.sequential)
    return str(crew.kickoff())

def run_audit_task(applicant_info: str, pet_info: str) -> str:
    """
    运行领养合规性审计任务
    """
    audit_expert = get_audit_expert_agent(llm)

    task = Task(
        description=f'''请对以下领养申请进行合规性审计：
        【申请人背景】: {applicant_info}
        【意向宠物信息】: {pet_info}
        请输出一份结构化的《AI 预审报告》。''',
        expected_output='一份包含 [匹配分值]、[优势]、[风险警示] 和 [审核建议] 的中文报告。',
        agent=audit_expert
    )

    crew = Crew(agents=[audit_expert], tasks=[task], process=Process.sequential)
    return str(crew.kickoff())

def run_knowledge_expert(user_query: str) -> str:
    """
    运行“萌宠百事通”百科专家 Agent
    """
    fact_finder = Agent(
        role='宠物百科百事通',
        goal='基于知识库为用户提供最准确、专业的宠物喂养和护理建议。',
        backstory='你是一部活的“宠物饲养全书”，擅长从海量资料中提取关键信息并用通俗易懂的方式讲解。',
        tools=[search_knowledge_tool],
        llm=llm,
        verbose=True
    )

    task = Task(
        description=f'用户提问："{user_query}"。',
        expected_output='一段专业、详细且易于理解的养宠建议或知识解答。',
        agent=fact_finder
    )

    crew = Crew(agents=[fact_finder], tasks=[task], process=Process.sequential)
    return str(crew.kickoff())
