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
# 2. UI 样式美化 (CSS)
# ==========================================
st.set_page_config(page_title="智慧宠物综合服务平台", page_icon="🐾", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .agent-box { background: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px dashed #ccc; margin-top: 10px; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; transition: 0.3s; }
    .role-tag { background: #333; color: white; padding: 2px 10px; border-radius: 15px; font-size: 0.8em; vertical-align: middle; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 后台业务逻辑 (支持邮箱唯一性)
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
        conn.commit()
        conn.close()
        return True, "注册成功"
    except sqlite3.IntegrityError:
        return False, "该邮箱已被注册，请直接登录"
    except Exception as e:
        return False, f"注册失败: {str(e)}"

# ==========================================
# 4. 登录/注册模块
# ==========================================
if 'user' not in st.session_state:
    col_a, col_b, col_c = st.columns([1, 1.5, 1])
    with col_b:
        st.markdown("<h1 style='text-align:center;'>🐾 智慧宠物平台</h1>", unsafe_allow_html=True)
        tab_l, tab_r = st.tabs(["🔑 登录系统", "📝 新用户注册"])
        
        with tab_l:
            login_email = st.text_input("邮箱地址", key="l_email", placeholder="example@test.com")
            login_pw = st.text_input("密码", type="password", key="l_p")
            if st.button("进入系统"):
                if not login_email or not login_pw:
                    st.warning("请填写邮箱和密码")
                else:
                    user_data = login_user(login_email, login_pw)
                    if user_data:
                        st.session_state['user'] = {
                            "id": user_data[0], 
                            "username": user_data[1], 
                            "role": user_data[2],
                            "email": user_data[3]
                        }
                        st.success(f"欢迎回来，{user_data[1]}！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("邮箱或密码不正确")
        
        with tab_r:
            reg_name = st.text_input("昵称 / 机构名")
            reg_email = st.text_input("注册邮箱 (唯一标识)")
            reg_pw = st.text_input("设置密码", type="password")
            reg_role = st.selectbox("您的身份", ["individual", "org_admin"], 
                                   format_func=lambda x: "👤 个人领养者" if x=="individual" else "🏢 救助机构管理员")
            reg_contact = st.text_input("联系电话")
            
            if st.button("提交注册"):
                if not reg_email or "@" not in reg_email:
                    st.error("请输入有效的邮箱地址")
                elif not reg_pw or len(reg_pw) < 3:
                    st.error("密码太简单啦（至少3位）")
                else:
                    success, msg = register_user(reg_name, reg_email, reg_pw, reg_role, reg_contact)
                    if success:
                        st.success("🎉 注册成功！请切换到“登录”标签进入系统。")
                        st.balloons()
                    else:
                        st.error(msg)

# ==========================================
# 5. 主系统逻辑 (基于角色)
# ==========================================
else:
    user = st.session_state['user']
    role = user['role']
    
    # --- 侧边栏 ---
    with st.sidebar:
        st.header(f"👋 你好, {user['username']}")
        role_cn = "管理员" if role == "org_admin" else ("个人" if role == "individual" else "超级用户")
        st.markdown(f"当前角色: <span class='role-tag'>{role_cn}</span>", unsafe_allow_html=True)
        st.caption(f"登录邮箱: {user['email']}")
        
        # 差异化菜单项
        menu = ["🏠 首页", "🩺 医疗预诊", "📖 养宠百科"]
        if role == "individual":
            menu += ["🐶 寻找领养", "📋 我的申请", "📤 个人送养"]
        elif role == "org_admin":
            menu += ["⚖️ 领养审核", "➕ 宠物上架", "📈 运营大盘"]
        elif role == "root":
            menu = ["⚙️ 系统管理", "📊 全库监控"]

        choice = st.radio("导航菜单", menu)
        if st.sidebar.button("登出系统"):
            del st.session_state['user']
            st.rerun()

    # --- 功能分发 (逻辑保持不变，确保稳定性) ---
    st.title(choice)

    if choice == "🏠 首页":
        st.markdown(f"""
        <div class='main-card'>
            <h3>欢迎回来，{user['username']}！</h3>
            <p>您的身份是 <b>{role_cn}</b>。系统已为您定制了专属的 Agent 协作面板。</p>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("活跃 Agent", "5 个")
        with c2: st.metric("知识库条目", "1,200+")
        with c3: st.metric("今日成功匹配", "12 对")

    elif "医疗预诊" in choice:
        st.info("💡 由 Medical Agent 和 Navigator Agent 协作的诊疗流。")
        symptom = st.text_area("请描述宠物表现", height=150)
        if st.button("开始 AI 协作诊断"):
            with st.status("🩺 医疗团队正在联合研判...") as status:
                doc = get_medical_expert_agent(llm)
                nav = get_navigator_agent(llm)
                t1 = Task(description=f"分析症状: {symptom}", expected_output="病情等级和建议", agent=doc)
                t2 = Task(description="若是紧急病情给出导诊建议。", expected_output="导诊方案", agent=nav, context=[t1])
                crew = Crew(agents=[doc, nav], tasks=[t1, t2], process=Process.sequential)
                result = crew.kickoff()
                status.update(label="✅ 诊断完成", state="complete")
            st.markdown(f"<div class='agent-box'>{result}</div>", unsafe_allow_html=True)

    elif "养宠百科" in choice:
        q = st.text_input("养宠知识查询...")
        if st.button("查阅百科"):
            with st.spinner("AI 专家查阅中..."):
                ans = run_knowledge_expert(q)
                st.success(ans)

    elif "寻找领养" in choice:
        u_pref = st.text_area("描述您的居住环境和理想宠物")
        if st.button("开始精准匹配"):
            with st.spinner("Agent 检索中..."):
                res = run_pet_crew(u_pref)
                st.markdown(res)

    elif "领养审核" in choice:
        st.markdown("<div class='main-card'><h3>📊 待审领养申请</h3></div>", unsafe_allow_html=True)
        conn = sqlite3.connect(SQLITE_DB_PATH)
        query = "SELECT a.id, a.user_name, a.reason, p.name as pet_name, p.description as pet_desc FROM applications a JOIN pets p ON a.pet_id = p.id WHERE a.status = '待审核'"
        apps_df = pd.read_sql_query(query, conn)
        conn.close()

        if apps_df.empty:
            st.info("暂无待处理申请。")
        else:
            for _, row in apps_df.iterrows():
                with st.expander(f"申请 #{row['id']} - {row['user_name']}"):
                    st.write(f"**理由:** {row['reason']}")
                    from src.agents.agents import run_audit_task
                    if st.button(f"🔍 AI 审计", key=f"audit_{row['id']}"):
                        with st.spinner("审计中..."):
                            report = run_audit_task(row['user_name'] + row['reason'], row['pet_name'])
                            st.markdown(f"#### 🤖 报告\n{report}")
