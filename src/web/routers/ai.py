from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, BackgroundTasks
from typing import Optional, Any
import json
import logging
from src.web.schemas import (
    ChatRequest, NutritionPlanRequest, SmartMatchRequest,
    NutritionFeedbackRequest, NutritionReplanRequest, AdoptionAssessmentRequest,
    MatchFollowupRequest, AdoptionFeedbackRequest, PetChatRequest,
    MutualAidTaskCreate, MutualAidMatchRequest, MutualAidAcceptRequest,
    MutualAidReportRequest, AdoptionEvaluationFollowupRequest,
    AdoptionEvaluationReviewRequest, AdoptionEvaluationFeedbackRequest
)
from src.agents.agents import analyze_pet_interview, run_pet_chat
from src.agents.tools import search_pet_knowledge_hits
from src.web.services.ai_service import (
    get_agent_reply, generate_nutrition_plan,
    get_smart_match, get_match_followup_questions, submit_adoption_feedback,
    submit_nutrition_feedback, replan_nutrition,
    run_adoption_assessment_service, get_mutual_aid_match,
    get_db, ai_service
)
from src.web.services.assessment_service import AdoptionAssessmentService
from src.web.services.adoption_flow_engine import flow_engine
from src.web.services.adoption_memory import (
    build_case_summary,
    persist_ai_review,
    persist_followup_records,
    sync_publisher_preferences,
    update_signal_weights_from_feedback,
    upsert_case_memory,
)
from src.web.dependencies import get_current_user
from src.web.limiter import limiter
from src.agents.coordinator import CoordinatorAgent
from langchain_openai import ChatOpenAI
import os

router = APIRouter(prefix="/api", tags=["ai"])
logger = logging.getLogger(__name__)

# 初始化子智能体
# 使用 DEEPSEEK_API_KEY 和 DEEPSEEK_BASE_URL 明确标识供应商，避免与 OpenAI 混淆。
# 用户输入将被发送至 DeepSeek 模型服务，请确保符合相关隐私与合规要求。
class LLMWrapper:
    """为了兼容 CoordinatorAgent 的 llm.ask 接口"""
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("环境变量 DEEPSEEK_API_KEY 未设置，AI 功能无法启动。")
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=api_key,
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3
        )
    async def ask(self, prompt: str) -> str:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="你是宠物领养平台的中央调度AI，负责意图分类与会话路由。请严格按照指令格式输出，不要添加多余文字。"),
            HumanMessage(content=prompt),
        ]
        res = await self.llm.ainvoke(messages)
        return res.content

coordinator = CoordinatorAgent(LLMWrapper(), get_db)
assessment_service = AdoptionAssessmentService()


def _parse_json_payload(raw_value: Any, fallback: Any):
    if raw_value in (None, "", b""):
        return fallback
    if isinstance(raw_value, (dict, list)):
        return raw_value
    try:
        loaded = json.loads(raw_value)
        return loaded if isinstance(loaded, type(fallback)) else fallback
    except Exception:
        return fallback


def _normalize_target_species(raw_value: str) -> str:
    text = (raw_value or "").lower()
    if any(token in text for token in ("dog", "犬", "狗")):
        return "dog"
    return "cat"


