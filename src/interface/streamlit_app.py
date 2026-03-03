import streamlit as st
import os
import sys
import sqlite3
import pandas as pd
import time

# 1. 路径与环境配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入核心逻辑与 Agent 构造器
from src.agents.agents import llm, run_knowledge_expert, run_pet_crew
from src.agents.medical_expert import get_medical_expert_agent
from src.agents.pet_expert import get_pet_expert_agent
from src.agents.navigator import get_navigator_agent
from crewai import Task, Crew, Process

try:
    from src.database.db_config import SQLITE_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH

# ==========================================
# 2. 旗舰级 UI 样式美化 (CSS)
# ==========================================
st.set_page_config(page_title="智慧宠物综合服务平台", page_icon="🐾", layout="wide")

st.markdown("""
    <style>
    /* 1. 强力隐藏顶部所有白条及装饰线 */
    header, [data-testid="stHeader"], .stAppHeader, [data-testid="stDecoration"] {
        background-color: rgba(0,0,0,0) !important;
        background: transparent !important;
        border: none !important;
        display: none !important;
    }
    
    /* 2. 全局背景与深色遮罩：解决文字看不清的问题 */
    [data-testid="stAppViewContainer"] {
        background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), 
                          url("https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80");
        background-attachment: fixed;
        background-size: cover;
        font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
    }

    /* 3. 登录卡片 - 旗舰级毛玻璃 */
    .login-container {
        background: rgba(255, 255, 255, 0.1); 
        backdrop-filter: blur(25px); 
        padding: 60px 80px;
        border-radius: 40px;
        box-shadow: 0 40px 100px rgba(0,0,0,0.5);
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-top: 5vh;
        text-align: center;
    }

    /* 4. 主标题与副标题 - 增加发光效果 */
    .huge-title {
        font-size: 76px !important;
        font-weight: 900 !important;
        color: #ff4b4b !important;
        margin-bottom: 10px !important;
        text-shadow: 0 0 20px rgba(255,75,75,0.4);
    }
    .sub-title {
        font-size: 28px !important;
        color: rgba(255,255,255,0.9) !important;
        margin-bottom: 50px !important;
        font-weight: 600;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
    }

    /* 5. 强制改变输入框上方标签字体 - 极其巨大且白亮 */
    div[data-testid="stWidgetLabel"] p {
        font-size: 34px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
        margin-bottom: 15px !important;
        text-align: left !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }

    /* 6. Tab 选项卡美化与对齐 - 深色底突出文字 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 30px;
        justify-content: center;
        background-color: transparent !important;
        border-bottom: 2px solid rgba(255,255,255,0.1);
    }
    .stTabs [data-baseweb="tab"] {
        height: 90px !important;
        background-color: rgba(255,255,255,0.05) !important;
        border-radius: 20px 20px 0 0 !important;
        padding: 0 50px !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .stTabs [data-baseweb="tab"] p {
        font-size: 36px !important;
        font-weight: 800 !important;
        color: rgba(255,255,255,0.7) !important;
    }
    /* 选中状态的 Tab - 高亮红 */
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] p {
        color: white !important;
    }

    /* 7. 输入框规格 - 内部字体深色方便阅读 */
    .stTextInput>div>div>input {
        height: 85px !important;
        font-size: 30px !important;
        border-radius: 20px !important;
        background-color: white !important;
        color: #333 !important;
        border: none !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1) !important;
    }

    /* 8. 按钮规格 - 超大渐变 */
    .stButton>button {
        height: 95px !important;
        font-size: 38px !important;
        font-weight: 900 !important;
        border-radius: 25px !important;
        background: linear-gradient(135deg, #ff4b4b 0%, #ff8f8f 100%) !important;
        color: white !important;
        margin-top: 40px !important;
        border: none !important;
        box-shadow: 0 15px 35px rgba(255,75,75,0.5) !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 45px rgba(255,75,75,0.6) !important;
    }

    /* 9. 内部系统卡片 */
    .main-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 30px;
        border-radius: 25px;
        color: #333 !important;
        border-left: 10px solid #ff4b4b;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 后台业务逻辑
# ==========================================
def login_user(email, password):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    res = conn.execute("SELECT id, username, role, email FROM users WHERE email=? AND password=?", (email, password)).fetchone()
    conn.close()
    return res

def register_user(username, email, password, role, contact):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.execute("INSERT INTO users (username, email, password, role, contact) VALUES (?,?,?,?,?)", 
                    (username, email, password, role, contact))
        conn.commit(); conn.close()
        return True, "注册成功"
    except sqlite3.IntegrityError:
        return False, "该邮箱已被注册，请直接登录"
    except Exception as e:
        return False, f"错误: {str(e)}"

# ==========================================
# 4. 登录/注册页面布局
# ==========================================
if 'user' not in st.session_state:
    _, center_col, _ = st.columns([0.4, 2.8, 0.4])
    
    with center_col:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<p class="huge-title">🐾 智慧宠物平台</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">多智能体驱动 · 温情公益领养 · 科学医疗服务</p>', unsafe_allow_html=True)
        
        tab_l, tab_r = st.tabs(["🔑 快速登录", "📝 加入我们"])
        
        with tab_l:
            st.markdown("<br>", unsafe_allow_html=True)
            login_email = st.text_input("注册邮箱", key="l_email", placeholder="请输入邮箱地址")
            login_pw = st.text_input("登录密码", type="password", key="l_p", placeholder="请输入登录密码")
            if st.button("立即开启智能服务", use_container_width=True):
                if login_email and login_pw:
                    user_data = login_user(login_email, login_pw)
                    if user_data:
                        st.session_state['user'] = {"id": user_data[0], "username": user_data[1], "role": user_data[2], "email": user_data[3]}
                        st.success(f"🎊 欢迎回来！正在同步数据...")
                        time.sleep(0.5); st.rerun()
                    else: st.error("登录失败：邮箱或密码错误")
                else: st.warning("提示：请填写邮箱和密码")
        
        with tab_r:
            st.markdown("<br>", unsafe_allow_html=True)
            reg_name = st.text_input("您的称呼", placeholder="您的姓名或救助站名称")
            reg_email = st.text_input("注册邮箱地址", placeholder="作为唯一的登录凭证", key="r_email")
            reg_pw = st.text_input("设置登录密码", type="password", placeholder="请设置至少3位密码")
            reg_role = st.selectbox("您的身份", ["individual", "org_admin"], 
                                   format_func=lambda x: "🏠 个人领养者" if x=="individual" else "🏢 救助机构管理员")
            reg_contact = st.text_input("联系电话", placeholder="用于后续沟通")
            if st.button("提交注册申请", use_container_width=True):
                if reg_email and "@" in reg_email:
                    success, msg = register_user(reg_name, reg_email, reg_pw, reg_role, reg_contact)
                    if success: st.success("🎉 注册成功！请切换至“登录”页。"); st.balloons()
                    else: st.error(msg)
                else: st.warning("请填写有效的邮箱地址")
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. 主系统逻辑 (基于角色)
# ==========================================
else:
    user = st.session_state['user']
    role = user['role']
    
    with st.sidebar:
        st.markdown(f"<div style='text-align:center;'><h2 style='color:#333; margin-bottom:0;'>{user['username']}</h2></div>", unsafe_allow_html=True)
        role_cn = "救助站管理员" if role == "org_admin" else ("个人用户" if role == "individual" else "系统核心")
        st.markdown(f"<div style='text-align:center;'><span class='role-tag'>{role_cn}</span></div>", unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        
        menu = ["🏠 首页", "🩺 医疗预诊", "📖 养宠百科"]
        if role == "individual":
            menu += ["🐶 寻找领养", "📋 我的申请进度", "📤 发布个人送养"]
        elif role == "org_admin":
            menu += ["⚖️ 领养申请审核", "➕ 上架机构宠物", "📈 救助数据大盘"]
        
        choice = st.radio("导航菜单", menu)
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("退出系统"):
            del st.session_state['user']; st.rerun()

    # 主内容区域
    st.title(f"{choice}")
    
    if choice == "🏠 首页":
        st.markdown(f"""
        <div class='main-card'>
            <h3>🐾 欢迎进入智慧宠物平台，{user['username']}！</h3>
            <p>您好！系统已为您分配了 <b>{role_cn}</b> 专属权限。您可以通过左侧菜单，唤醒不同的 Agent 专家为您服务。</p>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("在线 Agent", "5 位专家")
        c2.metric("知识库深度", "1,200+ 章节")
        c3.metric("总救助案例", "856 例")

    elif "医疗预诊" in choice:
        st.markdown("<div class='main-card'><h3>🩺 AI 宠物全科医生</h3><p>由 Medical Agent 提供初步诊断，Navigator Agent 提供就医指引</p></div>", unsafe_allow_html=True)
        symptom = st.text_area("请描述宠物的症状", height=150)
        if st.button("发起多智能体专家会诊"):
            with st.status("🩺 医疗专家组正在会诊...") as status:
                doc = get_medical_expert_agent(llm)
                nav = get_navigator_agent(llm)
                t1 = Task(description=f"分析症状: {symptom}", expected_output="病情评估", agent=doc)
                t2 = Task(description="若是紧急情况给出导诊。", expected_output="建议", agent=nav, context=[t1])
                res = Crew(agents=[doc, nav], tasks=[t1, t2]).kickoff()
                status.update(label="✅ 会诊结束", state="complete")
            st.markdown(f"<div class='agent-box' style='background:white; padding:20px; border-radius:15px; color:#333; box-shadow:0 4px 10px rgba(0,0,0,0.1);'>{res}</div>", unsafe_allow_html=True)

    elif "养宠百科" in choice:
        st.markdown("<div class='main-card'><h3>📖 萌宠百事通</h3><p>基于《全能宠物饲养百科手册》的 RAG 智能问答</p></div>", unsafe_allow_html=True)
        q = st.text_input("请输入养宠问题")
        if st.button("查阅权威百科"):
            with st.spinner("AI 专家正在翻阅知识库..."):
                ans = run_knowledge_expert(q)
                st.success(ans)

    elif "寻找领养" in choice:
        st.markdown("<div class='main-card'><h3>🐶 AI 领养匹配助手</h3><p>基于向量数据库 RAG 检索，为您找到灵魂伴侣</p></div>", unsafe_allow_html=True)
        u_pref = st.text_area("描述您的理想宠物")
        if st.button("开始精准筛选"):
            with st.spinner("Agent 检索中..."):
                res = run_pet_crew(u_pref)
                st.markdown(f"<div style='background:white; padding:20px; border-radius:15px; color:#333;'>{res}</div>", unsafe_allow_html=True)

    elif "领养申请审核" in choice:
        st.markdown("<div class='main-card'><h3>⚖️ 申请审核大盘</h3></div>", unsafe_allow_html=True)
        conn = sqlite3.connect(SQLITE_DB_PATH)
        apps = pd.read_sql_query("SELECT a.id, a.user_name, a.reason, p.name as pet_name FROM applications a JOIN pets p ON a.pet_id=p.id WHERE a.status='待审核'", conn)
        conn.close()
        if apps.empty:
            st.info("暂无待审核申请。")
        else:
            for _, row in apps.iterrows():
                with st.expander(f"📦 申请 #{row['id']} - {row['user_name']}"):
                    st.write(f"**意向宠物:** {row['pet_name']}")
                    from src.agents.agents import run_audit_task
                    if st.button(f"🔍 启动 AI 审计", key=f"aud_{row['id']}"):
                        with st.spinner("审计中..."):
                            report = run_audit_task(row['user_name'] + row['reason'], row['pet_name'])
                            st.markdown(f"#### 🤖 预审意见\n{report}")
