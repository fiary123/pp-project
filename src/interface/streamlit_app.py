import streamlit as st
import os
import sys
import sqlite3
import pandas as pd
import time
import base64
import asyncio

# --- 1. 路径�?Agent 导入 ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.agents.agents import llm, run_knowledge_expert, run_pet_crew, run_pet_chat, run_audit_task
from src.agents.pet_expert import get_pet_expert_agent
from crewai import Task, Crew, Process
try:
    from src.database.db_config import SQLITE_DB_PATH
except ImportError:
    from ..database.db_config import SQLITE_DB_PATH

# --- 2. 主题配置系统 ---
if 'theme_color' not in st.session_state:
    st.session_state.theme_color = "简约蓝"
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

THEMES = {
    "简约蓝": {"primary": "#3B82F6", "bg_light": "#F3F4F6", "bg_dark": "#111827", "card_light": "#FFFFFF", "card_dark": "#1F2937"},
    "森林�?: {"primary": "#10B981", "bg_light": "#F0FDF4", "bg_dark": "#064E3B", "card_light": "#FFFFFF", "card_dark": "#065F46"},
    "樱花�?: {"primary": "#EC4899", "bg_light": "#FDF2F8", "bg_dark": "#500724", "card_light": "#FFFFFF", "card_dark": "#700B33"},
    "高级�?: {"primary": "#6B7280", "bg_light": "#F9FAFB", "bg_dark": "#111827", "card_light": "#FFFFFF", "card_dark": "#374151"}
}

current_theme = THEMES[st.session_state.theme_color]
bg_color = current_theme["bg_dark"] if st.session_state.dark_mode else current_theme["bg_light"]
card_color = current_theme["card_dark"] if st.session_state.dark_mode else current_theme["card_light"]
text_color = "#F9FAFB" if st.session_state.dark_mode else "#111827"
primary_color = current_theme["primary"]

st.set_page_config(page_title="智慧宠物平台", page_icon="🐾", layout="wide")

