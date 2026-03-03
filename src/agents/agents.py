# 多智能体 CrewAI 核心逻辑
import os
import json
import chromadb
import asyncio
import edge_tts
import base64
from io import BytesIO
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# 导入专项 Agent 构造函数
from .audit_expert import get_audit_expert_agent
from .medical_expert import get_medical_expert_agent
from .navigator import get_navigator_agent
from .pet_expert import get_pet_expert_agent
from .pet_persona import get_pet_persona_agent

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
        print(f"语音生成失败: {e}")
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
