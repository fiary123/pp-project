from fastapi import APIRouter, Depends
from src.web.schemas import UserSanctionRequest, ApplicationUpdateRequest
from src.web.services.db_service import get_db_connection, ensure_tables
from src.web.dependencies import require_admin

# 在 APIRouter 级别添加依赖，使得该文件下所有路由默认受保护
router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/users")
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

@router.post("/users/sanction")
async def sanction_user(req: UserSanctionRequest, current_admin: dict = Depends(require_admin)):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    next_status = "muted" if req.type == "muted" else "banned"
    cursor.execute("UPDATE users SET status=? WHERE id=?", (next_status, req.user_id))
    # 记录日志，使用当前管理员的真实 ID
    cursor.execute(
        "INSERT INTO user_sanctions (user_id, admin_id, type, reason, evidence_url) VALUES (?, ?, ?, ?, ?)",
        (req.user_id, current_admin["id"], req.type.upper(), req.reason, req.evidence),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.post("/users/reactivate")
async def reactivate_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.get("/moderation/logs")
def get_moderation_logs():
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM moderation_logs ORDER BY delete_time DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@router.get("/applications")
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

@router.post("/applications/update")
async def update_application(req: ApplicationUpdateRequest):
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status=? WHERE id=?", (req.status, req.app_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.get("/ai/traces")
def get_ai_traces():
    """获取 AI 智能体执行日志"""
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_trace_logs ORDER BY create_time DESC LIMIT 100")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
