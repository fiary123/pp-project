import json
import logging
from fastapi import APIRouter, Depends
from src.web.schemas import UserSanctionRequest, ApplicationUpdateRequest
from src.web.services.db_service import get_db_connection, ensure_tables
from src.web.services.adoption_flow_engine import flow_engine
from src.web.services.adoption_memory import build_closed_loop_stats
from src.web.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

def _parse_json(raw_value, fallback):
    if raw_value in (None, "", b""): return fallback
    try:
        return json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except: return fallback

@router.get("/overview/stats")
def get_overview_stats():
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
        # 使用更稳健的 strftime
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
    conn = get_db_connection()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role, status FROM users ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@router.get("/applications")
def get_admin_applications():
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

@router.get("/mutual-aid/stats")
def get_mutual_aid_stats():
    # 简化逻辑，确保不崩溃
    return {"today_new": 0, "accept_rate": 0, "complete_rate": 0, "pending_reports": 0}

@router.get("/mutual-aid/tasks")
def get_mutual_aid_tasks(): return []

@router.get("/mutual-aid/reports")
def get_mutual_aid_reports(): return []
