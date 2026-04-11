class UserQueryHydrator:
    """
    请求补全器 - 获取用户的画像和偏好，填充到 Query 对象中
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service

    async def hydrate(self, query):
        profile = self.profile_service.get_user_profile(query.user_id)
        preference = self.profile_service.get_user_preferences(query.user_id)

        # 转换为统一的字典格式，方便后续 Filter 和 Scorer 使用
        query.user_profile = {
            "housing_type": profile.get("housing_type") if profile else None,
            "housing_size": profile.get("housing_size") if profile else None,
            "rental_status": profile.get("rental_status") if profile else None,
            "pet_experience": profile.get("pet_experience") if profile else None,
            "available_time": profile.get("available_time") if profile else None,
            "family_support": bool(profile.get("family_support", 0)) if profile else False,
            "budget_level": profile.get("budget_level") if profile else None,
        }

        query.user_preferences = {
            "preferred_pet_type": preference.get("preferred_pet_type") if preference else None,
            "preferred_age_range": preference.get("preferred_age_range") if preference else None,
            "preferred_size": preference.get("preferred_size") if preference else None,
            "accept_special_care": bool(preference.get("accept_special_care", 0)) if preference else False,
            "accept_high_energy": bool(preference.get("accept_high_energy", 1)) if preference else True,
        }
        
        return query