def _load_application_row(application_id: int):
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.*, p.name AS pet_name, p.species AS pet_species, p.adoption_preferences AS pet_preferences
            FROM applications a
            LEFT JOIN pets p ON p.id = a.pet_id
            WHERE a.id=?
            """,
            (application_id,),
        )
        row = cursor.fetchone()
    return dict(row) if row else None


def _ensure_application_access(app_row: dict, current_user: dict):
    if not app_row:
        raise HTTPException(status_code=404, detail="申请记录不存在")
    if current_user.get("role") == "org_admin":
        return
    if current_user["id"] not in {app_row.get("user_id"), app_row.get("pet_owner_id")}:
        raise HTTPException(status_code=403, detail="无权访问该申请")


def _build_assessment_payload(app_row: dict) -> dict:
    payload = _parse_json_payload(app_row.get("assessment_payload"), {})
    publisher_preferences = _parse_json_payload(app_row.get("pet_preferences"), {})
    payload["target_pet_name"] = payload.get("target_pet_name") or app_row.get("pet_name") or "未命名宠物"
    payload["target_species"] = _normalize_target_species(
        payload.get("target_species") or app_row.get("pet_species") or ""
    )
    payload["application_reason"] = payload.get("application_reason") or app_row.get("apply_reason") or ""
    payload["applicant_info"] = payload.get("applicant_info") or app_row.get("apply_reason") or "申请人提交了领养申请"
    payload["publisher_preferences"] = publisher_preferences
    return payload


async def _run_adoption_evaluation(application_id: int):
    app_row = _load_application_row(application_id)
    if not app_row:
        return

    payload = _build_assessment_payload(app_row)

    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        previous_flow_status = app_row.get("flow_status") or "submitted"
        conn.execute(
            """
            UPDATE applications
            SET flow_status='evaluating',
                evaluation_started_at=CURRENT_TIMESTAMP,
                evaluation_finished_at=NULL,
                evaluation_error=NULL,
                publisher_feedback='',
                manual_review_reason=''
            WHERE id=?
            """,
            (application_id,),
        )
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="assessment_started",
            from_status=previous_flow_status,
            to_status="evaluating",
            actor_role="system",
            actor_id=app_row.get("user_id"),
            payload={"trigger": "background_evaluation"},
        )
        conn.commit()

    try:
        result = await assessment_service.run_full_assessment(
            user_id=app_row["user_id"],
            applicant_data=payload,
        )
        sync_publisher_preferences(app_row.get("pet_owner_id"), app_row.get("pet_id"), payload.get("publisher_preferences"))

        confidence_level = result.get("confidence_level")
        consensus_score = None
        if confidence_level is not None:
            consensus_score = confidence_level * 100 if confidence_level <= 1 else confidence_level

        with get_db() as conn:
            from src.web.services.db_service import ensure_tables
            ensure_tables(conn)
            persisted_payload = dict(payload)
            persisted_payload["latest_assessment"] = result
            next_flow_status = flow_engine.resolve_result_flow_status(result)
            conn.execute(
                """
                UPDATE applications
                SET ai_decision=?,
                    ai_readiness_score=?,
                    ai_summary=?,
                    assessment_payload=?,
                    flow_status=?,
                    risk_level=?,
                    consensus_score=?,
                    missing_fields=?,
                    conflict_notes=?,
                    followup_questions=?,
                    evaluation_trace_id=?,
                    evaluation_finished_at=CURRENT_TIMESTAMP,
                    evaluation_error=NULL
                WHERE id=?
                """,
                (
                    result.get("decision"),
                    result.get("readiness_score"),
                    result.get("final_summary") or result.get("review_note") or "",
                    json.dumps(persisted_payload, ensure_ascii=False),
                    next_flow_status,
                    result.get("risk_level") or "Medium",
                    consensus_score,
                    json.dumps(result.get("missing_fields") or [], ensure_ascii=False),
                    json.dumps(result.get("conflict_notes") or [], ensure_ascii=False),
                    json.dumps(result.get("followup_questions") or [], ensure_ascii=False),
                    result.get("trace_id") or "",
                    application_id,
                ),
            )
            flow_engine.append_event(
                conn,
                application_id=application_id,
                event_type="assessment_completed",
                from_status="evaluating",
                to_status=next_flow_status,
                actor_role="system",
                actor_id=app_row.get("user_id"),
                payload={
                    "decision": result.get("decision"),
                    "route_decision": result.get("route_decision"),
                    "consensus_result": result.get("consensus_result"),
                },
            )
            persist_ai_review(application_id, result)
            conn.commit()
    except Exception as exc:
        logger.exception("adoption evaluation background task failed")
        with get_db() as conn:
            from src.web.services.db_service import ensure_tables
            ensure_tables(conn)
            conn.execute(
                """
                UPDATE applications
                SET flow_status='manual_review',
                    evaluation_finished_at=CURRENT_TIMESTAMP,
                    evaluation_error=?,
                    publisher_feedback='评估服务执行异常，请由送养方或管理员人工确认'
                WHERE id=?
                """,
                (str(exc), application_id),
            )
            flow_engine.append_event(
                conn,
                application_id=application_id,
                event_type="assessment_failed",
                from_status="evaluating",
                to_status="manual_review",
                actor_role="system",
                actor_id=app_row.get("user_id"),
                payload={"error": str(exc)[:240]},
            )
            conn.commit()


@router.get("/knowledge/stats")
async def knowledge_stats():
    """查询知识库状态：条目数量、分类统计"""
    try:
        import chromadb
        from src.database.db_config import CHROMA_DB_PATH
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(name="pet_knowledge")
        total = collection.count()
        # 按分类统计
        if total > 0:
            all_items = collection.get(include=["metadatas"])
            categories: dict = {}
            for meta in all_items["metadatas"]:
                cat = meta.get("category", "other")
                categories[cat] = categories.get(cat, 0) + 1
        else:
            categories = {}
        return {
            "total": total,
            "categories": categories,
            "category_labels": {
                "breed_wiki": "品种百科",
                "health_care": "健康护理",
                "feeding_guide": "喂养指南",
                "adoption_knowledge": "领养知识"
            }
        }
    except Exception as e:
        return {"total": 0, "categories": {}, "error": str(e)}


@router.post("/knowledge/search")
async def knowledge_search(req: dict):
    """知识库语义检索接口（演示用）"""
    keyword = req.get("keyword", "")
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    async def build_llm_fallback(message: str):
        try:
            fallback_answer = await ai_service.ask(
                f"用户提问：{keyword}\n"
                f"当前知识库检索情况：{message}\n"
                "请给出简洁、友好的宠物知识补充回答。要求："
                "1）开头明确说明这是 AI 通用知识补充，不是知识库命中结果；"
                "2）不要编造来源；"
                "3）若涉及疾病、持续异常或用药风险，提醒咨询兽医。"
            )
        except Exception:
            fallback_answer = "当前知识库没有检索到合适内容，我先基于通用宠物知识为你补充回答；若涉及疾病、用药或持续异常，建议尽快咨询专业兽医。"
        return {
            "results": [],
            "keyword": keyword,
            "source": "llm_fallback",
            "message": message,
            "fallback_answer": fallback_answer,
        }

    try:
        hits = search_pet_knowledge_hits(keyword, limit=5)
        if not hits:
            return await build_llm_fallback("知识库中没有直接匹配当前问题的内容，以下为 AI 通用知识补充。")
        items = []
        for hit in hits:
            meta = hit.get("meta") or {}
            items.append({
                "text": str(hit.get("text", ""))[:300],
                "category": meta.get("category"),
                "similarity": hit.get("similarity", 0),
                "meta": meta
            })
        if not items:
            return await build_llm_fallback("知识库中暂无高度相关内容，以下为 AI 通用知识补充。")
        return {"results": items, "keyword": keyword, "source": "knowledge_base"}
    except Exception as e:
        logger.warning(f"knowledge_search failed, falling back to llm: {e}")
        return await build_llm_fallback("知识库检索暂时不可用，以下为 AI 通用知识补充。")


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest, current_user: dict = Depends(get_current_user)):
    # 使用协调智能体处理输入
    session_id = f"session_{current_user['id']}"
    result = await coordinator.handle_user_input(
        session_id=session_id,
        user_id=current_user["id"],
        user_message=req.message,
        followup_answers=req.followup_answers,
        target_pet_name=req.target_pet_name,
        target_species=req.target_species,
    )
    return {
        "reply": result["reply"],
        "ui_actions": result["ui_actions"],
        "stage": result["stage"],
        "trace_id": "coord_" + session_id
    }


@router.post("/nutrition/plan")
@limiter.limit("10/minute")
async def create_nutrition_plan(request: Request, req: NutritionPlanRequest):
    plan, markdown, trace_id, plan_id = generate_nutrition_plan(req.model_dump())
    return {
        "status": "success",
        "plan": plan,
        "explanation_markdown": markdown,
        "trace_id": trace_id,
        "plan_id": plan_id
    }

@router.post("/nutrition/feedback")
async def nutrition_feedback(req: NutritionFeedbackRequest):
    """提交营养方案执行反馈"""
    feedback_id = submit_nutrition_feedback(req.model_dump())
    return {"status": "success", "feedback_id": feedback_id}

@router.post("/nutrition/replan")
async def nutrition_replan(req: NutritionReplanRequest):
    """基于反馈进行方案再规划"""
    try:
        new_plan, markdown, trace_id = replan_nutrition(req.plan_id, req.feedback_id)
        return {
            "status": "success",
            "plan": new_plan,
            "explanation_markdown": markdown,
            "trace_id": trace_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/pets/match-followup")
async def match_followup(req: MatchFollowupRequest):
    """
    创新点1：基于用户初始描述，生成 2-3 个追问问题（需求显化）。
    """
    questions = get_match_followup_questions(req.user_query)
    return {"questions": questions}


@router.post("/pets/smart-match")
async def smart_match(req: SmartMatchRequest):
    """
    创新点1+3：LLM 语义匹配 + 结构化可解释推荐。
    """
    matches = get_smart_match(req.user_query, req.pet_list, req.followup_answers)
    return {"matches": matches}


@router.post("/adoption/feedback")
async def adoption_feedback(
    req: AdoptionFeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    创新点3：领养后回访反馈接口。
    """
    feedback_id = submit_adoption_feedback(
        user_id=req.user_id,
        pet_id=req.pet_id,
        pet_name=req.pet_name,
        overall_satisfaction=req.overall_satisfaction,
        bond_level=req.bond_level,
        unexpected_challenges=req.unexpected_challenges,
        would_recommend=req.would_recommend,
        free_feedback=req.free_feedback
    )
    return {"status": "success", "feedback_id": feedback_id}


