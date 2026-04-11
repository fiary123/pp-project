from fastapi import APIRouter, Depends, HTTPException
from src.web.services.profile_service import ProfileService
from src.web.services.recommendation_service import RecommendationService
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/recommendation", tags=["recommendation"])

@router.get("/pets/{user_id}")
async def get_pet_recommendations(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取个性化宠物推荐"""
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
