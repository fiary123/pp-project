import streamlit as st
import os
import sys
import sqlite3
import pandas as pd
import time
import base64

# --- 1. 路径与 Agent 导入 ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.agents.agents import llm, run_knowledge_expert, run_pet_crew, run_pet_chat, run_audit_task
from src.agents.medical_expert import get_medical_expert_agent
from src.agents.pet_expert import get_pet_expert_agent
from src.agents.navigator import get_navigator_agent
from crewai import Task, Crew, Process
try:
    from src.database.db_config import SQLITE_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH

# --- 2. 旗舰级 UI/UX 美化 ---
st.set_page_config(page_title="智慧宠物平台", page_icon="🐾", layout="wide")
st.markdown("""
<style>
    /* 隐藏 Streamlit 默认装饰 */
    [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }
    
    /* 全局背景 */
    [data-testid="stAppViewContainer"] {
        background-image: linear-gradient(rgba(240, 242, 246, 0.9), rgba(240, 242, 246, 0.9)), 
                          url("https://images.unsplash.com/photo-1543466835-00a7907e9de1?q=80&w=2070&auto=format&fit=crop");
        background-size: cover; background-attachment: fixed;
    }

    /* 顶部大图标导航栏 */
    .top-nav {
        display: flex; justify-content: space-around; align-items: center;
        background: white; padding: 15px 10px; border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08); margin-bottom: 30px;
    }
    .nav-button {
        background-color: transparent; border: none; padding: 10px;
        border-radius: 15px; transition: background-color 0.3s;
    }
    .nav-button:hover { background-color: #f0f2f6; }
    .nav-button-active { background-color: #ff4b4b; }
    .nav-button-active p { color: white !important; }
    .nav-icon { font-size: 48px; }
    .nav-text { font-size: 20px; font-weight: 700; color: #333; margin-top: 5px; }

    /* 宠物瀑布流卡片 */
    .pet-card {
        background: white; border-radius: 20px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06); text-align: center;
        transition: transform 0.3s, box-shadow 0.3s;
    }
    .pet-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
    .pet-image { width: 100%; height: 200px; object-fit: cover; border-radius: 15px; margin-bottom: 15px; }
    .pet-name { font-size: 24px; font-weight: 800; color: #333; }
    .pet-desc { font-size: 16px; color: #666; height: 3.6em; overflow: hidden; }

    /* 登录页样式 */
    .login-container {
        background: rgba(255, 255, 255, 0.98); padding: 50px; border-radius: 30px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.2); margin-top: 10vh;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 后台业务函数 ---
def login_user(e, p): return sqlite3.connect(SQLITE_DB_PATH).execute("SELECT id, username, role, email FROM users WHERE email=? AND password=?", (e, p)).fetchone()
def register_user(u, e, p, r, c):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.execute("INSERT INTO users (username, email, password, role, contact) VALUES (?,?,?,?,?)", (u, e, p, r, c)); conn.commit()
        return True, "注册成功"
    except sqlite3.IntegrityError: return False, "邮箱已被注册"
def fetch_all_pets(): return pd.read_sql_query("SELECT * FROM pets WHERE status='待领养'", sqlite3.connect(SQLITE_DB_PATH))

# --- 4. 导航栏渲染函数 ---
def render_top_nav(role):
    menu_items = {"individual": ["智能寻找", "医疗预诊", "我的申请", "发布送养"],
                  "org_admin": ["申请审核", "宠物上架", "数据大盘"]}
    icons = {"智能寻找": "🔍", "医疗预诊": "🩺", "我的申请": "📋", "发布送养": "📤",
             "申请审核": "⚖️", "宠物上架": "➕", "数据大盘": "📈"}
    
    # 初始化页面状态
    if 'page' not in st.session_state:
        st.session_state.page = menu_items[role][0]
    
    st.markdown('<div class="top-nav">', unsafe_allow_html=True)
    cols = st.columns(len(menu_items[role]))
    for i, item in enumerate(menu_items[role]):
        with cols[i]:
            active_class = "nav-button-active" if st.session_state.page == item else ""
            if st.button(f'<div class="nav-icon">{icons[item]}</div><p class="nav-text">{item}</p>', use_container_width=True):
                st.session_state.page = item
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. 登录/注册页面 ---
if 'user' not in st.session_state:
    _, center_col, _ = st.columns([1, 1.8, 1])
    with center_col:
        with st.container(border=False):
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("<h1 style='text-align:center; font-size: 52px; color: #ff4b4b;'>🐾 智慧宠物平台</h1>", unsafe_allow_html=True)
            tab_l, tab_r = st.tabs(["🔑 登录", "📝 注册"])
            with tab_l:
                email = st.text_input("邮箱", placeholder="请输入您的登录邮箱")
                pw = st.text_input("密码", type="password")
                if st.button("立即登录"):
                    user_data = login_user(email, pw)
                    if user_data:
                        st.session_state['user'] = {"id": user_data[0], "username": user_data[1], "role": user_data[2]}
                        st.rerun()
                    else: st.error("邮箱或密码错误")
            with tab_r:
                u, e, p, r, c = st.text_input("昵称"), st.text_input("邮箱"), st.text_input("密码", type="password"), st.selectbox("身份", ["individual", "org_admin"]), st.text_input("联系电话")
                if st.button("完成注册"):
                    success, msg = register_user(u, e, p, r, c); (st.success(msg) if success else st.error(msg))
            st.markdown('</div>', unsafe_allow_html=True)
# --- 6. 主系统界面 ---
else:
    user = st.session_state['user']
    render_top_nav(user['role'])
    
    page = st.session_state.get('page', '智能寻找')

    if page == "智能寻找":
        st.subheader("💖 正在等待领养的小可爱们")
        pets_df = fetch_all_pets()
        if pets_df.empty:
            st.info("所有小可爱都找到家啦！敬请期待新的伙伴到来。")
        else:
            cols = st.columns(3)
            for i, row in pets_df.iterrows():
                with cols[i % 3]:
                    st.markdown('<div class="pet-card">', unsafe_allow_html=True)
                    # 宠物图片占位符 - 请替换为真实图片路径或 URL
                    st.image("https://images.unsplash.com/photo-1596854407944-bf87f6fdd49e?q=80&w=880&auto=format&fit=crop", use_column_width=True,
                             output_format="PNG", extra_props={'class': 'pet-image'})
                    st.markdown(f'<p class="pet-name">{row["name"]}</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="pet-desc">{row["description"]}</p>', unsafe_allow_html=True)
                    if st.button(f"💬 和 {row['name']} 聊聊", key=f"chat_{row['id']}"):
                        st.session_state.chat_target = row.to_dict()
                        st.session_state.chat_history = [] # 清空历史
                    st.markdown('</div><br>', unsafe_allow_html=True)
        
        # 聊天模块
        if 'chat_target' in st.session_state:
            pet = st.session_state.chat_target
            st.divider()
            st.subheader(f"你正在和 **{pet['name']}** 聊天...")
            
            # 显示历史消息
            for msg in st.session_state.get('chat_history', []):
                with st.chat_message(msg['role'], avatar="🐾" if msg['role'] == 'assistant' else 'user'):
                    st.write(msg['content'])

            if prompt := st.chat_input(f"对 {pet['name']} 说点什么吧..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.write(prompt)

                with st.chat_message("assistant", avatar="🐾"):
                    with st.spinner("TA 正在组织语言..."):
                        resp_text, audio_b64 = run_pet_chat(prompt, pet['name'], pet['species'], pet['description'])
                        st.session_state.chat_history.append({"role": "assistant", "content": resp_text})
                        st.write(resp_text)
                        if audio_b64:
                            st.audio(base64.b64decode(audio_b64), format="audio/mp3", autoplay=True)

    elif page == "医疗预诊":
        st.subheader("🩺 AI 宠物全科医生")
        # 此处省略具体实现，保持框架清晰
        st.info("医疗预诊功能开发中...")

    elif page == "申请审核":
        st.subheader("⚖️ 领养申请审核")
        st.info("审核功能开发中...")

    # 在侧边栏放置一个固定的登出按钮
    st.sidebar.title(f"你好, {user['username']}")
    if st.sidebar.button("退出登录"):
        del st.session_state['user']
        if 'page' in st.session_state: del st.session_state['page']
        if 'chat_target' in st.session_state: del st.session_state['chat_target']
        st.rerun()
