import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from src.web.schemas import UserSanctionRequest, ApplicationUpdateRequest, TakedownRequest
from src.web.services.db_service import get_db_connection, ensure_tables, get_db
from src.web.services.adoption_flow_engine import flow_engine
from src.web.services.adoption_memory import build_closed_loop_stats
from src.web.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

def _parse_json(raw_value, fallback):
    if raw_value in (None, "", b""): return fallback
    try:
        return json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except: return fallback

def _send_notification(conn, user_id: int, type: str, title: str, content: str):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (user_id, type, title, content) VALUES (?, ?, ?, ?)",
        (user_id, type, title, content)
    )

@router.get("/overview/stats")
def get_overview_stats():
    # 评审说明：
    # 该接口为后台总览页提供用户、帖子、申请和趋势图等聚合指标。
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    
    # 默认兜底数据
    res = {
        "summary": {
            "total_users": 0, "total_posts": 0, "successful_adoptions": 0, "total_applications": 0,
            "pets_waiting": 0, "total_pets": 0, "total_announcements": 0, "total_ai_traces": 0,
            "owner_followed_ai": 0, "owner_rejected_ai": 0
        },
        "post_breakdown": {"daily": 0, "experience": 0, "adopt_help": 0},
        "application_breakdown": {"pending": 0, "approved": 0, "rejected": 0},
        "recent_posts": [], "recent_applications": []
    }

    try:
        # 1. 基础总数统计
        cursor.execute("SELECT COUNT(*) FROM users")
        res["summary"]["total_users"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM posts")
        res["summary"]["total_posts"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT type, COUNT(*) FROM posts GROUP BY type")
        for r in cursor.fetchall():
            if r[0] in res["post_breakdown"]: res["post_breakdown"][r[0]] = r[1]

        cursor.execute("SELECT COUNT(*) FROM applications")
        res["summary"]["total_applications"] = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
        for r in cursor.fetchall():
            res["application_breakdown"][r[0]] = r[1]

        # 2. 增强统计 (增加容错)
        try:
            cursor.execute("SELECT COUNT(*) FROM applications WHERE owner_followed_ai = 1")
            res["summary"]["owner_followed_ai"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM applications WHERE owner_followed_ai = 0")
            res["summary"]["owner_rejected_ai"] = cursor.fetchone()[0]
        except: pass

        cursor.execute("SELECT COUNT(*) FROM adopt_records")
        res["summary"]["successful_adoptions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pets")
        res["summary"]["total_pets"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pets WHERE status='待领养'")
        res["summary"]["pets_waiting"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM announcements")
        res["summary"]["total_announcements"] = cursor.fetchone()[0]

        try:
            cursor.execute("SELECT COUNT(*) FROM agent_trace_logs")
            res["summary"]["total_ai_traces"] = cursor.fetchone()[0]
        except: pass

        # 3. 趋势图统计
        cursor.execute("SELECT strftime('%m-%d', create_time) as d, COUNT(*) as cnt FROM posts GROUP BY d ORDER BY d DESC LIMIT 7")
        res["recent_posts"] = [dict(r) for r in cursor.fetchall()][::-1]

        cursor.execute("SELECT strftime('%m-%d', create_time) as d, COUNT(*) as cnt FROM applications GROUP BY d ORDER BY d DESC LIMIT 7")
        res["recent_applications"] = [dict(r) for r in cursor.fetchall()][::-1]

        try:
            closed_loop_stats = build_closed_loop_stats()
            res["summary"].update(closed_loop_stats)
        except Exception:
            pass

    except Exception as e:
        logging.error(f"Stats Error: {e}")
    finally:
        conn.close()

    return res

@router.get("/users")
def get_admin_users():
    # 用户治理页直接读取用户基础信息和状态，供管理员执行制裁动作。
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, status FROM users ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@router.get("/applications")
def get_admin_applications():
    # 后台审核列表会额外补充申请时间线，便于集中查看审核过程。
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.username as user_name, p.name as pet_name, o.username as owner_name 
        FROM applications a 
        LEFT JOIN users u ON a.user_id = u.id 
        LEFT JOIN users o ON a.pet_owner_id = o.id 
        LEFT JOIN pets p ON a.pet_id = p.id 
        ORDER BY a.create_time DESC
    """)
    rows = []
    for row in cursor.fetchall():
        item = dict(row)
        item["flow_timeline"] = flow_engine.get_timeline(conn, item["id"], limit=6)
        rows.append(item)
    conn.close()
    return rows

@router.get("/moderation/logs")
def get_moderation_logs():
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM moderation_logs ORDER BY delete_time DESC")
        return [dict(r) for r in cursor.fetchall()]
    except: return []
    finally: conn.close()

@router.get("/ai/traces")
def get_ai_traces():
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, trace_id, endpoint, agent_name, tool_name, latency_ms, fallback_used,
                   input_msg, output_msg, create_time
            FROM agent_trace_logs
            ORDER BY create_time DESC, id DESC
            LIMIT 100
        """)
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            item["message"] = item.get("output_msg") or item.get("input_msg") or ""
            rows.append(item)
        return rows
    except Exception:
        return []
    finally:
        conn.close()

@router.post("/posts/{post_id}/takedown")
async def takedown_post(post_id: int, req: TakedownRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, title FROM posts WHERE id=?", (post_id,))
        post = cursor.fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        user_id = post["user_id"]
        post_title = post["title"] or "未命名帖子"
        # 1. 记录审计日志
        # 所有治理操作都应留痕，便于后续追踪管理员处置依据。
        cursor.execute(
            "INSERT INTO moderation_logs (target_id, admin_id, reason, evidence_url) VALUES (?, ?, ?, ?)",
            (post_id, req.admin_id or 0, req.reason, req.evidence_url)
        )
        # 2. 发送通知给用户
        _send_notification(conn, user_id, "moderation", "内容下架通知", 
                          f"您的帖子《{post_title}》已被下架。原因：{req.reason}")
        # 3. 执行删除 (或软删除，此处执行物理删除)
        cursor.execute("DELETE FROM pets WHERE source_post_id = ?", (post_id,))
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        
        conn.commit()
    return {"status": "success", "message": "帖子已成功下架并通知用户"}

@router.get("/mutual-aid/stats")
def get_mutual_aid_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mutual_aid_tasks")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM mutual_aid_tasks WHERE strftime('%Y-%m-%d', create_time) = ?", (datetime.now().strftime("%Y-%m-%d"),))
        today_new = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM mutual_aid_tasks WHERE status='accepted'")
        accepted = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM mutual_aid_reports WHERE status='pending'")
        pending_reports = cursor.fetchone()[0]
        
        accept_rate = round((accepted / total * 100), 1) if total > 0 else 0
        return {"total": total, "today_new": today_new, "accept_rate": accept_rate, "pending_reports": pending_reports}

@router.get("/mutual-aid/tasks")
def get_admin_mutual_aid_tasks():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, u.username as publisher_name 
            FROM mutual_aid_tasks t 
            JOIN users u ON t.user_id = u.id 
            ORDER BY t.create_time DESC
        """)
        return [dict(r) for r in cursor.fetchall()]

@router.get("/mutual-aid/reports")
def get_admin_mutual_aid_reports():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, u.username as reporter_name, t.pet_name, publisher.username as task_owner_name
            FROM mutual_aid_reports r
            JOIN users u ON r.reporter_id = u.id
            JOIN mutual_aid_tasks t ON r.task_id = t.id
            JOIN users publisher ON t.user_id = publisher.id
            ORDER BY r.create_time DESC
        """)
        return [dict(r) for r in cursor.fetchall()]

@router.post("/mutual-aid/tasks/{task_id}/takedown")
async def takedown_mutual_aid_task(task_id: int, req: TakedownRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, task_type, pet_name FROM mutual_aid_tasks WHERE id=?", (task_id,))
        task = cursor.fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="互助任务不存在")
        
        user_id = task["user_id"]
        task_info = f"{task['task_type']} - {task['pet_name']}"
        
        # 1. 记录审计日志
        cursor.execute(
            "INSERT INTO moderation_logs (target_id, admin_id, reason, evidence_url) VALUES (?, ?, ?, ?)",
            (task_id, req.admin_id or 0, f"[互助任务下架] {req.reason}", req.evidence_url)
        )
        
        # 2. 发送通知
        _send_notification(conn, user_id, "moderation", "互助任务下架通知", 
                          f"您的互助任务《{task_info}》已被下架。原因：{req.reason}")
        
        # 3. 更新状态或删除 (此处执行物理删除)
        # 同步把关联举报标记为已处理，形成完整治理闭环。
        cursor.execute("DELETE FROM mutual_aid_tasks WHERE id = ?", (task_id,))
        cursor.execute("UPDATE mutual_aid_reports SET status='resolved_cancel', resolve_note=? WHERE task_id=?", (req.reason, task_id))
        
        conn.commit()
    return {"status": "success", "message": "互助任务已成功下架"}

@router.post("/mutual-aid/reports/{report_id}/resolve")
async def resolve_report(report_id: int, req: dict):
    # 此处简化实现，仅更新状态
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE mutual_aid_reports SET status=?, resolve_note=?, resolve_time=CURRENT_TIMESTAMP WHERE id=?", 
                      (f"resolved_{req['action']}", req['note'], report_id))
        conn.commit()
    return {"status": "success"}

@router.post("/users/sanction")
def sanction_user(req: UserSanctionRequest):
    # 制裁动作会同时更新用户状态、写入制裁记录并发送站内通知。
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status=? WHERE id=?", (req.type, req.user_id))
        cursor.execute(
        "INSERT INTO user_sanctions (user_id, admin_id, type, reason, evidence_url) VALUES (?, ?, ?, ?, ?)",
            (req.user_id, req.admin_id, req.type.upper(), req.reason, req.evidence)
        )
        _send_notification(conn, req.user_id, "moderation", "账号状态变更通知", 
                f"由于违规行为（{req.reason}），您的账号已被{ '禁言' if req.type=='muted' else '封禁'}。")
        conn.commit()
    return {"status": "success"}
@router.post("/users/reactivate")
def reactivate_user(user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
        _send_notification(conn, user_id, "moderation", "账号功能恢复通知", "您的账号已恢复正常使用。")
        conn.commit()
    return {"status": "success"}
