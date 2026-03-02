import os
import sys
import sqlite3
# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_config import SQLITE_DB_PATH
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# ==========================================
# 1. 模型配置 (DeepSeek)
# ==========================================
# 请确保已安装: pip install crewai
os.environ["DEEPSEEK_API_KEY"] = "sk-c69656763f3a49bc9650e243c5ce0542"

deepseek_llm = LLM(
    model="openai/deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    temperature=0.2
)

# ==========================================
# 2. 定义数据库工具 (Agent 的手)
# ==========================================
import requests

# 推荐使用高德地图 API（国内访问最稳，毕设首选）
AMAP_KEY = "966b3f41682127d765517a06be14953a"

@tool("search_nearby_hospitals")
def search_nearby_hospitals(location: str):
    """
    根据用户经纬度（如 '116.48,39.99'）搜索附近 5 公里的宠物医院。
    """
    url = f"https://restapi.amap.com/v3/place/around?key={AMAP_KEY}&location={location}&keywords=宠物医院&types=090500&radius=5000&offset=5&page=1&extensions=all"
    
    response = requests.get(url)
    data = response.json()
    
    if data['status'] == '1' and int(data['count']) > 0:
        hospitals = []
        for poi in data['pois']:
            hospitals.append(f"🏥 {poi['name']} | 距离: {poi['distance']}米 | 地址: {poi['address']}")
        return "\n".join(hospitals)
    return "抱歉，您附近 5 公里内未找到宠物医院。"

@tool("pet_database_search")


def pet_database_search(query_keyword: str):
    """
    这是一个数据库查询工具。当需要根据用户的需求（如品种、性格、是否掉毛）
    寻找真实的宠物时，请调用此工具。传入一个关键词。
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 在品种、性格、描述中进行模糊搜索
    sql = "SELECT name, species, is_shedding, energy_level, description FROM pets WHERE status = '待领养' AND (species LIKE ? OR energy_level LIKE ? OR description LIKE ?)"
    param = f"%{query_keyword}%"
    cursor.execute(sql, (param, param, param))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "数据库中目前没有匹配该关键词的宠物。"
    
    results = []
    for r in rows:
        results.append(f"【匹配到】姓名：{r[0]}，品种：{r[1]}，掉毛情况：{r[2]}，活力：{r[3]}。简介：{r[4]}")
    
    return "\n\n".join(results)

# ==========================================
# 3. 定义智能体 (Agents)
# ==========================================
dispatcher = Agent(
    role='需求分析专家',
    goal='从用户的自我介绍中提取最核心的宠物需求关键词',
    backstory='你擅长洞察人类的需求，能将复杂的描述简化为搜索关键词，如“安静”、“不掉毛”、“猫”等。',
    llm=deepseek_llm,
    verbose=True
)

recommender = Agent(
    role='资深领养匹配官',
    goal='根据提取的关键词查询数据库，并基于真实数据给出领养建议',
    backstory='你是一个有温度的领养站长，你坚持只推荐数据库中真实存在的宠物，并给出专业的匹配理由。',
    llm=deepseek_llm,
    tools=[pet_database_search], # 赋予查询数据库的权利
    verbose=True
)

# ==========================================
# 4. 定义任务 (Tasks)
# ==========================================
user_input = "我是一名程序员，经常熬夜写代码，住在一个小公寓里。我想要一个安静、不怎么掉毛的伙伴陪我。"

task1 = Task(
    description=f"分析这段用户话语：'{user_input}'。提取出1个最关键的宠物特性关键词（例如：'安静' 或 '不掉毛'）。",
    expected_output="一个最能代表用户需求的关键词字符串。",
    agent=dispatcher
)

task2 = Task(
    description="使用 pet_database_search 工具查询数据库。基于查询到的真实宠物信息，为用户撰写一份温暖的推荐词。如果工具返回无结果，请诚实告知用户。",
    expected_output="一份基于真实数据库信息的中文推荐报告。",
    agent=recommender,
    context=[task1]
)

# ==========================================
# 5. 组建团队并执行
# ==========================================
pet_crew = Crew(
    agents=[dispatcher, recommender],
    tasks=[task1, task2],
    process=Process.sequential
)

if __name__ == "__main__":
    print("🚀 正在启动 AI 领养顾问团队...")
    result = pet_crew.kickoff()
    print("\n" + "="*50)
    print("✨ AI 最终推荐方案：\n")
    print(result)