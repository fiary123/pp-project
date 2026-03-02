import os
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# ==========================================
# 0. 强制清除电脑底层的 Google Cloud 幽灵配置！
# ==========================================
for key in ['GOOGLE_CLOUD_PROJECT', 'GCLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS']:
    if key in os.environ:
        del os.environ[key]  # 强行删掉干扰项

# ==========================================
# 1. 配置你的 API Keys
# ==========================================
# 填入你刚才在 AI Studio 申请的全新 Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyD-jPyLAHNUGEtYjiZC_BjqVUTlyI0eFHQ"
os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"] # 双重保险，防止 CrewAI 底层找不到

# 填入 DeepSeek API Key
os.environ["DEEPSEEK_API_KEY"] = "sk-c69656763f3a49bc9650e243c5ce0542"

# 实例化 Gemini 大脑 (修正模型名称为 models/gemini-1.5-flash)
gemini_llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash", temperature=0.3)

# 国内大脑：深谙中文语境和情感，适合做客服和推荐官
chat_llm = ChatOpenAI(
    model_name="deepseek-chat", 
    openai_api_key=os.environ["DEEPSEEK_API_KEY"], 
    openai_api_base="https://api.deepseek.com",
    temperature=0.7
)

# ==========================================
# 3. 创建专职智能体 (Agents)
# ==========================================
dispatcher = Agent(
    role='中央调度与任务分析师',
    goal='准确理解用户的长难句需求，将其拆解为具体的筛选条件',
    backstory='你是平台的大脑，思维极其严谨。你只负责提取关键信息，不负责和用户寒暄。',
    llm=gemini_llm, # 挂载 Gemini
    verbose=True
)

recommender = Agent(
    role='金牌宠物推荐官',
    goal='根据调度员提取的条件，用极其温暖、共情的中文拟人化语气向用户推荐宠物',
    backstory='你是一个充满爱心的动物救助志愿者，非常懂中文的沟通艺术。',
    llm=chat_llm, # 挂载 国内模型
    verbose=True
)

# ==========================================
# 4. 创建任务流 (Tasks)
# ==========================================
# 模拟用户在前端输入的一段话：
user_input = "我是一个程序员，平时经常加班，住在一个50平米的小公寓里。我想找个不怎么掉毛、安静点的毛孩子陪我。"

task1 = Task(
    description=f'分析用户的输入："{user_input}"。提取出用户的：1. 职业特点 2. 居住环境 3. 对宠物的具体要求。',
    expected_output='一段精简的 JSON 或列表格式的需求摘要。',
    agent=dispatcher
)

task2 = Task(
    description='基于上一步提取的需求，虚构一只完全符合要求的猫咪（例如：一只叫"布丁"的英短蓝猫），并写一段不少于100字的温暖推荐话术。',
    expected_output='一段直接发给用户的中文拟人化回复。',
    agent=recommender
)

# ==========================================
# 5. 组建团队并执行 (The Crew)
# ==========================================
pet_crew = Crew(
    agents=[dispatcher, recommender],
    tasks=[task1, task2],
    process=Process.sequential # 采用顺序流程，先调度分解，再推荐回复
)

if __name__ == "__main__":
    print("🚀 多智能体团队正在后台思考，请稍候...")
    result = pet_crew.kickoff()
    
    print("\n" + "="*50)
    print("✨ 最终呈现给用户的回复：\n")
    print(result)