# 动态注�?CSS
st.markdown(f"""
<style>
    /* 隐藏默认装饰 */
    [data-testid="stHeader"], [data-testid="stDecoration"] {{ display: none !important; }}
    
    /* 全局背景与文字颜�?*/
    [data-testid="stAppViewContainer"] {{
        background-color: {bg_color};
        color: {text_color};
        transition: background-color 0.3s, color 0.3s;
    }}
    
    /* 侧边栏样�?*/
    [data-testid="stSidebar"] {{
        background-color: {card_color};
        border-right: 1px solid {primary_color}33;
    }}

    .stMarkdown, p, h1, h2, h3, h4, span, label {{
        color: {text_color} !important;
    }}

    /* 顶部导航�?*/
    .top-nav {{
        display: flex; justify-content: space-around; align-items: center;
        background: {card_color}; padding: 15px 10px; border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1); margin-bottom: 30px;
        border: 1px solid {primary_color}33;
    }}
    .nav-icon {{ font-size: 32px; }}
    .nav-text {{ font-size: 16px; font-weight: 700; margin-top: 5px; }}

    /* 宠物卡片 */
    .pet-card {{
        background: {card_color}; border-radius: 20px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
        transition: transform 0.3s; border: 1px solid {primary_color}22;
    }}
    .pet-card:hover {{ transform: translateY(-5px); border-color: {primary_color}; }}
    .pet-image {{ width: 100%; height: 180px; object-fit: cover; border-radius: 15px; margin-bottom: 15px; }}
    
    /* 自定义按钮样�?*/
    div.stButton > button {{
        background-color: {primary_color} !important;
        color: white !important;
        border-radius: 10px; border: none;
        padding: 0.5rem 1rem;
        transition: opacity 0.3s;
    }}
    div.stButton > button:hover {{
        opacity: 0.8;
        color: white !important;
    }}
    
    /* 登录容器 */
    .login-container {{
        background: {card_color}; padding: 50px; border-radius: 30px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.2); margin-top: 5vh;
        border: 1px solid {primary_color}33;
    }}
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
def fetch_all_pets(): return pd.read_sql_query("SELECT * FROM pets WHERE status='待领�?", sqlite3.connect(SQLITE_DB_PATH))

# --- 4. 侧边栏设�?---
st.sidebar.title("🎨 外观设置")
st.session_state.dark_mode = st.sidebar.toggle("深色模式", value=st.session_state.dark_mode)
st.session_state.theme_color = st.sidebar.selectbox("选择主题�?, list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme_color))

# --- 5. 导航栏渲�?---
def render_top_nav(role):
    menu_items = {"user": ["智能寻找", "我的申请", "发布送养"],
                  "admin": ["申请审核", "宠物上架", "数据大盘"]}
    icons = {"智能寻找": "🔍", "我的申请": "📋", "发布送养": "📤",
             "申请审核": "⚖️", "宠物上架": "�?, "数据大盘": "📈"}
    
    if 'page' not in st.session_state:
        st.session_state.page = menu_items[role][0]
    
    st.markdown('<div class="top-nav">', unsafe_allow_html=True)
    cols = st.columns(len(menu_items[role]))
    for i, item in enumerate(menu_items[role]):
        with cols[i]:
            if st.button(f'{icons[item]} {item}', key=f"nav_{item}", use_container_width=True):
                st.session_state.page = item
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. 登录/注册页面 ---
if 'user' not in st.session_state:
    _, center_col, _ = st.columns([1, 1.8, 1])
    with center_col:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:center; font-size: 52px; color: {primary_color};'>🐾 智慧宠物平台</h1>", unsafe_allow_html=True)
        tab_l, tab_r = st.tabs(["🔑 登录", "📝 注册"])
        with tab_l:
            email = st.text_input("邮箱", placeholder="请输入您的登录邮�?)
            pw = st.text_input("密码", type="password")
            if st.button("立即登录"):
                user_data = login_user(email, pw)
                if user_data:
                    st.session_state['user'] = {"id": user_data[0], "username": user_data[1], "role": user_data[2]}
                    st.rerun()
                else: st.error("邮箱或密码错�?)
        with tab_r:
            u, e, p, r, c = st.text_input("昵称"), st.text_input("邮箱"), st.text_input("密码", type="password"), st.selectbox("身份", ["user", "admin"]), st.text_input("联系电话")
            if st.button("完成注册"):
                success, msg = register_user(u, e, p, r, c); (st.success(msg) if success else st.error(msg))
        st.markdown('</div>', unsafe_allow_html=True)
# --- 7. 主系统界�?---
else:
    user = st.session_state['user']
    render_top_nav(user['role'])
    page = st.session_state.get('page', '智能寻找')

    if page == "智能寻找":
        st.subheader("💖 正在等待领养的小可爱�?)
        pets_df = fetch_all_pets()
        if pets_df.empty:
            st.info("所有小可爱都找到家啦！敬请期待新的伙伴到来�?)
        else:
            cols = st.columns(3)
            for i, row in pets_df.iterrows():
                with cols[i % 3]:
                    st.markdown(f'''<div class="pet-card">
                        <img src="https://images.unsplash.com/photo-1596854407944-bf87f6fdd49e?q=80&w=880&auto=format&fit=crop" class="pet-image">
                        <p class="pet-name">{row["name"]}</p>
                        <p class="pet-desc">{row["description"]}</p>
                    </div>''', unsafe_allow_html=True)
                    if st.button(f"💬 �?{row['name']} 聊聊", key=f"chat_{row['id']}"):
                        st.session_state.chat_target = row.to_dict()
                        st.session_state.chat_history = []
                    st.write("")
        
        if 'chat_target' in st.session_state:
            pet = st.session_state.chat_target
            st.divider()
            st.subheader(f"你正在和 **{pet['name']}** 聊天...")
            for msg in st.session_state.get('chat_history', []):
                with st.chat_message(msg['role'], avatar="🐾" if msg['role'] == 'assistant' else 'user'):
                    st.write(msg['content'])
            if prompt := st.chat_input(f"�?{pet['name']} 说点什么吧..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.write(prompt)
                with st.chat_message("assistant", avatar="🐾"):
                    with st.spinner("TA 正在组织语言..."):
                        resp_text, audio_b64 = asyncio.run(run_pet_chat(prompt, pet['name'], pet['species'], pet['description']))
                        st.session_state.chat_history.append({"role": "assistant", "content": resp_text})
                        st.write(resp_text)
                        if audio_b64:
                            st.audio(base64.b64decode(audio_b64), format="audio/mp3", autoplay=True)

    elif page == "申请审核":
        st.subheader("⚖️ 领养申请审核")
        st.info("审核功能开发中...")

    st.sidebar.divider()
    st.sidebar.title(f"👤 {user['username']}")
    if st.sidebar.button("退出登�?):
        del st.session_state['user']
        if 'page' in st.session_state: del st.session_state['page']
        if 'chat_target' in st.session_state: del st.session_state['chat_target']
        st.rerun()