@router.post("/adoption/assess")
@limiter.limit("5/minute")
async def adoption_assess(
    request: Request,
    req: AdoptionAssessmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    领养资质多智能体评估接口（创新架构版）
    结合规则引擎与 LLM 语义推理，输出可解释的结构化报告。
    """
    result = await assessment_service.run_full_assessment(
        user_id=current_user["id"],
        applicant_data=req.model_dump()
    )
    return result


@router.post("/adoption/evaluate/{application_id}")
async def start_adoption_evaluation(
    application_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    app_row = _load_application_row(application_id)
    _ensure_application_access(app_row, current_user)

    if not _parse_json_payload(app_row.get("assessment_payload"), {}):
        raise HTTPException(status_code=400, detail="该申请缺少评估输入，无法启动生命周期评估")
    if app_row.get("status") in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="该申请已是最终状态，无需再次评估")

    background_tasks.add_task(_run_adoption_evaluation, application_id)
    return {
        "status": "accepted",
        "application_id": application_id,
        "flow_status": "evaluating",
        "message": "评估任务已启动，请稍后刷新状态。"
    }


@router.get("/adoption/evaluate/{application_id}/status")
async def get_adoption_evaluation_status(
    application_id: int,
    current_user: dict = Depends(get_current_user),
):
    app_row = _load_application_row(application_id)
    _ensure_application_access(app_row, current_user)

    response = dict(app_row)
    for field in ("missing_fields", "conflict_notes", "followup_questions"):
        response[field] = _parse_json_payload(response.get(field), [])
    response["assessment_payload"] = _parse_json_payload(response.get("assessment_payload"), {})
    response["pet_preferences"] = _parse_json_payload(response.get("pet_preferences"), {})
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        response["flow_timeline"] = flow_engine.get_timeline(conn, application_id, limit=8)
    return response


@router.post("/adoption/evaluate/{application_id}/followup")
async def submit_adoption_evaluation_followup(
    application_id: int,
    req: AdoptionEvaluationFollowupRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    app_row = _load_application_row(application_id)
    _ensure_application_access(app_row, current_user)

    if current_user.get("role") != "org_admin" and current_user["id"] != app_row.get("user_id"):
        raise HTTPException(status_code=403, detail="只有申请人可以补充评估信息")

    payload = _build_assessment_payload(app_row)
    existing_questions = _parse_json_payload(app_row.get("followup_questions"), [])
    if req.applicant_info is not None:
        payload["applicant_info"] = req.applicant_info
    if req.application_reason is not None:
        payload["application_reason"] = req.application_reason
    if req.monthly_budget is not None:
        payload["monthly_budget"] = req.monthly_budget
    if req.daily_companion_hours is not None:
        payload["daily_companion_hours"] = req.daily_companion_hours
    if req.has_pet_experience is not None:
        payload["has_pet_experience"] = req.has_pet_experience
    if req.housing_type is not None:
        payload["housing_type"] = req.housing_type
    if req.existing_pets is not None:
        payload["existing_pets"] = req.existing_pets
    if req.supplement_text:
        supplement = req.supplement_text.strip()
        applicant_info = payload.get("applicant_info", "").strip()
        payload["applicant_info"] = f"{applicant_info}\n补充说明：{supplement}".strip()
        app_reason = payload.get("application_reason", "").strip()
        payload["application_reason"] = f"{app_reason}\n补充说明：{supplement}".strip()

    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        previous_flow_status = app_row.get("flow_status") or "need_more_info"
        conn.execute(
            """
            UPDATE applications
            SET apply_reason=?,
                assessment_payload=?,
                flow_status='evaluating',
                followup_questions='[]',
                conflict_notes='[]',
                missing_fields='[]',
                evaluation_error=NULL,
                publisher_feedback=''
            WHERE id=?
            """,
            (
                payload.get("application_reason") or payload.get("applicant_info") or app_row.get("apply_reason") or "",
                json.dumps(payload, ensure_ascii=False),
                application_id,
            ),
        )
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="followup_submitted",
            from_status=previous_flow_status,
            to_status="evaluating",
            actor_role="applicant" if current_user.get("role") != "org_admin" else "admin",
            actor_id=current_user["id"],
            payload={
                "supplement_text": (req.supplement_text or "")[:240],
                "updated_fields": [key for key, value in req.model_dump().items() if value not in (None, "", [])],
            },
        )
        conn.commit()

    persist_followup_records(
        application_id,
        existing_questions,
        req.supplement_text or payload.get("application_reason") or payload.get("applicant_info") or "",
    )
    background_tasks.add_task(_run_adoption_evaluation, application_id)
    return {
        "status": "accepted",
        "application_id": application_id,
        "flow_status": "evaluating",
        "message": "补充信息已收到，系统正在重新评估。"
    }


@router.post("/adoption/evaluate/{application_id}/review")
async def review_adoption_evaluation(
    application_id: int,
    req: AdoptionEvaluationReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    app_row = _load_application_row(application_id)
    _ensure_application_access(app_row, current_user)

    is_admin = current_user.get("role") == "org_admin"
    is_owner = current_user["id"] == app_row.get("pet_owner_id")
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="只有送养方或管理员可以处理该申请")
    if app_row.get("status") in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="该申请已是最终状态")

    previous_flow_status = app_row.get("flow_status") or "waiting_publisher"
    flow_status = flow_engine.resolve_terminal_flow_status(req.status)
    owner_followed_ai = None
    ai_decision = (app_row.get("ai_decision") or "").lower()
    if req.status in ("approved", "rejected") and ai_decision:
        ai_positive = ai_decision in ("pass", "conditional_pass", "approved", "通过", "建议通过")
        owner_followed_ai = 1 if ai_positive == (req.status == "approved") else 0

    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE applications
            SET status=?,
                flow_status=?,
                owner_note=?,
                publisher_feedback=?,
                manual_review_reason=?,
                owner_followed_ai=?,
                decision_by=?,
                decision_time=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                req.status,
                flow_status,
                req.note,
                req.note if req.status in ("approved", "rejected", "probing", "human_review") else "",
                req.note if req.status == "human_review" else "",
                owner_followed_ai,
                current_user["id"],
                application_id,
            ),
        )
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="review_completed",
            from_status=previous_flow_status,
            to_status=flow_status,
            actor_role="admin" if is_admin else "publisher",
            actor_id=current_user["id"],
            payload={
                "requested_status": req.status,
                "note": req.note[:240],
                "owner_followed_ai": owner_followed_ai,
            },
        )

        if req.status == "approved":
            cursor.execute(
                "SELECT COUNT(1) AS cnt FROM adopt_records WHERE user_id=? AND pet_id=?",
                (app_row["user_id"], app_row["pet_id"]),
            )
            record_exists = cursor.fetchone()["cnt"]
            if not record_exists:
                cursor.execute(
                    "INSERT INTO adopt_records (user_id, pet_id) VALUES (?, ?)",
                    (app_row["user_id"], app_row["pet_id"]),
                )
            cursor.execute("UPDATE pets SET status='已领养' WHERE id=?", (app_row["pet_id"],))

        conn.commit()

    upsert_case_memory(
        application_id=application_id,
        case_summary=build_case_summary(app_row, {"decision": req.status, "readiness_score": app_row.get("ai_readiness_score"), "risk_level": app_row.get("risk_level")}),
        decision_result=req.status,
        owner_followed_ai=owner_followed_ai,
        risk_tags=(_parse_json_payload(_parse_json_payload(app_row.get("assessment_payload"), {}).get("latest_assessment", {}).get("consensus_result"), {}) or {}).get("risk_tags", []),
    )

    return {"status": "success", "application_id": application_id, "new_status": req.status}


@router.post("/adoption/evaluate/{application_id}/feedback")
async def write_adoption_evaluation_feedback(
    application_id: int,
    req: AdoptionEvaluationFeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    app_row = _load_application_row(application_id)
    _ensure_application_access(app_row, current_user)

    if app_row.get("status") != "approved":
        raise HTTPException(status_code=400, detail="只有已通过的领养申请才能提交回访反馈")
    if current_user.get("role") != "org_admin" and current_user["id"] != app_row.get("user_id"):
        raise HTTPException(status_code=403, detail="只有申请人可以提交回访反馈")
    if app_row.get("feedback_written"):
        raise HTTPException(status_code=400, detail="该申请已提交过回访反馈")

    feedback_id = submit_adoption_feedback(
        user_id=app_row["user_id"],
        pet_id=app_row["pet_id"],
        pet_name=app_row.get("pet_name") or f"宠物{app_row['pet_id']}",
        overall_satisfaction=req.overall_satisfaction,
        bond_level=req.bond_level,
        unexpected_challenges=req.unexpected_challenges,
        would_recommend=req.would_recommend,
        free_feedback=req.free_feedback,
    )

    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        next_flow_status = flow_engine.resolve_feedback_flow_status(app_row.get("flow_status"))
        conn.execute(
            "UPDATE applications SET feedback_written=1, flow_status=? WHERE id=?",
            (next_flow_status, application_id),
        )
        flow_engine.append_event(
            conn,
            application_id=application_id,
            event_type="feedback_written",
            from_status=app_row.get("flow_status") or "adopted",
            to_status=next_flow_status,
            actor_role="applicant" if current_user.get("role") != "org_admin" else "admin",
            actor_id=current_user["id"],
            payload={
                "overall_satisfaction": req.overall_satisfaction,
                "bond_level": req.bond_level,
                "would_recommend": req.would_recommend,
            },
        )
        conn.commit()

    latest_assessment = _parse_json_payload(app_row.get("assessment_payload"), {}).get("latest_assessment", {})
    feedback_summary = (
        f"满意度 {req.overall_satisfaction}/5，亲密度 {req.bond_level}，"
        f"是否推荐：{'是' if req.would_recommend else '否'}；挑战：{req.unexpected_challenges or '无'}"
    )
    upsert_case_memory(
        application_id=application_id,
        case_summary=build_case_summary(app_row, feedback_summary=feedback_summary),
        decision_result=app_row.get("status") or "approved",
        owner_followed_ai=app_row.get("owner_followed_ai"),
        followup_outcome=feedback_summary,
        risk_tags=latest_assessment.get("consensus_result", {}).get("risk_tags", []),
        feedback_id=feedback_id,
        embedding_status="synced",
    )
    update_signal_weights_from_feedback(
        route_decision=(latest_assessment.get("route_decision") or {}).get("next_action", ""),
        risk_tags=latest_assessment.get("consensus_result", {}).get("risk_tags", []),
        followup_questions=latest_assessment.get("followup_questions", []) or _parse_json_payload(app_row.get("followup_questions"), []),
        overall_satisfaction=req.overall_satisfaction,
        would_recommend=req.would_recommend,
    )

    return {"status": "success", "feedback_id": feedback_id}

@router.get("/pet-chat/history")
async def get_pet_chat_history(pet_name: str, user_id: int):
    """获取指定用户与指定宠物的历史聊天记录（最近 30 条）"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, create_time FROM pet_chat_history "
            "WHERE user_id=? AND pet_name=? ORDER BY create_time ASC LIMIT 30",
            (user_id, pet_name)
        )
        rows = [dict(r) for r in cursor.fetchall()]
    return rows


