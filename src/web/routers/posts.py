from fastapi import APIRouter, HTTPException, Depends
from src.web.schemas import PostCreate, PostUpdate, CommentCreate
from src.web.services.db_service import get_db, ensure_tables
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["posts"])


@router.get("/posts")
def get_posts(skip: int = 0, limit: int = 20):
    if limit > 100:
        limit = 100
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.id, p.user_id, p.title, p.content, p.image_url,
                   p.type, p.likes, p.create_time,
                   u.username, u.role
            FROM posts p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.create_time DESC
            LIMIT ? OFFSET ?
            """,
            (limit, skip),
        )
        items = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM posts")
        total = cursor.fetchone()[0]
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.post("/posts")
async def publish_post(req: PostCreate, current_user: dict = Depends(get_current_user)):
    if current_user["id"] != req.user_id:
        raise HTTPException(status_code=403, detail="无权限以他人身份发帖")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO posts (user_id, title, content, image_url, type) VALUES (?, ?, ?, ?, ?)",
            (req.user_id, req.title, req.content, req.image_url, req.type),
        )
        conn.commit()
    return {"status": "success"}


@router.put("/posts/{post_id}")
async def update_post(post_id: int, req: PostUpdate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM posts WHERE id=?", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if post["user_id"] != current_user["id"] and current_user.get("role") not in ["org_admin"]:
            raise HTTPException(status_code=403, detail="无权限修改他人帖子")
        cursor.execute(
            "UPDATE posts SET title=COALESCE(?,title), content=COALESCE(?,content), image_url=COALESCE(?,image_url) WHERE id=?",
            (req.title, req.content, req.image_url, post_id),
        )
        conn.commit()
    return {"status": "success"}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM posts WHERE id=?", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if post["user_id"] != current_user["id"] and current_user.get("role") not in ["org_admin"]:
            raise HTTPException(status_code=403, detail="无权限删除他人帖子")
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        cursor.execute(
            "INSERT INTO moderation_logs (target_id, admin_id, reason, evidence_url) VALUES (?, ?, ?, ?)",
            (post_id, current_user["id"], "用户删除帖子", ""),
        )
        conn.commit()
    return {"status": "success"}


@router.post("/posts/{post_id}/like")
async def like_post(post_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET likes = COALESCE(likes,0) + 1 WHERE id = ?", (post_id,))
        conn.commit()
    return {"status": "success"}


@router.post("/posts/comment")
async def create_comment(req: CommentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["id"] != req.user_id:
        raise HTTPException(status_code=403, detail="无权限以他人身份评论")
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
            (req.post_id, req.user_id, req.content),
        )
        conn.commit()
    return {"status": "success"}


@router.get("/posts/{post_id}/comments")
def get_comments(post_id: int):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT c.*, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE post_id = ? ORDER BY c.create_time ASC",
            (post_id,),
        )
        res = [dict(row) for row in cursor.fetchall()]
    return res
