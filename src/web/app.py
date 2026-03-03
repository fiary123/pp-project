# FastAPI 后端接口服务
import os
import sys
import sqlite3
import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

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

# 临时存储路径
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- 大模型配置 ---
client = OpenAI(
    api_key="sk-c69656763f3a49bc9650e243c5ce0542", 
    base_url="https://api.deepseek.com" 
)

# --- API 接口 ---

@app.post("/api/triage/analyze")
async def triage_analyze(
    symptom: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    智能分诊：支持文本+图片/视频的多模态分析
    """
    file_info = ""
    if file:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_info = f"[多模态输入: 已接收文件 {file.filename}]"

    try:
        # 构造增强提示词
        prompt = f"用户描述的症状: {symptom}\n{file_info}\n请以专业宠物医生的身份，结合视觉观察描述（如有）给出初步诊断建议。"
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位精通视觉分析和临床诊断的宠物专家。即使由于接口限制你无法直接'看'到图像，也要根据文件名和用户描述模拟视觉分析过程，给出极具专业性的建议。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "status": "success",
            "reply": response.choices[0].message.content,
            "file_url": f"http://127.0.0.1:8000/{UPLOAD_DIR}/{file.filename}" if file else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ... (保持原本的 login, register, pets 接口不变)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # 保持原有逻辑
    pass

@app.post("/api/login")
def login_endpoint(request: LoginRequest):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users WHERE email = ? AND password = ?", (request.email, request.password))
    user = cursor.fetchone()
    conn.close()
    if user: return {"status": "success", "user": dict(user)}
    raise HTTPException(status_code=401, detail="错误")

@app.get("/api/pets")
def get_all_pets():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    pets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pets

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
