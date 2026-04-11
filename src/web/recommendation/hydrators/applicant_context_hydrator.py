class ApplicantContextHydrator:
    """
    数据补全器 - 为申请人候选对象填充完整的评估上下文（包括申请人画像、宠物特征、领养要求）
    """
    def __init__(self, profile_service, pet_service):
        self.profile_service = profile_service
        self.pet_service = pet_service

    async def hydrate(self, query, candidates):
        # 1. 先获取目标宠物的基本信息和相关特征/要求
        pet_base = self.pet_service.get_by_id(query.pet_id)
        pet_feature = self.profile_service.get_pet_features(query.pet_id)
        pet_requirement = self.profile_service.get_pet_requirements(query.pet_id)

        # 2. 对每个申请人候选对象进行数据补全
        for candidate in candidates:
            application = candidate.raw_data.get("application", {})
            user_id = candidate.candidate_id

            # 获取申请人的画像和偏好
            profile = self.profile_service.get_user_profile(user_id)
            preference = self.profile_service.get_user_preferences(user_id)

            # 填充申请人特征
            candidate.features["applicant_profile"] = {
                "housing_type": profile.get("housing_type") if profile else None,
                "housing_size": profile.get("housing_size") if profile else None,
                "rental_status": profile.get("rental_status") if profile else None,
                "pet_experience": profile.get("pet_experience") if profile else None,
                "available_time": profile.get("available_time") if profile else None,
                "family_support": bool(profile.get("family_support", 0)) if profile else False,
                "budget_level": profile.get("budget_level") if profile else None,
            }

            candidate.features["applicant_preference"] = {
                "preferred_pet_type": preference.get("preferred_pet_type") if preference else None,
                "preferred_age_range": preference.get("preferred_age_range") if preference else None,
                "preferred_size": preference.get("preferred_size") if preference else None,
                "accept_special_care": bool(preference.get("accept_special_care", 0)) if preference else False,
                "accept_high_energy": bool(preference.get("accept_high_energy", 1)) if preference else True,
            }

            # 填充申请表自带特征
            candidate.features["application"] = {
                "accept_return_visit": bool(application.get("accept_return_visit", 0)),
                "apply_reason": application.get("apply_reason", ""),
                "status": application.get("status", "pending"),
            }

            # 填充目标宠物特征
            candidate.features["pet"] = {
                "species": pet_base.get("species") if pet_base else None,
                "age": pet_base.get("age") if pet_base else None,
                "energy_level": pet_feature.get("energy_level") if pet_feature else None,
                "care_level": pet_feature.get("care_level") if pet_feature else None,
                "beginner_friendly": bool(pet_feature.get("beginner_friendly", 1)) if pet_feature else True,
                "social_level": pet_feature.get("social_level") if pet_feature else None,
                "special_care_flag": bool(pet_feature.get("special_care_flag", 0)) if pet_feature else False,
            }

            # 填充送养人的要求
            candidate.features["requirement"] = {
                "require_experience": pet_requirement.get("require_experience") if pet_requirement else None,
                "require_stable_housing": bool(pet_requirement.get("require_stable_housing", 1)) if pet_requirement else True,
                "require_return_visit": bool(pet_requirement.get("require_return_visit", 1)) if pet_requirement else True,
                "region_limit": pet_requirement.get("region_limit") if pet_requirement else None,
            }

        return candidates