@router.get("/pet-chat/profile")
async def get_pet_chat_profile(pet_name: str, user_id: int):
    """获取用户与指定宠物聊天过程中形成的隐式领养画像。"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT profile_json, summary, updated_at FROM pet_chat_profiles WHERE user_id=? AND pet_name=?",
            (user_id, pet_name)
        )
        row = cursor.fetchone()
    if not row:
        return {
            "profile": {
                "user_traits": [],
                "strengths": [],
                "risk_flags": [],
                "missing_topics": [],
                "next_probe": "",
                "interview_stage": "early",
                "summary": ""
            },
            "updated_at": None
        }
    try:
        profile = json.loads(row["profile_json"] or "{}")
    except Exception:
        profile = {}
    if not profile.get("summary") and row["summary"]:
        profile["summary"] = row["summary"]
    return {"profile": profile, "updated_at": row["updated_at"]}


@router.post("/pet-chat")
@limiter.limit("10/minute")
async def pet_chat(request: Request, req: PetChatRequest):
    """
    宠物拟人化聊天接口：以宠物口吻回复用户，并返回 Edge-TTS 语音 base64。
    支持长期记忆：从数据库读取历史对话注入上下文，并将本轮对话存入数据库。
    """
    history = []
    observer_profile = {
        "user_traits": [],
        "strengths": [],
        "risk_flags": [],
        "missing_topics": [],
        "next_probe": "你平时会怎么照顾我呀？",
        "interview_stage": "early",
        "summary": ""
    }
    response_text = "我刚刚有点紧张，不过我还是很想继续认识你。你愿意再和我说说你的生活节奏吗？"
    audio_base64 = None

    try:
        if req.user_id:
            with get_db() as conn:
                from src.web.services.db_service import ensure_tables
                ensure_tables(conn)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content FROM pet_chat_history "
                    "WHERE user_id=? AND pet_name=? ORDER BY create_time ASC LIMIT 10",
                    (req.user_id, req.pet_name)
                )
                history = [dict(r) for r in cursor.fetchall()]
                cursor.execute(
                    "SELECT profile_json, summary FROM pet_chat_profiles WHERE user_id=? AND pet_name=?",
                    (req.user_id, req.pet_name)
                )
                profile_row = cursor.fetchone()
                if profile_row:
                    try:
                        observer_profile = json.loads(profile_row["profile_json"] or "{}")
                    except Exception:
                        observer_profile = {}
                    if profile_row["summary"] and not observer_profile.get("summary"):
                        observer_profile["summary"] = profile_row["summary"]

        observer_profile = await analyze_pet_interview(
            user_msg=req.user_msg,
            pet_name=req.pet_name,
            pet_species=req.pet_species,
            pet_desc=req.pet_desc,
            history=history,
            previous_profile=observer_profile,
        )

        response_text, audio_base64 = await run_pet_chat(
            user_msg=req.user_msg,
            pet_name=req.pet_name,
            pet_species=req.pet_species,
            pet_desc=req.pet_desc,
            history=history,
            observer_profile=observer_profile,
        )
    except Exception:
        logger.exception("pet_chat pipeline failed")
        observer_profile = {
            **observer_profile,
            "summary": observer_profile.get("summary") or f"已记录你正在了解{req.pet_name}，系统会继续补充画像。"
        }
        if "猫" in req.pet_species:
            response_text = "喵，我刚刚有点卡壳了，不过还是想继续认识你。你平时下班后能陪我多久呀？"
        elif "狗" in req.pet_species or "犬" in req.pet_species:
            response_text = "汪，我刚才没接上话，不过我还是很想了解你。你每天能带我出门和陪我玩吗？"
        else:
            response_text = "我刚刚有点紧张，不过还是想继续认识你。你愿意再和我说说你的照顾计划吗？"

    if req.user_id:
        try:
            with get_db() as conn:
                from src.web.services.db_service import ensure_tables
                ensure_tables(conn)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO pet_chat_history (user_id, pet_name, role, content) VALUES (?,?,?,?)",
                    (req.user_id, req.pet_name, "user", req.user_msg)
                )
                cursor.execute(
                    "INSERT INTO pet_chat_history (user_id, pet_name, role, content) VALUES (?,?,?,?)",
                    (req.user_id, req.pet_name, "pet", response_text)
                )
                cursor.execute(
                    """
                    INSERT INTO pet_chat_profiles (user_id, pet_name, profile_json, summary, updated_at)
                    VALUES (?,?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, pet_name) DO UPDATE SET
                        profile_json=excluded.profile_json,
                        summary=excluded.summary,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        req.user_id,
                        req.pet_name,
                        json.dumps(observer_profile, ensure_ascii=False),
                        observer_profile.get("summary", "")
                    )
                )
                conn.commit()
        except Exception:
            logger.exception("pet_chat persistence failed")

    return {
        "text": response_text,
        "audio_base64": audio_base64,
        "observer_profile": observer_profile
    }


