from fastapi import APIRouter, Depends, HTTPException
from src.web.services.profile_service import ProfileService
from src.web.services.recommendation_service import RecommendationService
from src.web.services.pet_service import PetService
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/recommendation", tags=["recommendation"])

@router.get("/pets/{user_id}")
async def get_pet_recommendations(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取个性化宠物推荐 (领养人视角)"""
    # 权限检查：只能为自己或作为管理员获取推荐
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权获取他人的推荐")

    # 实例化服务
    profile_service = ProfileService()
    recommender = RecommendationService(profile_service)

    # 执行推荐逻辑
    results = await recommender.recommend_pets_for_user(user_id)

    # 格式化输出
    return [
        {
            "pet_id": item.candidate_id,
            "pet_name": item.raw_data.get("pet", {}).get("name"),
            "species": item.raw_data.get("pet", {}).get("species"),
            "score": round(item.final_score, 2),
            "reasons": item.reasons,
            "risk_flags": item.risk_flags,
            "sub_scores": item.scores,
            "image_url": item.raw_data.get("pet", {}).get("image_url")
        }
        for item in results
    ]

@router.get("/pets/{pet_id}/applicants")
async def rank_applicants(pet_id: int, current_user: dict = Depends(get_current_user)):
    """获取申请人匹配度排序 (发布者/送养人视角)"""
    pet_service = PetService()
    pet = pet_service.get_by_id(pet_id)
    if not pet:
        raise HTTPException(status_code=404, detail="宠物不存在")

    # 权限检查：仅宠物发布者或管理员有权查看申请人排名
    if pet["owner_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅宠物发布者可查看申请人排名")

    profile_service = ProfileService()
    recommender = RecommendationService(profile_service)

    # 执行流水线排序
    results = await recommender.rank_applicants_for_pet(pet_id)

    return [
        {
            "user_id": item.candidate_id,
            "score": round(item.final_score, 2),
            "reasons": item.reasons,
            "risk_flags": item.risk_flags,
            "sub_scores": item.scores,
            "application_status": item.features.get("application", {}).get("status")
        }
        for item in results
    ]

