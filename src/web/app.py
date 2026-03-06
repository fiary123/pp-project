# FastAPI 后端接口服务
import os
import sys
import sqlite3
import shutil
import json
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime

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

# 配置文件上传目录
UPLOAD_DIR = "static/uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 挂载静态文件目录，使得上传的图片可以通过浏览器访问
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 大模型配置 ---
client = OpenAI(
    api_key="sk-c69656763f3a49bc9650e243c5ce0542", 
    base_url="https://api.deepseek.com" 
)

# --- 模型定义 ---
class LoginRequest(BaseModel):
    email: str
    password: str

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None

class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_hot: Optional[int] = 0

# --- 辅助函数 ---
def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- API 接口 ---

# 0. 文件上传接口 (支持本地图片)
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # 生成唯一文件名防止覆盖
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 返回相对路径，前端拼接后端地址即可访问
    url = f"http://127.0.0.1:8000/static/uploads/{new_filename}"
    return {"status": "success", "url": url}

# 1. 用户认证
@app.post("/api/login")
async def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (req.email, req.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "success", "user": {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]}}
    raise HTTPException(status_code=401, detail="邮箱或密码错误")

# 2. 社区帖子管理
@app.get("/api/posts")
def get_posts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT p.*, u.username, u.role FROM posts p JOIN users u ON p.user_id = u.id ORDER BY p.create_time DESC")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

@app.post("/api/posts")
async def publish_post(user_id: int = Form(...), title: str = Form(...), content: str = Form(...), type: str = Form("daily"), image_url: str = Form(None)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (user_id, title, content, image_url, type) VALUES (?, ?, ?, ?, ?)",
                   (user_id, title, content, image_url, type))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.put("/api/posts/{post_id}")
async def update_post(post_id: int, req: PostUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET title=COALESCE(?,title), content=COALESCE(?,content), image_url=COALESCE(?,image_url) WHERE id=?", 
                   (req.title, req.content, req.image_url, post_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# 3. 宠物管理
@app.get("/api/pets")
def get_all_pets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

@app.put("/api/pets/{pet_id}")
async def update_pet(pet_id: int, req: PetUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE pets SET name=COALESCE(?,name), species=COALESCE(?,species), image_url=COALESCE(?,image_url), description=COALESCE(?,description) WHERE id=?", 
                   (req.name, req.species, req.image_url, req.description, pet_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/pets/{pet_id}")
async def delete_pet(pet_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# 4. 公告管理
@app.get("/api/announcements")
def get_announcements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY date DESC")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

@app.post("/api/announcements")
async def create_announcement(req: AnnouncementCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcements (title, content, is_hot, date) VALUES (?, ?, ?, ?)", 
                   (req.title, req.content, req.is_hot, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/announcements/{id}")
async def delete_announcement(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM announcements WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT c.*, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE post_id = ?", (post_id,))
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
