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

            candidate.features["pet"] = {
                "species": pet_base.get("species"),
                "age": pet_base.get("age"),
                "energy_level": feature.get("energy_level") if feature else None,
                "care_level": feature.get("care_level") if feature else None,
                "beginner_friendly": bool(feature.get("beginner_friendly", 1)) if feature else True,
                "social_level": feature.get("social_level") if feature else None,
                "special_care_flag": bool(feature.get("special_care_flag", 0)) if feature else False,
            }

            candidate.features["requirement"] = {
                "require_experience": requirement.get("require_experience") if requirement else None,
                "require_stable_housing": bool(requirement.get("require_stable_housing", 1)) if requirement else True,
                "require_return_visit": bool(requirement.get("require_return_visit", 1)) if requirement else True,
                "region_limit": requirement.get("region_limit") if requirement else None,
            }

        return candidates