@router.post("/mutual-aid/tasks")
async def create_mutual_aid_task(req: MutualAidTaskCreate, current_user: dict = Depends(get_current_user)):
    """发布互助任务"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO mutual_aid_tasks
               (user_id, task_type, pet_name, pet_species, start_time, end_time, location, description, status)
               VALUES (?,?,?,?,?,?,?,?,'open')""",
            (current_user["id"], req.task_type, req.pet_name, req.pet_species,
             req.start_time, req.end_time, req.location, req.description)
        )
        task_id = cursor.lastrowid
        cursor.execute("SELECT * FROM mutual_aid_tasks WHERE id=?", (task_id,))
        created_task = dict(cursor.fetchone())
        conn.commit()
    return {"status": "success", "task_id": task_id, "task": created_task}


@router.get("/mutual-aid/tasks")
async def list_mutual_aid_tasks(status: str = "open", limit: int = 20):
    """获取互助任务列表"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM mutual_aid_tasks WHERE status=? ORDER BY create_time DESC LIMIT ?",
            (status, limit)
        )
        rows = [dict(r) for r in cursor.fetchall()]
    return rows


@router.post("/mutual-aid/tasks/{task_id}/accept")
async def accept_mutual_aid_task(task_id: int, req: MutualAidAcceptRequest, current_user: dict = Depends(get_current_user)):
    """接单"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT status, user_id FROM mutual_aid_tasks WHERE id=?", (task_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="任务不存在")
        if row["status"] != "open":
            raise HTTPException(status_code=400, detail="该任务已被接单")
        if row["user_id"] == current_user["id"]:
            raise HTTPException(status_code=400, detail="不能接自己发布的任务")
        cursor.execute("UPDATE mutual_aid_tasks SET status='accepted' WHERE id=?", (task_id,))
        cursor.execute(
            "INSERT INTO mutual_aid_orders (task_id, helper_id, status) VALUES (?,?,'accepted')",
            (task_id, current_user["id"])
        )
        conn.commit()
    return {"status": "success"}


