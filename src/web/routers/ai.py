from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from typing import Optional
from src.web.schemas import (
    ChatRequest, NutritionPlanRequest, SmartMatchRequest,
    NutritionFeedbackRequest, NutritionReplanRequest, AdoptionAssessmentRequest
)
from src.web.services.ai_service import (
    get_agent_reply, get_triage_reply, generate_nutrition_plan,
    get_smart_match, submit_nutrition_feedback, replan_nutrition,
    run_adoption_assessment_service
)
from src.web.dependencies import get_current_user
from src.web.limiter import limiter

router = APIRouter(prefix="/api", tags=["ai"])

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest):
    reply, trace_id = get_agent_reply(req.message)
    return {"reply": reply, "trace_id": trace_id}

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

@router.post("/pets/smart-match")
async def smart_match(req: SmartMatchRequest):
    matches = get_smart_match(req.user_query, req.pet_list)
    return {"matches": matches}


@router.post("/adoption/assess")
@limiter.limit("5/minute")
async def adoption_assess(
    request: Request,
    req: AdoptionAssessmentRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    领养资质多智能体评估接口（五层架构）

    L2 规则预筛  → 识别硬约束与明显风险（命中硬约束直接驳回，不消耗 LLM）
    L3 LLM 推理  → 语义动机分析、矛盾识别、四维评分
    L4 多专家协同 → 百科专家（Baseline）+ 共处风险专家
    L5 结构化输出 → readiness_score / success_probability / risk_factors / recommendations

    所有 AI 决策链路写入 agent_trace_logs，可在管理后台审计溯源。
    """
    result, trace_id = run_adoption_assessment_service(
        applicant_info=req.applicant_info,
        target_species=req.target_species,
        target_pet_name=req.target_pet_name,
        monthly_budget=req.monthly_budget,
        daily_companion_hours=req.daily_companion_hours,
        has_pet_experience=req.has_pet_experience,
        housing_type=req.housing_type,
        application_reason=req.application_reason,
        existing_pets=req.existing_pets,
    )
    return {
        "status": "success",
        # 核心评分
        "readiness_score": result["readiness_score"],
        "success_probability": result["success_probability"],
        "confidence_level": result["confidence_level"],
        # 决策结论
        "risk_level": result["risk_level"],
        "decision": result["decision"],
        "need_manual_review": result["need_manual_review"],
        # 详细分析
        "risk_factors": result["risk_factors"],
        "recommendations": result["recommendations"],
        "review_note": result["review_note"],
        # 子报告
        "baseline_report": result["baseline_report"],
        "profile_report": result["profile_report"],
        "cohabitation_report": result["cohabitation_report"],
        "final_summary": result["final_summary"],
        # 追踪
        "trace_id": trace_id,
    }
