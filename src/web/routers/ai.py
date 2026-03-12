from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from typing import Optional
from src.web.schemas import ChatRequest, NutritionPlanRequest, SmartMatchRequest, NutritionFeedbackRequest, NutritionReplanRequest
from src.web.services.ai_service import (
    get_agent_reply, get_triage_reply, generate_nutrition_plan,
    get_smart_match, submit_nutrition_feedback, replan_nutrition
)

router = APIRouter(prefix="/api", tags=["ai"])

@router.post("/chat")
async def chat(request: Request, req: ChatRequest):
    reply, trace_id = get_agent_reply(req.message)
    return {"reply": reply, "trace_id": trace_id}

@router.post("/triage/analyze")
async def triage_analyze(request: Request, symptom: str = Form(...), file: UploadFile = File(None)):
    reply, trace_id = get_triage_reply(symptom)
    return {"reply": reply, "trace_id": trace_id}

@router.post("/nutrition/plan")
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

@router.post("/pets/smart-match")
async def smart_match(req: SmartMatchRequest):
    matches = get_smart_match(req.user_query, req.pet_list)
    return {"matches": matches}