@router.post("/mutual-aid/match")
@limiter.limit("10/minute")
async def mutual_aid_match(request: Request, req: MutualAidMatchRequest, current_user: dict = Depends(get_current_user)):
    """AI 多智能体互助匹配推荐"""
    reply, trace_id = get_mutual_aid_match(req.query, current_user["id"])
    return {"reply": reply, "trace_id": trace_id}


@router.post("/mutual-aid/tasks/{task_id}/complete")
async def complete_mutual_aid_task(task_id: int, current_user: dict = Depends(get_current_user)):
    """完成任务：发布人或接单人均可标记完成"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT status, user_id FROM mutual_aid_tasks WHERE id=?", (task_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="任务不存在")
        if row["status"] not in ("accepted",):
            raise HTTPException(status_code=400, detail="只有已接单的任务才能标记完成")
        # 验证操作人是发布人或接单人
        cursor.execute("SELECT helper_id FROM mutual_aid_orders WHERE task_id=? AND status='accepted'", (task_id,))
        order = cursor.fetchone()
        allowed = [row["user_id"]]
        if order:
            allowed.append(order["helper_id"])
        if current_user["id"] not in allowed:
            raise HTTPException(status_code=403, detail="无权操作此任务")
        cursor.execute("UPDATE mutual_aid_tasks SET status='completed' WHERE id=?", (task_id,))
        if order:
            cursor.execute("UPDATE mutual_aid_orders SET status='completed' WHERE task_id=?", (task_id,))
        conn.commit()
    return {"status": "success"}


@router.get("/mutual-aid/tasks/mine")
async def get_my_mutual_aid_tasks(current_user: dict = Depends(get_current_user)):
    """我的互助：我发布的任务 + 我接的单（含接单人信息）"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        # 我发布的任务，带接单人信息
        cursor.execute(
            """SELECT t.*, u.username as helper_name, u.email as helper_email
               FROM mutual_aid_tasks t
               LEFT JOIN mutual_aid_orders o ON t.id = o.task_id AND o.status != 'cancelled'
               LEFT JOIN users u ON o.helper_id = u.id
               WHERE t.user_id=?
               ORDER BY t.create_time DESC""",
            (current_user["id"],)
        )
        published = [dict(r) for r in cursor.fetchall()]
        # 我接的单，带任务详情
        cursor.execute(
            """SELECT t.*, o.status as order_status
               FROM mutual_aid_orders o
               JOIN mutual_aid_tasks t ON o.task_id = t.id
               WHERE o.helper_id=?
               ORDER BY o.create_time DESC""",
            (current_user["id"],)
        )
        accepted = [dict(r) for r in cursor.fetchall()]
    return {"published": published, "accepted": accepted}


