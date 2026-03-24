from fastapi import APIRouter, Depends
from src.web.schemas import UserSanctionRequest, ApplicationUpdateRequest
from src.web.services.db_service import get_db_connection, ensure_tables
from src.web.dependencies import require_admin

# 在 APIRouter 级别添加依赖，使得该文件下所有路由默认受保护
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

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


# ══════════════════════════════════════════════════════
# 互助平台管理接口
# ══════════════════════════════════════════════════════

@router.get("/mutual-aid/stats")
def get_mutual_aid_stats():
    """互助平台统计数据"""
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    # 总任务数
    cursor.execute("SELECT COUNT(*) FROM mutual_aid_tasks")
    total = cursor.fetchone()[0]
    # 各状态数量
    cursor.execute("SELECT status, COUNT(*) as cnt FROM mutual_aid_tasks GROUP BY status")
    status_map = {r[0]: r[1] for r in cursor.fetchall()}
    # 今日发布
    cursor.execute("SELECT COUNT(*) FROM mutual_aid_tasks WHERE DATE(create_time)=DATE('now')")
    today_new = cursor.fetchone()[0]
    # 接单率
    accepted = status_map.get('accepted', 0) + status_map.get('completed', 0)
    accept_rate = round(accepted / total * 100, 1) if total > 0 else 0
    # 完成率
    completed = status_map.get('completed', 0)
    complete_rate = round(completed / total * 100, 1) if total > 0 else 0
    # 待处理举报
    cursor.execute("SELECT COUNT(*) FROM mutual_aid_reports WHERE status='pending'")
    pending_reports = cursor.fetchone()[0]
    conn.close()
    return {
        "total": total,
        "open": status_map.get('open', 0),
        "accepted": status_map.get('accepted', 0),
        "completed": completed,
        "cancelled": status_map.get('cancelled', 0),
        "today_new": today_new,
        "accept_rate": accept_rate,
        "complete_rate": complete_rate,
        "pending_reports": pending_reports,
    }


@router.get("/mutual-aid/tasks")
def get_all_mutual_aid_tasks(status: str = "", limit: int = 50):
    """查看所有互助任务（含发布人信息）"""
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    if status:
        cursor.execute(
            """SELECT t.*, u.username as publisher_name, u.email as publisher_email
               FROM mutual_aid_tasks t
               LEFT JOIN users u ON t.user_id = u.id
               WHERE t.status=? ORDER BY t.create_time DESC LIMIT ?""",
            (status, limit)
        )
    else:
        cursor.execute(
            """SELECT t.*, u.username as publisher_name, u.email as publisher_email
               FROM mutual_aid_tasks t
               LEFT JOIN users u ON t.user_id = u.id
               ORDER BY t.create_time DESC LIMIT ?""",
            (limit,)
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@router.post("/mutual-aid/tasks/{task_id}/cancel")
async def admin_cancel_task(task_id: int, body: dict, current_admin: dict = Depends(require_admin)):
    """管理员强制下架互助任务"""
    reason = body.get("reason", "违规内容")
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mutual_aid_tasks WHERE id=?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="任务不存在")
    cursor.execute("UPDATE mutual_aid_tasks SET status='cancelled' WHERE id=?", (task_id,))
    # 记录到 moderation_logs
    cursor.execute(
        "INSERT INTO moderation_logs (target_id, admin_id, reason) VALUES (?,?,?)",
        (task_id, current_admin["id"], f"[互助任务下架] {reason}")
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/mutual-aid/reports")
def get_mutual_aid_reports(status: str = "pending"):
    """获取举报列表（含任务和举报人信息）"""
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT r.*,
               u.username as reporter_name,
               t.task_type, t.pet_name, t.location, t.status as task_status,
               t.user_id as task_owner_id,
               ou.username as task_owner_name
           FROM mutual_aid_reports r
           LEFT JOIN users u ON r.reporter_id = u.id
           LEFT JOIN mutual_aid_tasks t ON r.task_id = t.id
           LEFT JOIN users ou ON t.user_id = ou.id
           WHERE r.status=?
           ORDER BY r.create_time DESC""",
        (status,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@router.post("/mutual-aid/reports/{report_id}/resolve")
async def resolve_mutual_aid_report(report_id: int, body: dict, current_admin: dict = Depends(require_admin)):
    """
    仲裁举报：
    action = 'cancel'   → 下架任务 + 可选封禁发布人
    action = 'dismiss'  → 驳回举报
    """
    action = body.get("action", "dismiss")   # cancel | dismiss
    note = body.get("note", "")
    ban_publisher = body.get("ban_publisher", False)
    ban_reason = body.get("ban_reason", "")

    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()

    # 查举报详情
    cursor.execute(
        "SELECT r.task_id, t.user_id FROM mutual_aid_reports r LEFT JOIN mutual_aid_tasks t ON r.task_id=t.id WHERE r.id=?",
        (report_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="举报记录不存在")

    task_id, task_owner_id = row[0], row[1]
    new_status = "resolved_cancel" if action == "cancel" else "resolved_dismiss"

    # 更新举报状态
    cursor.execute(
        "UPDATE mutual_aid_reports SET status=?, resolve_note=?, admin_id=?, resolve_time=CURRENT_TIMESTAMP WHERE id=?",
        (new_status, note, current_admin["id"], report_id)
    )

    if action == "cancel":
        # 下架任务
        cursor.execute("UPDATE mutual_aid_tasks SET status='cancelled' WHERE id=?", (task_id,))
        cursor.execute(
            "INSERT INTO moderation_logs (target_id, admin_id, reason) VALUES (?,?,?)",
            (task_id, current_admin["id"], f"[举报仲裁-下架] {note}")
        )
        # 可选封禁发布人
        if ban_publisher and task_owner_id:
            cursor.execute("UPDATE users SET status='banned' WHERE id=?", (task_owner_id,))
            cursor.execute(
                "INSERT INTO user_sanctions (user_id, admin_id, type, reason) VALUES (?,?,?,?)",
                (task_owner_id, current_admin["id"], "BAN", ban_reason or f"互助举报仲裁封禁：{note}")
            )

    conn.commit()
    conn.close()
    return {"status": "success"}
