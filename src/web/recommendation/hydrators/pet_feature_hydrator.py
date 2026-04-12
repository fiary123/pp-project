class PetFeatureHydrator:
    """
    数据补全器 - 为候选宠物填充详细的推荐特征和领养要求
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service

    async def hydrate(self, query, candidates):
        for candidate in candidates:
            pet_id = candidate.candidate_id
            pet_base = candidate.raw_data.get("pet", {})
            
            # 补全宠物特征
            feature = self.profile_service.get_pet_features(pet_id)
            # 补全领养要求
            requirement = self.profile_service.get_pet_requirements(pet_id)

            if not feature:
                feature = {}
            if not requirement:
                requirement = {}

            candidate.features["pet"] = {
                "species": pet_base.get("species") or feature.get("species"),
                "age": pet_base.get("age"),
                "age_stage": feature.get("age_stage", "成年"),
                "size_level": feature.get("size_level", "中型"),
                "health_status": feature.get("health_status", "健康"),
                "sterilized": bool(feature.get("sterilized", 0)),
                "energy_level": feature.get("energy_level") or "中",
                "care_level": feature.get("care_level") or "中等",
                "beginner_friendly": bool(feature.get("beginner_friendly", 1)),
                "social_level": feature.get("social_level") or "友好",
                "temperament_tags": feature.get("temperament_tags", ""),
                "good_with_children": bool(feature.get("good_with_children", 1)),
                "good_with_other_pets": bool(feature.get("good_with_other_pets", 1)),
                "companionship_need": feature.get("companionship_need", "中"),
                "budget_need_level": feature.get("budget_need_level", "中"),
                "special_care_flag": bool(feature.get("special_care_flag", 0)),
            }

            candidate.features["requirement"] = {
                "allow_beginner": bool(requirement.get("allow_beginner", 1)),
                "min_budget_level": requirement.get("min_budget_level", "低"),
                "min_companion_hours": float(requirement.get("min_companion_hours", 0)),
                "required_housing_type": requirement.get("required_housing_type"),
                "forbid_other_pets": bool(requirement.get("forbid_other_pets", 0)),
                "forbid_children": bool(requirement.get("forbid_children", 0)),
                "require_experience": requirement.get("require_experience", "无"),
                "require_stable_housing": bool(requirement.get("require_stable_housing", 1)),
                "require_return_visit": bool(requirement.get("require_return_visit", 1)),
                "region_limit": requirement.get("region_limit"),
                "special_notes": requirement.get("special_notes", "")
            }

        return candidates
