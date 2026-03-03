# FastAPI 后端接口服务
import os
import sys
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI  # 新增：引入大模型 SDK

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db_config import SQLITE_DB_PATH

app = FastAPI(title="智能宠物领养平台 API")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 大模型配置 ---
# 建议通过环境变量设置 API Key，或者直接在这里替换
# 这里以 OpenAI/DeepSeek 兼容格式为例
client = OpenAI(
    api_key="sk-c69656763f3a49bc9650e243c5ce0542", # TODO: 替换为真实的 API Key
    base_url="https://api.deepseek.com" # 如果用 DeepSeek 改为此 URL，用 OpenAI 删掉这行
)

# --- 模型定义 ---
class ChatRequest(BaseModel):
    message: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "individual"

# --- 辅助函数 ---
def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- API 接口 ---

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    智能对话接口：接入大模型实现全知全能的问答
    """
    try:
        print(f"用户提问: {request.message}")
        
        # 调用大模型
        response = client.chat.completions.create(
            model="deepseek-chat", # 或者 "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "你是一位专业的宠物百科专家和全能生活助理。你精通各种宠物的习性、疾病预防、喂养技巧，也能回答用户关于生活、情感、技术的任何通用问题。"},
                {"role": "user", "content": request.message}
            ],
            stream=False
        )
        
        ai_reply = response.choices[0].message.content
        return {"status": "success", "reply": ai_reply}
        
    except Exception as e:
        print(f"大模型调用失败: {str(e)}")
        return {
            "status": "error", 
            "reply": f"AI 暂时去休息了（报错: {str(e)}）。请检查 API Key 或网络连接。"
        }

@app.post("/api/login")
def login_endpoint(request: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users WHERE email = ? AND password = ?", 
                   (request.email, request.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "success", "user": dict(user)}
    raise HTTPException(status_code=401, detail="邮箱或密码错误")

@app.post("/api/register")
def register_endpoint(request: RegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (request.username, request.email, request.password, request.role)
        )
        conn.commit()
        return {"status": "success", "message": "注册成功"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    finally:
        conn.close()

@app.get("/api/pets")
def get_all_pets(species: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pets

if __name__ == "__main__":
    import uvicorn
    print("🚀 后端大模型接口已就绪！")
    uvicorn.run(app, host="127.0.0.1", port=8000)
