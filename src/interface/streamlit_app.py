import streamlit as st
import os
import sys
import sqlite3

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
try:
    from src.database.db_config import SQLITE_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH

# ==========================================
# 1. 页面配置与美化
# ==========================================
st.set_page_config(page_title="智慧宠物领养系统", page_icon="🐾", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ 系统设置")
    api_key = st.text_input("DeepSeek API Key", type="password")
    st.info("本系统由 CrewAI 多智能体引擎驱动")
    if st.button("查看当前库内宠物"):
        conn = sqlite3.connect(SQLITE_DB_PATH)
        df = conn.execute("SELECT name, species, energy_level FROM pets").fetchall()
        st.write(df)

# ==========================================
# 2. 定义 Agent 逻辑 (封装成函数)
# ==========================================
@tool("pet_database_search")

def add_pet_to_db(name, species, shedding, energy, desc):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pets (name, species, is_shedding, energy_level, description) VALUES (?, ?, ?, ?, ?)",
                   (name, species, shedding, energy, desc))
    conn.commit()
    conn.close()

def submit_application(user_name, pet_name, contact):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    # 模拟简单的申请入库
    cursor.execute("CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY, user TEXT, pet TEXT, contact TEXT)")
    cursor.execute("INSERT INTO applications (user, pet, contact) VALUES (?, ?, ?)", (user_name, pet_name, contact))
    conn.commit()
    conn.close()

tab1, tab2, tab3 = st.tabs(["🔍 智能领养匹配", "📋 领养申请", "⚙️ 管理员后台"])

with tab1:
    # 这里放你之前的 CrewAI 匹配逻辑
    st.write("之前的匹配逻辑搬到这里...")

with tab2:
    st.subheader("提交领养意向")
    with st.form("apply_form"):
        u_name = st.text_input("您的姓名")
        p_name = st.text_input("想领养的宠物名字")
        u_contact = st.text_input("联系方式")
        if st.form_submit_button("提交申请"):
            submit_application(u_name, p_name, u_contact)
            st.success("申请已提交，等待审核！")

with tab3:
    st.subheader("待领养宠物管理")
    with st.expander("➕ 添加新宠物"):
        with st.form("add_pet"):
            n = st.text_input("名字")
            s = st.selectbox("品种", ["猫", "狗", "其他"])
            sh = st.selectbox("掉毛程度", ["极少", "中等", "经常"])
            en = st.selectbox("活力程度", ["安静", "中等", "活泼"])
            de = st.text_area("详细描述")
            if st.form_submit_button("上架宠物"):
                add_pet_to_db(n, s, sh, en, de)
                st.toast("宠物信息已存入数据库！")
def pet_database_search(query_keyword: str):
    """根据关键词检索数据库中的宠物。"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    sql = "SELECT name, species, description FROM pets WHERE status = '待领养' AND (species LIKE ? OR energy_level LIKE ? OR description LIKE ?)"
    param = f"%{query_keyword}%"
    cursor.execute(sql, (param, param, param))
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"【{r[0]}】{r[1]}: {r[2]}" for r in rows]) if rows else "无匹配"

def run_ai_crew(user_input, api_key):
    # 初始化 LLM
    llm = LLM(model="openai/deepseek-chat", base_url="https://api.deepseek.com", api_key=api_key)
    
    # 定义 Agent
    dispatcher = Agent(role='分析专家', goal='提取宠物特征词', backstory='提取关键词', llm=llm)
    recommender = Agent(role='领养顾问', goal='查库并推荐', backstory='基于真实数据回复', llm=llm, tools=[pet_database_search])
    
    # 定义 Task
    t1 = Task(description=f"提取关键词：{user_input}", expected_output="1个关键词", agent=dispatcher)
    t2 = Task(description="查库并生成温馨推荐词", expected_output="中文推荐报告", agent=recommender, context=[t1])
    
    crew = Crew(agents=[dispatcher, recommender], tasks=[t1, t2], process=Process.sequential)
    return crew.kickoff()

# ==========================================
# 3. 主界面交互
# ==========================================
st.title("🐾 基于多智能体协作的智慧宠物领养系统")
st.caption("2026 届毕业设计演示 demo | 驱动引擎：DeepSeek-V3 + CrewAI")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 领养意向输入")
    user_query = st.text_area("请描述您的职业、居住环境以及对宠物的期待：", 
                             height=150, 
                             placeholder="例如：我平时工作比较忙，住在小公寓，想要一只安静不掉毛的猫...")
    
    if st.button("开始 AI 智能匹配"):
        if not api_key:
            st.warning("请在左侧边栏输入 API Key")
        else:
            with st.status("🤖 多智能体正在协作分析...", expanded=True) as status:
                st.write("1. 需求分析专家正在提取特征...")
                # 此处运行 Crew 逻辑
                result = run_ai_crew(user_query, api_key)
                status.update(label="✅ 匹配完成！", state="complete", expanded=False)
            
            with col2:
                st.subheader("✨ AI 推荐方案")
                st.success("为您找到以下匹配对象：")
                st.markdown(result)
                st.balloons()

if not user_query:
    with col2:
        st.info("在左侧输入需求后，点击按钮即可看到 Agent 团队的协作结果。")