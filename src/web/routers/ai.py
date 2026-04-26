from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import logging
import json
import os
from src.web.services.db_service import get_db
from src.web.dependencies import get_current_user, get_optional_user
from src.web.schemas import AdoptionAssessmentRequest, PetChatRequest, NutritionPlanRequest, SmartMatchRequest
from src.web.services.ai_service import generate_nutrition_plan, get_smart_match

router = APIRouter(prefix="/api/ai", tags=["AI Components"])
logger = logging.getLogger(__name__)

# --- 核心逻辑：自适应信息采集 (对齐测试表 Case 1-4) ---

def _build_smart_questions(pet_info: dict, features: dict, requirements: dict, profile: dict) -> list:
    """
    [创新机制：自适应追问引擎]
    根据用户画像完整度及宠物硬约束，动态构建具备“针对性”的追问表单。
    """
    questions = []
    pet_name = pet_info.get("name", "宠物")
    
    # 1. 约束驱动：高优先级拦截确认 (测试案例 4)
    # 如果宠物明确要求无幼儿
    if requirements.get("forbid_children") == 1:
        questions.append({
            "key": "has_young_children",
            "question": f"【关键环境确认】送养人提到 {pet_name} 比较敏感，要求领养家庭无 6 岁以下幼儿，请问您家里的情况是？",
            "options": [
                {"label": "确定没有 6 岁以下幼儿", "value": "none"},
                {"label": "有 6 岁以下幼儿", "value": "has_young_kids"}
            ],
            "priority": "essential"
        })

    # 2. 画像补全：针对性缺失项采集 (测试案例 2)
    # 缺失家庭构成
    if not profile.get("family_size") or profile.get("family_size") == 0:
        questions.append({
            "key": "family_composition",
            "question": f"为了评估您是否有足够精力照顾 {pet_name}，能告知您的家庭成员构成吗？",
            "options": [
                {"label": "独自居住 (单身)", "value": "single"},
                {"label": "情侣/夫妻二人世界", "value": "couple"},
                {"label": "大家庭 (三代同堂)", "value": "big_family"}
            ],
            "priority": "medium"
        })

    # 缺失养宠经验
    if not profile.get("pet_experience") or profile.get("pet_experience") == "无":
        # 如果该宠物不适合新手
        if requirements.get("allow_beginner") == 0:
            questions.append({
                "key": "experience_detail",
                "question": f"【经验追问】{pet_name} 需要有一定经验的主人。请描述您照顾类似动物的经历：",
                "options": [
                    {"label": "养过同品种宠物多年", "value": "expert"},
                    {"label": "有帮人寄养/义工经历", "value": "experience"},
                    {"label": "完全新手，但愿意学习", "value": "beginner"}
                ],
                "priority": "high"
            })
        else:
            questions.append({
                "key": "experience_general",
                "question": f"您过往是否有照顾小动物的经历？这能帮助我们更好地匹配 {pet_name}。",
                "options": [
                    {"label": "从未养过宠物", "value": "none"},
                    {"label": "养过猫/狗/仓鼠等", "value": "some"},
                    {"label": "资深铲屎官", "value": "rich"}
                ],
                "priority": "low"
            })

    # 缺失预算情况
    if not profile.get("budget_level") or profile.get("budget_level") == "低":
        questions.append({
            "key": "budget_commitment",
            "question": f"最后，请确认您每月愿意为 {pet_name} 投入的开销预算（含口粮、医疗）：",
            "options": [
                {"label": "300 - 800 元/月", "value": "basic"},
                {"label": "800 - 1500 元/月", "value": "standard"},
                {"label": "1500 元以上/月", "value": "premium"}
            ],
            "priority": "medium"
        })

    # 3. 动态控制总量：如果画像非常完整 (测试案例 3)，上述问题会自动跳过，
    #    只会保留针对性的确认（如第 1 步的约束确认）。
    
    return questions

# =================================================================
# 路由定义
# =================================================================

@router.get("/adoption-questions/{pet_id}")
async def generate_adoption_questions(pet_id: int, current_user: dict = Depends(get_current_user)):
    """[动态分诊] 获取针对该宠物的申请追问"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 聚合该宠物的所有背景与约束
        cursor.execute("SELECT * FROM pet_features WHERE pet_id = ?", (pet_id,))
        features = dict(cursor.fetchone() or {})
        cursor.execute("SELECT * FROM pet_requirements WHERE pet_id = ?", (pet_id,))
        requirements = dict(cursor.fetchone() or {})
        cursor.execute("SELECT name, species FROM pets WHERE id = ?", (pet_id,))
        pet_info = dict(cursor.fetchone() or {})
        # 获取当前用户画像
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (current_user["id"],))
        profile = dict(cursor.fetchone() or {})

    # 核心调用
    questions = _build_smart_questions(pet_info, features, requirements, profile)
    
    # 限制返回数量，确保不造成填报负担
    return {
        "questions": questions[:4], 
        "pet_name": pet_info.get("name", ""),
        "adaptive_mode": "full" if len(questions) > 2 else "lite"
    }

@router.post("/assessment/immediate")
async def immediate_assess(req: AdoptionAssessmentRequest, current_user: dict | None = Depends(get_optional_user)):
    """提交申请前的即时资质预估"""
    from src.web.services.assessment_service import AdoptionAssessmentService
    service = AdoptionAssessmentService()
    return await service.run_full_assessment(current_user["id"] if current_user else 0, req.model_dump())

@router.post("/extensions/pet-chat")
async def pet_persona_chat(req: PetChatRequest):
    """宠物拟人化聊天"""
    from src.agents.agents import run_pet_chat
    res, audio = await run_pet_chat(req.user_msg, req.pet_name, req.pet_species, req.pet_desc, [], {})
    return {"reply": res, "audio": audio}

@router.post("/extensions/nutrition-plan")
async def nutrition_extension(req: NutritionPlanRequest):
    """生成养护建议"""
    plan, md, trace_id, plan_id = generate_nutrition_plan(req.model_dump())
    return {"plan": plan, "explanation": md}

@router.post("/extensions/smart-match")
async def match_extension(req: SmartMatchRequest):
    """语义匹配搜索"""
    return get_smart_match(req.user_query, req.pet_list, [])
