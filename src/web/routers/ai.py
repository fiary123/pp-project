from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from typing import Optional
import json
from src.web.schemas import (
    ChatRequest, NutritionPlanRequest, SmartMatchRequest,
    NutritionFeedbackRequest, NutritionReplanRequest, AdoptionAssessmentRequest,
    MatchFollowupRequest, AdoptionFeedbackRequest, PetChatRequest,
    MutualAidTaskCreate, MutualAidMatchRequest, MutualAidAcceptRequest,
    MutualAidReportRequest
)
from src.agents.agents import run_pet_chat
from src.web.services.ai_service import (
    get_agent_reply, generate_nutrition_plan,
    get_smart_match, get_match_followup_questions, submit_adoption_feedback,
    submit_nutrition_feedback, replan_nutrition,
    run_adoption_assessment_service, get_mutual_aid_match,
    get_db
)
from src.web.services.assessment_service import AdoptionAssessmentService
from src.web.dependencies import get_current_user
from src.web.limiter import limiter
from src.agents.coordinator import CoordinatorAgent
from langchain_openai import ChatOpenAI
import os

router = APIRouter(prefix="/api", tags=["ai"])

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
        res = await self.llm.ainvoke(prompt)
        return res.content

coordinator = CoordinatorAgent(LLMWrapper(), get_db)
assessment_service = AdoptionAssessmentService()


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
    try:
        import chromadb
        from src.database.db_config import CHROMA_DB_PATH
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(name="pet_knowledge")
        if collection.count() == 0:
            return {"results": [], "message": "知识库尚未初始化"}
        results = collection.query(
            query_texts=[keyword],
            n_results=min(5, collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        items = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            items.append({
                "text": doc[:300],
                "category": meta.get("category"),
                "similarity": round(1 - dist, 3),
                "meta": meta
            })
        return {"results": items, "keyword": keyword}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/pet-chat")
@limiter.limit("10/minute")
async def pet_chat(request: Request, req: PetChatRequest):
    """
    宠物拟人化聊天接口：以宠物口吻回复用户，并返回 Edge-TTS 语音 base64。
    支持长期记忆：从数据库读取历史对话注入上下文，并将本轮对话存入数据库。
    """
    history = []
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

    response_text, audio_base64 = run_pet_chat(
        user_msg=req.user_msg,
        pet_name=req.pet_name,
        pet_species=req.pet_species,
        pet_desc=req.pet_desc,
        history=history
    )

    # 存储本轮对话
    if req.user_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO pet_chat_history (user_id, pet_name, role, content) VALUES (?,?,?,?)",
                (req.user_id, req.pet_name, "user", req.user_msg)
            )
            cursor.execute(
                "INSERT INTO pet_chat_history (user_id, pet_name, role, content) VALUES (?,?,?,?)",
                (req.user_id, req.pet_name, "pet", response_text)
            )
            conn.commit()

    return {
        "text": response_text,
        "audio_base64": audio_base64
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
        conn.commit()
    return {"status": "success", "task_id": task_id}


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
