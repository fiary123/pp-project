# FastAPI 后端接口服务
import os
import sys
import sqlite3
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database.db_config import SQLITE_DB_PATH
from src.agents.nutrition_planner import build_nutrition_plan, render_nutrition_markdown

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
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 挂载静态文件目录，使得上传的图片可以通过浏览器访问
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- 模型定义 ---
class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Literal["individual", "org_admin", "root"] = "individual"


class PostCreate(BaseModel):
    user_id: int
    title: Optional[str] = None
    content: str
    type: str = "daily"
    image_url: Optional[str] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None


class CommentCreate(BaseModel):
    post_id: int
    user_id: int
    content: str


class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_hot: Optional[int] = 0


class NutritionPlanRequest(BaseModel):
    species: Literal["cat", "dog"]
    age_months: int = Field(ge=0, le=400)
    weight_kg: float = Field(gt=0, le=150)
    neutered: bool = False
    activity_level: Literal["low", "medium", "high"] = "medium"
    goal: Literal["maintain", "lose_weight", "gain_weight"] = "maintain"
    food_kcal_per_100g: float = Field(default=360, gt=0, le=900)
    symptoms: List[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str


class TriageRequest(BaseModel):
    symptom: str
    location: Optional[str] = None


class MessageCreate(BaseModel):
    sender_id: int
    receiver_id: int
    content: str


class ChangePasswordRequest(BaseModel):
    user_id: int
    old_password: str
    new_password: str


class ApplicationUpdateRequest(BaseModel):
    app_id: int
    status: str


class UserSanctionRequest(BaseModel):
    user_id: int
    admin_id: int
    type: Literal["muted", "banned"]
    reason: str
    evidence: Optional[str] = ""


class SmartMatchRequest(BaseModel):
    user_query: str
    pet_list: List[dict] = Field(default_factory=list)


# --- 辅助函数 ---
def get_db_connection():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'individual',
        status TEXT DEFAULT 'active',
        occupation TEXT,
        contact TEXT
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        content TEXT NOT NULL,
        image_url TEXT,
        type TEXT DEFAULT 'daily',
        likes INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pet_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT '待审核',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        user_id INTEGER,
        parent_id INTEGER DEFAULT NULL,
        content TEXT NOT NULL,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_id INTEGER,
        admin_id INTEGER,
        reason TEXT NOT NULL,
        evidence_url TEXT,
        delete_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS user_sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        admin_id INTEGER,
        type TEXT NOT NULL,
        reason TEXT NOT NULL,
        evidence_url TEXT,
        expire_date DATETIME,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()


def _try_agent_reply(user_msg: str) -> str:
    """优先走多智能体，失败时回退到可用回复。"""
    try:
        from src.agents.agents import run_knowledge_expert
        return run_knowledge_expert(user_msg)
    except Exception:
        return f"已收到你的问题：{user_msg}。建议先提供宠物年龄、体重、品种与当前症状，我会给你更具体建议。"


# --- API 接口 ---

# 0. 文件上传接口 (支持本地图片)
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"http://127.0.0.1:8000/static/uploads/{new_filename}"
    return {"status": "success", "url": url}


# 1. 用户认证
@app.post("/api/login")
async def login(req: LoginRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (req.email, req.password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"status": "success", "user": {"id": user["id"], "username": user["username"], "email": user["email"], "role": user["role"]}}
    raise HTTPException(status_code=401, detail="邮箱或密码错误")


@app.post("/api/register")
async def register(req: RegisterRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (req.username, req.email, req.password, req.role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="邮箱已注册")
    conn.close()
    return {"status": "success"}


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
async def publish_post(req: PostCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posts (user_id, title, content, image_url, type) VALUES (?, ?, ?, ?, ?)",
        (req.user_id, req.title, req.content, req.image_url, req.type),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.put("/api/posts/{post_id}")
async def update_post(post_id: int, req: PostUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE posts SET title=COALESCE(?,title), content=COALESCE(?,content), image_url=COALESCE(?,image_url) WHERE id=?",
        (req.title, req.content, req.image_url, post_id),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    cursor.execute(
        "INSERT INTO moderation_logs (target_id, admin_id, reason, evidence_url) VALUES (?, ?, ?, ?)",
        (post_id, 0, "管理员删除帖子", ""),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: int):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET likes = COALESCE(likes,0) + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/posts/comment")
async def create_comment(req: CommentCreate):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
        (req.post_id, req.user_id, req.content),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.*, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE post_id = ? ORDER BY c.create_time ASC",
        (post_id,),
    )
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res


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
    cursor.execute(
        "UPDATE pets SET name=COALESCE(?,name), species=COALESCE(?,species), image_url=COALESCE(?,image_url), description=COALESCE(?,description) WHERE id=?",
        (req.name, req.species, req.image_url, req.description, pet_id),
    )
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


@app.post("/api/pets/smart-match")
async def smart_match(req: SmartMatchRequest):
    query = req.user_query.lower()
    pets = req.pet_list

    # 优先尝试多智能体
    try:
        from src.agents.agents import run_pet_crew
        _ = run_pet_crew(req.user_query)
    except Exception:
        pass

    scored = []
    for pet in pets:
        text = f"{pet.get('name','')} {pet.get('species','')} {pet.get('desc','')} {' '.join(pet.get('tags', []))}".lower()
        score = 0
        for word in query.replace('，', ',').split(','):
            w = word.strip()
            if w and w in text:
                score += 1
        scored.append((score, pet))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [
        {
            "id": p.get("id"),
            "reason": f"匹配命中 {s} 个关键词，建议优先了解其性格与护理要求。",
        }
        for s, p in scored[:5]
        if p.get("id") is not None
    ]
    return {"matches": matches}


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
    cursor.execute(
        "INSERT INTO announcements (title, content, is_hot, date) VALUES (?, ?, ?, ?)",
        (req.title, req.content, req.is_hot, datetime.now().strftime("%Y-%m-%d")),
    )
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


# 5. 聊天/分诊/百科
@app.post("/api/chat")
async def chat(req: ChatRequest):
    return {"reply": _try_agent_reply(req.message)}


@app.post("/api/triage/analyze")
async def triage_analyze(symptom: str = Form(...), file: UploadFile = File(None)):
    _ = file
    try:
        from src.agents.agents import run_triage_expert
        return {"reply": run_triage_expert(symptom)}
    except Exception:
        triage_text = f"【初步分诊】已识别症状：{symptom}。建议先观察精神、饮水、体温，并记录24小时变化。"
        if any(k in symptom for k in ["抽搐", "昏迷", "便血", "呼吸困难"]):
            triage_text += "\n风险等级：紧急就医。请尽快前往最近宠物医院。"
        else:
            triage_text += "\n风险等级：建议就医（非急症）。"
        return {"reply": triage_text}


# 6. 营养专家
@app.post("/api/nutrition/plan")
async def create_nutrition_plan(req: NutritionPlanRequest):
    plan = build_nutrition_plan(**req.model_dump())
    markdown = render_nutrition_markdown(req.species, plan)
    return {"status": "success", "plan": plan, "explanation_markdown": markdown}


# 7. 私信
@app.get("/api/messages/{user_id}")
def get_messages(user_id: int):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*, su.username AS sender_name, ru.username AS receiver_name
        FROM messages m
        LEFT JOIN users su ON su.id = m.sender_id
        LEFT JOIN users ru ON ru.id = m.receiver_id
        WHERE m.sender_id = ? OR m.receiver_id = ?
        ORDER BY m.create_time ASC
        """,
        (user_id, user_id),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@app.post("/api/messages/send")
async def send_message(req: MessageCreate):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
        (req.sender_id, req.receiver_id, req.content),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


# 8. 用户中心
@app.post("/api/user/change-password")
async def change_password(req: ChangePasswordRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE id=?", (req.user_id,))
    row = cursor.fetchone()
    if not row or row["password"] != req.old_password:
        conn.close()
        raise HTTPException(status_code=400, detail="旧密码错误")
    cursor.execute("UPDATE users SET password=? WHERE id=?", (req.new_password, req.user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/api/user/applications/{user_id}")
def get_user_applications(user_id: int):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(applications)")
    cols = {r[1] for r in cursor.fetchall()}
    if "user_id" in cols:
        order_col = "create_time" if "create_time" in cols else "id"
        cursor.execute(
            f"SELECT * FROM applications WHERE user_id=? ORDER BY {order_col} DESC",
            (user_id,),
        )
    else:
        cursor.execute("SELECT * FROM applications ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# 9. 管理后台
@app.get("/api/admin/users")
def get_admin_users():
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in cursor.fetchall()}
    select_cols = ["id", "username", "email", "role"]
    for c in ["status", "occupation", "contact"]:
        if c in cols:
            select_cols.append(c)
    cursor.execute(f"SELECT {', '.join(select_cols)} FROM users ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@app.post("/api/admin/users/sanction")
async def sanction_user(req: UserSanctionRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    next_status = "muted" if req.type == "muted" else "banned"
    cursor.execute("UPDATE users SET status=? WHERE id=?", (next_status, req.user_id))
    cursor.execute(
        "INSERT INTO user_sanctions (user_id, admin_id, type, reason, evidence_url) VALUES (?, ?, ?, ?, ?)",
        (req.user_id, req.admin_id, req.type.upper(), req.reason, req.evidence),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/admin/users/reactivate")
async def reactivate_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/api/admin/moderation/logs")
def get_moderation_logs():
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM moderation_logs ORDER BY delete_time DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@app.get("/api/admin/applications")
def get_admin_applications():
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(applications)")
    cols = {r[1] for r in cursor.fetchall()}
    order_col = "create_time" if "create_time" in cols else "id"
    cursor.execute(f"SELECT * FROM applications ORDER BY {order_col} DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@app.post("/api/admin/applications/update")
async def update_application(req: ApplicationUpdateRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status=? WHERE id=?", (req.status, req.app_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
