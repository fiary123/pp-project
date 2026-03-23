from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from typing import Optional
import json
from src.web.schemas import (
    ChatRequest, NutritionPlanRequest, SmartMatchRequest,
    NutritionFeedbackRequest, NutritionReplanRequest, AdoptionAssessmentRequest,
    MatchFollowupRequest, AdoptionFeedbackRequest
)
from src.web.services.ai_service import (
    get_agent_reply, get_triage_reply, generate_nutrition_plan,
    get_smart_match, get_match_followup_questions, submit_adoption_feedback,
    submit_nutrition_feedback, replan_nutrition,
    run_adoption_assessment_service,
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
        user_message=req.message
    )
    return {
        "reply": result["reply"],
        "ui_actions": result["ui_actions"],
        "stage": result["stage"],
        "trace_id": "coord_" + session_id
    }

@router.post("/triage/analyze")
@limiter.limit("15/minute")
async def triage_analyze(request: Request, symptom: str = Form(...), file: UploadFile = File(None)):
    reply, trace_id = get_triage_reply(symptom)
    return {"reply": reply, "trace_id": trace_id}

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

@router.get("/admin/assessment/report/{trace_id}")
async def get_assessment_report(trace_id: str, current_user: dict = Depends(get_current_user)):
    """
    [管理员专享] 获取结构化的 AI 审核详情报告。
    用于解决 AI 黑盒决策问题，提供审计追踪依据。
    """
    if current_user.get("role") not in ["org_admin", "root"]:
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
