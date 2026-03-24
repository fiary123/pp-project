from fastapi import APIRouter, HTTPException, Depends, Body
from src.web.schemas import ChangePasswordRequest, MessageCreate
from src.web.services.db_service import get_db, ensure_tables
from src.web.services.auth_service import verify_password, get_password_hash
from src.web.dependencies import get_current_user
from src.web.services.credit_service import CreditService
from src.web.services.ai_service import ai_service

router = APIRouter(prefix="/api/user", tags=["user"])
credit_service = CreditService(ai_service)

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    # 只允许修改自己的密码
    if current_user["id"] != req.user_id:
        raise HTTPException(status_code=403, detail="无权限修改他人密码")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id=?", (req.user_id,))
        row = cursor.fetchone()
        if not row or not verify_password(req.old_password, row["password"]):
            raise HTTPException(status_code=400, detail="旧密码错误")
        hashed_new = get_password_hash(req.new_password)
        cursor.execute("UPDATE users SET password=? WHERE id=?", (hashed_new, req.user_id))
        conn.commit()
    return {"status": "success"}

@router.get("/applications/{user_id}")
def get_user_applications(user_id: int, current_user: dict = Depends(get_current_user)):
    # 只允许查询自己的申请（管理员除外）
    if current_user["id"] != user_id and current_user.get("role") not in ["org_admin"]:
        raise HTTPException(status_code=403, detail="无权限查询他人申请")
    with get_db() as conn:
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
    return rows

@router.get("/messages/{user_id}")
def get_messages(user_id: int, current_user: dict = Depends(get_current_user)):
    # 只允许查询自己的消息
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="无权限查询他人消息")
    with get_db() as conn:
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
    return rows

@router.get("/messages/{user_id}/contacts")
def get_contacts(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取当前用户的联系人列表（按最新消息时间排序，附带最后一条消息预览）"""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="无权限查询他人联系人")
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                other_id,
                u.username AS other_name,
                last_msg,
                last_time
            FROM (
                SELECT
                    CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS other_id,
                    content AS last_msg,
                    create_time AS last_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
                        ORDER BY create_time DESC
                    ) AS rn
                FROM messages
                WHERE sender_id = ? OR receiver_id = ?
            ) t
            LEFT JOIN users u ON u.id = t.other_id
            WHERE t.rn = 1
            ORDER BY last_time DESC
            """,
            (user_id, user_id, user_id, user_id),
        )
        rows = [dict(r) for r in cursor.fetchall()]
    return rows


@router.get("/messages/{user_id}/with/{other_id}")
def get_conversation(user_id: int, other_id: int, current_user: dict = Depends(get_current_user)):
    """获取与指定用户的对话记录"""
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="无权限查询他人消息")
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.*, su.username AS sender_name, ru.username AS receiver_name
            FROM messages m
            LEFT JOIN users su ON su.id = m.sender_id
            LEFT JOIN users ru ON ru.id = m.receiver_id
            WHERE (m.sender_id = ? AND m.receiver_id = ?)
               OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.create_time ASC
            """,
            (user_id, other_id, other_id, user_id),
        )
        rows = [dict(r) for r in cursor.fetchall()]
    return rows


@router.post("/messages/send")
async def send_message(req: MessageCreate, current_user: dict = Depends(get_current_user)):
    # 只允许以自己身份发送消息
    if current_user["id"] != req.sender_id:
        raise HTTPException(status_code=403, detail="无权限以他人身份发送消息")
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (req.sender_id, req.receiver_id, req.content),
        )
        conn.commit()
    return {"status": "success"}

@router.get("/credit")
async def get_my_credit(current_user: dict = Depends(get_current_user)):
    """获取我的信用档案"""
    profile = credit_service.get_user_credit(current_user["id"])
    if not profile:
        # 如果没记录，尝试初始化一个
        await credit_service.add_credit_event(current_user["id"], "initial", "")
        profile = credit_service.get_user_credit(current_user["id"])
    return profile

@router.post("/credit/task/visit_report")
async def submit_visit_report(
    content: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """提交宠物回访任务，触发 AI 评分"""
    result = await credit_service.add_credit_event(
        current_user["id"], 
        "visit_report", 
        content
    )
    return {
        "message": "回访提交成功，AI 已完成评估",
        "points_earned": result["points"],
        "quality_multiplier": result["multiplier"]
    }
