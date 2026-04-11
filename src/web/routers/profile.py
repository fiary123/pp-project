from fastapi import APIRouter, Depends, HTTPException
from src.web.schemas import UserProfileUpdate, UserPreferenceUpdate
from src.web.services.profile_service import ProfileService
from src.web.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/{user_id}")
async def get_profile(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取用户画像"""
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权查看他人画像")
    profile = ProfileService.get_user_profile(user_id)
    return profile if profile else {}

@router.put("/{user_id}")
async def update_profile(user_id: int, profile: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    """更新用户画像"""
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权修改他人画像")
    ProfileService.update_user_profile(user_id, profile)
    return {"message": "画像更新成功"}

@router.get("/{user_id}/preference")
async def get_preference(user_id: int, current_user: dict = Depends(get_current_user)):
    """获取用户领养偏好"""
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权查看他人偏好")
    prefs = ProfileService.get_user_preferences(user_id)
    return prefs if prefs else {}

@router.put("/{user_id}/preference")
async def update_preference(user_id: int, prefs: UserPreferenceUpdate, current_user: dict = Depends(get_current_user)):
    """更新用户领养偏好"""
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="无权修改他人偏好")
    ProfileService.update_user_preferences(user_id, prefs)
    return {"message": "领养偏好更新成功"}
