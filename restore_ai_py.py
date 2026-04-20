content = """from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, BackgroundTasks
from typing import Optional, Any
import json
import logging
from src.web.schemas import (
    ChatRequest, NutritionPlanRequest, SmartMatchRequest,
    AdoptionAssessmentRequest, MatchFollowupRequest, PetChatRequest,
    MutualAidTaskCreate, MutualAidMatchRequest, AdoptionEvaluationFollowupRequest,
    AdoptionEvaluationReviewRequest, AdoptionEvaluationFeedbackRequest
)
from src.agents.agents import analyze_pet_interview, run_pet_chat
from src.agents.tools import search_pet_knowledge_hits
from src.web.services.ai_service import (
    generate_nutrition_plan, get_smart_match, get_match_followup_questions,
    submit_adoption_feedback, submit_nutrition_feedback, replan_nutrition,
    get_mutual_aid_match, ai_service
)
from src.web.services.assessment_service import AdoptionAssessmentService
from src.web.services.adoption_flow_engine import flow_engine
from src.web.services.db_service import get_db
from src.web.dependencies import get_current_user, get_optional_user
from src.web.limiter import limiter
from src.agents.coordinator import CoordinatorAgent
from langchain_openai import ChatOpenAI
import os

router = APIRouter(prefix="/api", tags=["ai"])
logger = logging.getLogger(__name__)

class LLMWrapper:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("API KEY 未设置")
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=api_key,
            openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=0.3
        )
    async def ask(self, prompt: str) -> str:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="你是宠物领养平台的中央调度AI。"),
            HumanMessage(content=prompt),
        ]
        res = await self.llm.ainvoke(messages)
        return res.content

coordinator = CoordinatorAgent(LLMWrapper(), get_db)
assessment_service = AdoptionAssessmentService()

def _parse_json_payload(raw_value: Any, fallback: Any):
    if raw_value in (None, "", b""): return fallback
    try: return json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except: return fallback

def _load_application_row(application_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT a.*, p.name AS pet_name FROM applications a LEFT JOIN pets p ON p.id = a.pet_id WHERE a.id=?", (application_id,))
        row = cursor.fetchone()
    return dict(row) if row else None

def _ensure_application_access(app_row: dict, current_user: dict):
    if not app_row: raise HTTPException(status_code=404)
    if current_user.get("role") == "admin": return
    if current_user["id"] not in {app_row.get("user_id"), app_row.get("pet_owner_id")}:
        raise HTTPException(status_code=403)

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, req: ChatRequest, current_user: dict = Depends(get_current_user)):
    res = await coordinator.handle_user_input(f"session_{current_user['id']}", current_user["id"], req.message)
    return {"reply": res["reply"], "stage": res["stage"]}

@router.post("/adoption/assess")
async def adoption_assess(request: Request, req: AdoptionAssessmentRequest, current_user: dict | None = Depends(get_optional_user)):
    return await assessment_service.run_full_assessment(current_user["id"] if current_user else 0, req.model_dump())

@router.get("/adoption/evaluate/{application_id}/status")
async def get_adoption_evaluation_status(application_id: int, current_user: dict = Depends(get_current_user)):
    app_row = _load_application_row(application_id)
    _ensure_application_access(app_row, current_user)
    res = dict(app_row)
    res["assessment_payload"] = _parse_json_payload(app_row.get("assessment_payload"), {})
    return res

@router.post("/pet-chat")
async def pet_chat(req: PetChatRequest):
    response_text, audio_base64 = await run_pet_chat(req.user_msg, req.pet_name, req.pet_species, req.pet_desc, [], {})
    return {"text": response_text, "audio_base64": audio_base64}

@router.post("/mutual-aid/tasks")
async def create_mutual_aid_task(req: MutualAidTaskCreate, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        conn.execute("INSERT INTO mutual_aid_tasks (user_id, task_type, pet_name, status) VALUES (?,?,?,'open')", (current_user["id"], req.task_type, req.pet_name))
        conn.commit()
    return {"status": "success"}

@router.get("/mutual-aid/tasks")
async def list_mutual_aid_tasks(status: str = "open"):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mutual_aid_tasks WHERE status=?", (status,))
        return [dict(r) for r in cursor.fetchall()]

@router.post("/mutual-aid/tasks/{task_id}/accept")
async def accept_mutual_aid_task(task_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        conn.execute("UPDATE mutual_aid_tasks SET status='accepted' WHERE id=?", (task_id,))
        conn.execute("INSERT INTO mutual_aid_orders (task_id, helper_id, status) VALUES (?,?,'accepted')", (task_id, current_user["id"]))
        conn.commit()
    return {"status": "success"}

@router.post("/mutual-aid/match")
async def mutual_aid_match(req: MutualAidMatchRequest, current_user: dict = Depends(get_current_user)):
    reply, trace_id = get_mutual_aid_match(req.query, current_user["id"])
    return {"reply": reply, "trace_id": trace_id}

@router.get("/admin/assessment/report/{trace_id}")
async def get_assessment_report(trace_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin": raise HTTPException(status_code=403)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT input_msg, output_msg FROM agent_trace_logs WHERE trace_id = ?", (trace_id,))
        row = cursor.fetchone()
    if not row: raise HTTPException(status_code=404)
    return {"applicant_snapshot": json.loads(row[0]), "ai_decision_summary": json.loads(row[1])}
"""

with open('src/web/routers/ai.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("ai.py restored successfully.")
