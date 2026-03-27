from fastapi import APIRouter, HTTPException, Depends, Body
import json
from src.web.schemas import (
    ChangePasswordRequest, MessageCreate,
    AdoptionApplicationCreateRequest, OwnerApplicationDecisionRequest
)
from src.web.services.db_service import get_db, ensure_tables
from src.web.services.auth_service import verify_password, get_password_hash
from src.web.dependencies import get_current_user
from src.web.services.credit_service import CreditService
from src.web.services.ai_service import ai_service

router = APIRouter(prefix="/api/user", tags=["user"])
credit_service = CreditService(ai_service)


def _load_pet_preferences(raw_value):
    default_pref = {
        "hard_preferences": [],
        "soft_preferences": ["住房稳定性", "陪伴时间", "责任意识"],
        "allow_novice": True,
        "accept_renting": True,
        "prefer_local": False,
        "require_family_agreement": False,
        "focus_experience": False,
        "focus_companionship": True,
        "focus_stability": True,
    }
    if not raw_value:
        return default_pref
    try:
        loaded = json.loads(raw_value)
        if isinstance(loaded, dict):
            default_pref.update(loaded)
    except Exception:
        pass
    return default_pref


def _build_owner_ai_report(app_row: dict, pref: dict) -> dict:
    score = int(app_row.get("ai_readiness_score") or 0)
    ai_decision = (app_row.get("ai_decision") or "").lower()
    strengths = []
    risks = []
    confirm_questions = []

    if score >= 75:
        strengths.append("申请人基础准备度较高，适合继续推进沟通")
    elif score >= 60:
        strengths.append("申请人整体条件尚可，具备进一步沟通价值")
    else:
        risks.append("AI 准备度评分偏低，建议谨慎核验关键条件")

    if pref.get("focus_stability"):
        confirm_questions.append("请进一步确认申请人的居住稳定性与未来 1 年安置计划")
    if pref.get("focus_companionship"):
        confirm_questions.append("建议确认日常陪伴时长是否能长期兑现")
    if pref.get("focus_experience"):
        confirm_questions.append("建议确认其过往养宠经验与突发情况处理能力")
    if pref.get("require_family_agreement"):
        confirm_questions.append("建议确认家庭成员是否全部知情并同意领养")
    if not pref.get("accept_renting", True):
        risks.append("发布者对租房申请较谨慎，需补充稳定居住证明")
    if not pref.get("allow_novice", True):
        risks.append("发布者不倾向新手申请，需重点核验照护经验")
    if pref.get("prefer_local"):
        strengths.append("若申请人为本地领养，可降低交接与回访成本")
        confirm_questions.append("建议确认申请人是否便于线下沟通、回访或探视")

    suggested_action = "继续沟通"
    if score < 50 or ai_decision == "reject":
        suggested_action = "谨慎拒绝或要求补充材料"
    elif score < 70 or ai_decision in ("review_required", "conditional_pass"):
        suggested_action = "补充关键信息后再决定"

    if not strengths:
        strengths.append("已形成基础申请材料，可结合实际沟通继续判断")
    if not risks:
        risks.append("暂未发现明显硬性风险，但仍建议核验关键细节")
    if not confirm_questions:
        confirm_questions.append("建议确认其长期责任感与应急处理意识")

    return {
        "applicant_summary": f"AI 评分 {score}/100，系统倾向：{app_row.get('ai_decision') or '待评估'}",
        "compatibility_score": score,
        "strengths": strengths[:3],
        "risks": risks[:3],
        "confirm_questions": confirm_questions[:4],
        "suggested_action": suggested_action,
    }


def _owner_followed_ai(final_status: str, ai_decision: str) -> int | None:
    ai = (ai_decision or "").lower()
    if not ai:
        return None
    ai_positive = ai in ("pass", "conditional_pass", "approved", "通过", "建议通过")
    final_positive = final_status == "approved"
    return 1 if ai_positive == final_positive else 0


def _detect_flow_status(ai_decision: str, missing_fields: list | None, followup_questions: list | None) -> str:
    if followup_questions or missing_fields:
        return "need_more_info"
    if (ai_decision or "").lower() in ("review_required", "reject"):
        return "manual_review"
    return "waiting_publisher"

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
            select_sql = f"""
            SELECT a.*,
                   p.name AS pet_name,
                   p.species AS pet_species,
                   u.username AS owner_name
                FROM applications a
                LEFT JOIN pets p ON a.pet_id = p.id
                LEFT JOIN users u ON a.pet_owner_id = u.id
                WHERE a.user_id=?
                ORDER BY a.{order_col} DESC
            """
            cursor.execute(select_sql, (user_id,))
        else:
            cursor.execute("SELECT * FROM applications ORDER BY id DESC")
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            for key in ("missing_fields", "conflict_notes", "followup_questions"):
                raw = item.get(key)
                if raw:
                    try:
                        item[key] = json.loads(raw)
                    except Exception:
                        item[key] = []
                else:
                    item[key] = []
            rows.append(item)
    return rows


