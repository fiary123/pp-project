from fastapi import APIRouter, HTTPException
from src.web.schemas import ChangePasswordRequest, MessageCreate
from src.web.services.db_service import get_db_connection, ensure_tables

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/change-password")
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

@router.get("/applications/{user_id}")
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

@router.get("/messages/{user_id}")
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

@router.post("/messages/send")
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
