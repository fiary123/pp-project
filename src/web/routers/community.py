from fastapi import APIRouter, UploadFile, File, HTTPException
from src.web.schemas import PostCreate, PostUpdate, CommentCreate, AnnouncementCreate, PetUpdate
from src.web.services.db_service import get_db_connection, ensure_tables
import os
import uuid
import shutil
from datetime import datetime

router = APIRouter(prefix="/api", tags=["community"])

UPLOAD_DIR = "static/uploads"

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"http://127.0.0.1:8000/static/uploads/{new_filename}"
    return {"status": "success", "url": url}

# --- Posts ---
@router.get("/posts")
def get_posts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT p.*, u.username, u.role FROM posts p JOIN users u ON p.user_id = u.id ORDER BY p.create_time DESC")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

@router.post("/posts")
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

@router.put("/posts/{post_id}")
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

@router.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    cursor.execute(
        "INSERT INTO moderation_logs (target_id, admin_id, reason, evidence_url) VALUES (?, ?, ?, ?)",
        (post_id, 0, "社区违规内容自动清理", ""),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.post("/posts/{post_id}/like")
async def like_post(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET likes = COALESCE(likes,0) + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.post("/posts/comment")
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

@router.get("/posts/{post_id}/comments")
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

# --- Pets ---
@router.get("/pets")
def get_all_pets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

@router.put("/pets/{pet_id}")
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

@router.delete("/pets/{pet_id}")
async def delete_pet(pet_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- Announcements ---
@router.get("/announcements")
def get_announcements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY date DESC")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return res

@router.post("/announcements")
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

@router.delete("/announcements/{id}")
async def delete_announcement(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM announcements WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