@router.post("/applications/submit")
async def submit_adoption_application(
    req: AdoptionApplicationCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT id, owner_id, status FROM pets WHERE id=?", (req.pet_id,))
        pet = cursor.fetchone()
        if not pet:
            raise HTTPException(status_code=404, detail="宠物不存在")
        if pet["owner_id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="不能申请自己发布的宠物")
        if pet["status"] not in ("待领养", "pending", "available", None):
            raise HTTPException(status_code=400, detail="该宠物当前不可申请")

        cursor.execute(
            """SELECT id FROM applications
               WHERE user_id=? AND pet_id=? AND status IN ('pending', 'pending_owner_review')""",
            (current_user["id"], req.pet_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="您已提交过该宠物的待处理申请")

        cursor.execute(
            """INSERT INTO applications
               (user_id, pet_id, pet_owner_id, apply_reason, ai_decision, ai_readiness_score, ai_summary,
                flow_status, risk_level, consensus_score, missing_fields, conflict_notes, followup_questions, memory_scope, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_owner_review')""",
            (
                current_user["id"], req.pet_id, pet["owner_id"], req.apply_reason,
                req.ai_decision, req.ai_readiness_score, req.ai_summary or "",
                _detect_flow_status(req.ai_decision or "", req.missing_fields, req.followup_questions),
                req.risk_level or "Medium",
                req.consensus_score if req.consensus_score is not None else req.ai_readiness_score,
                json.dumps(req.missing_fields or [], ensure_ascii=False),
                json.dumps(req.conflict_notes or [], ensure_ascii=False),
                json.dumps(req.followup_questions or [], ensure_ascii=False),
                req.memory_scope or f"/adoption/pet_{req.pet_id}/applicant_{current_user['id']}"
            )
        )
        app_id = cursor.lastrowid
        conn.commit()
    return {"status": "success", "application_id": app_id}


@router.get("/applications/incoming")
def get_incoming_applications(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.*,
                   p.name AS pet_name,
                   p.species AS pet_species,
                   p.adoption_preferences AS pet_preferences,
                   u.username AS applicant_name,
                   u.email AS applicant_email
            FROM applications a
            LEFT JOIN pets p ON a.pet_id = p.id
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.pet_owner_id = ?
            ORDER BY a.create_time DESC
            """,
            (current_user["id"],)
        )
        rows = []
        for row in cursor.fetchall():
            item = dict(row)
            prefs = _load_pet_preferences(item.get("pet_preferences"))
            for key in ("missing_fields", "conflict_notes", "followup_questions"):
                raw = item.get(key)
                if raw:
                    try:
                        item[key] = json.loads(raw)
                    except Exception:
                        item[key] = []
                else:
                    item[key] = []
            item["pet_preferences"] = prefs
            item["owner_ai_report"] = _build_owner_ai_report(item, prefs)
            rows.append(item)
    return rows


@router.post("/applications/{app_id}/owner-decision")
async def owner_decide_application(
    app_id: int,
    req: OwnerApplicationDecisionRequest,
    current_user: dict = Depends(get_current_user)
):
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id=?", (app_id,))
        app = cursor.fetchone()
        if not app:
            raise HTTPException(status_code=404, detail="申请记录不存在")
        if app["pet_owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="只有送养方可以处理该申请")
        
        # 允许从 pending, probing, human_review 状态流向最终决策
        if app["status"] in ("approved", "rejected"):
            raise HTTPException(status_code=400, detail="该申请已是最终状态，无法修改")

        # 计算送养人是否采纳了 AI 建议
        # 采纳定义：AI 建议通过且送养人通过，或 AI 建议驳回且送养人驳回
        owner_followed_ai = 0
        ai_suggestion = app.get("ai_decision", "").lower()
        if req.status == "approved" and ai_suggestion in ("pass", "conditional_pass"):
            owner_followed_ai = 1
        elif req.status == "rejected" and ai_suggestion == "reject":
            owner_followed_ai = 1
        flow_status = {
            "approved": "approved",
            "rejected": "rejected",
            "probing": "need_more_info",
            "human_review": "manual_review",
        }.get(req.status, "waiting_publisher")

        cursor.execute(
            """UPDATE applications
               SET status=?, flow_status=?, owner_note=?, publisher_feedback=?, manual_review_reason=?,
                   owner_followed_ai=?, decision_by=?, decision_time=CURRENT_TIMESTAMP
               WHERE id=?""",
            (
                req.status,
                flow_status,
                req.owner_note,
                req.owner_note if req.status in ("approved", "rejected", "probing", "human_review") else "",
                req.owner_note if req.status == "human_review" else "",
                owner_followed_ai,
                current_user["id"],
                app_id,
            )
        )

        # 特殊逻辑处理
        if req.status == "approved":
            # 记录领养成功
            cursor.execute(
                "INSERT INTO adopt_records (user_id, pet_id) VALUES (?, ?)",
                (app["user_id"], app["pet_id"])
            )
            # 更新宠物状态
            cursor.execute("UPDATE pets SET status='已领养' WHERE id=?", (app["pet_id"],))
        
        elif req.status == "probing":
            # 如果是追问，可以触发某种系统通知或消息，这里暂时只更新状态
            pass
            
        elif req.status == "human_review":
            # 标记需要平台管理员介入
            pass

        conn.commit()
    return {"status": "success", "new_status": req.status}

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
