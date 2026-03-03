# FastAPI 后端接口服务
import os
import sys
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db_config import SQLITE_DB_PATH
try:
    from src.agents.agents import run_pet_crew
except ImportError:
    from ..agents.agents import run_pet_crew

app = FastAPI(title="智能宠物领养平台 API")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 模型定义 ---
class ChatRequest(BaseModel):
    message: str

class AdoptionRequest(BaseModel):
    pet_id: int
    user_name: str
    contact: str
    reason: str

# --- 辅助函数 ---
def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典形式的结果
    return conn

# --- API 接口 ---

@app.get("/api/pets")
def get_all_pets(species: Optional[str] = None):
    """获取所有待领养宠物（支持按种类筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if species:
        cursor.execute("SELECT * FROM pets WHERE status = '待领养' AND species LIKE ?", (f'%{species}%',))
    else:
        cursor.execute("SELECT * FROM pets WHERE status = '待领养'")
    pets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return pets

@app.get("/api/pets/{pet_id}")
def get_pet_detail(pet_id: int):
    """获取宠物详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets WHERE id = ?", (pet_id,))
    pet = cursor.fetchone()
    conn.close()
    if not pet:
        raise HTTPException(status_code=404, detail="宠物不存在")
    return dict(pet)

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    """智能对话接口"""
    try:
        print(f"收到用户消息: {request.message}")
        ai_response = run_pet_crew(request.message)
        return {"status": "success", "reply": ai_response}
    except Exception as e:
        return {"status": "error", "reply": f"系统大脑开小差了: {str(e)}"}

@app.post("/api/adopt")
def apply_adoption(request: AdoptionRequest):
    """提交领养申请"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO applications (pet_id, user_name, contact, reason) VALUES (?, ?, ?, ?)",
            (request.pet_id, request.user_name, request.contact, request.reason)
        )
        conn.commit()
        return {"status": "success", "message": "申请已提交，请等待 AI 评估和管理员审核"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    print("🚀 API 后端服务启动于 http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
