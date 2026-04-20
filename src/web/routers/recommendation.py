from fastapi import APIRouter, Depends, HTTPException
from src.web.services.profile_service import ProfileService
from src.web.services.recommendation_service import RecommendationService
from src.web.services.pet_service import PetService
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])

@router.get("/pets/{user_id}")
async def get_pet_recommendations(
    user_id: int, 
    user_query: str = "", # 新增：支持从前端传入搜索/理想描述
    current_user: dict = Depends(get_current_user)
):
    """获取个性化宠物推荐（领养人视角）"""
    # 权限检查：只能为自己或作为管理员获取推荐
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权获取他人的推荐")

    # 实例化服务
    profile_service = ProfileService()
    recommender = RecommendationService(profile_service)

    # 执行推荐逻辑 (包含冷启动检测与语义透传)
    service_res = await recommender.recommend_pets_for_user(user_id, user_query=user_query)
    results = service_res["results"]
    needs_cold_start = service_res["needs_cold_start"]
    debug_trace = getattr(service_res.get("query_obj"), "last_execution_trace", None)

    # 格式化输出
    return {
        "results": [
            {
                "rank": index + 1,
                "pet_id": item.candidate_id,
                "pet_name": item.raw_data.get("pet", {}).get("name"),
                "species": item.raw_data.get("pet", {}).get("species"),
                "score": round(item.final_score, 2),
                "workflow": "用户画像与领养需求采集 -> 候选宠物生成 -> 约束过滤 -> 多维评分 -> 推荐排序 -> 申请审核联动",
                "reasons": item.reasons,
                "risk_flags": item.risk_flags,
                "sub_scores": item.scores,
                "image_url": item.raw_data.get("pet", {}).get("image_url"),
                "constraint_passed": bool(getattr(item, "hard_filter_pass", 1)),
                "stage_trace": item.stage_trace,
            }
            for index, item in enumerate(results)
        ],
        "needs_cold_start": needs_cold_start,
        "debug_trace": debug_trace
    }

@router.get("/demo/pipeline/{user_id}")
async def get_recommendation_pipeline_demo(user_id: int, user_query: str = "", current_user: dict = Depends(get_current_user)):
    """
    [演示专用接口] 获取推荐流水线的全链路追踪数据
    展示：结构化输入 -> 候选生成 -> 约束过滤 -> 多维评分 -> 排序结果
    """
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="仅管理员或本人可访问演示数据")

    profile_service = ProfileService()
    recommender = RecommendationService(profile_service)

    # 1. 显式执行推荐，并捕获执行追踪
    # 为了演示方便，我们这里直接使用 recommend_pets_for_user
    service_res = await recommender.recommend_pets_for_user(user_id, user_query=user_query)
    
    # 2. 我们需要从 service_res 中提取 pipeline 执行时挂载在 query 上的 trace
    # 注意：推荐结果通常通过 pipeline.execute(query) 执行，trace 已经挂载在 query 上
    # 在 RecommendationService 中，query 是局部变量，我们需要稍微调整 Service 或手动重读
    
    # 获取原始数据以展示“结构化输入”
    profile = profile_service.get_user_profile(user_id)
    preference = profile_service.get_user_preferences(user_id)
    
    return {
        "input_features": {
            "user_profile": profile,
            "user_preferences": preference,
            "user_query": user_query
        },
        "pipeline_trace": service_res.get("debug_trace") or getattr(service_res.get("query_obj", {}), "last_execution_trace", {}),
        "top_results": [
            {
                "pet_name": item.raw_data.get("pet", {}).get("name"),
                "score": item.final_score,
                "reasons": item.reasons,
                "sub_scores": item.scores,
                "risk_flags": item.risk_flags
            }
            for item in service_res["results"]
        ]
    }