@router.post("/mutual-aid/tasks/{task_id}/report")
async def report_mutual_aid_task(
    task_id: int,
    req: MutualAidReportRequest,
    current_user: dict = Depends(get_current_user)
):
    """举报互助任务"""
    with get_db() as conn:
        from src.web.services.db_service import ensure_tables
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM mutual_aid_tasks WHERE id=?", (task_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="任务不存在")
        # 防重复举报
        cursor.execute(
            "SELECT id FROM mutual_aid_reports WHERE task_id=? AND reporter_id=? AND status='pending'",
            (task_id, current_user["id"])
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="您已举报过该任务，请等待处理")
        cursor.execute(
            "INSERT INTO mutual_aid_reports (task_id, reporter_id, reason) VALUES (?,?,?)",
            (task_id, current_user["id"], req.reason)
        )
        conn.commit()
    return {"status": "success"}


@router.get("/admin/assessment/report/{trace_id}")
async def get_assessment_report(trace_id: str, current_user: dict = Depends(get_current_user)):
    """
    [管理员专享] 获取结构化的 AI 审核详情报告。
    用于解决 AI 黑盒决策问题，提供审计追踪依据。
    """
    if current_user.get("role") not in ["org_admin"]:
        raise HTTPException(status_code=403, detail="无权查阅 AI 审计日志")
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT input_msg, output_msg FROM agent_trace_logs WHERE trace_id = ?", (trace_id,))
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="未找到相关评估记录")

    input_msg, output_msg = row[0], row[1]
    assessment_data = json.loads(output_msg)
    
    return {
        "report_id": trace_id,
        "applicant_snapshot": json.loads(input_msg),
        "ai_decision_summary": {
            "final_score": assessment_data.get("readiness_score"),
            "conclusion": assessment_data.get("decision"),
            "confidence": assessment_data.get("confidence_level"),
            "risk_tags": assessment_data.get("risk_tags", [])
        },
        "expert_reasoning": assessment_data.get("expert_summary")
    }
