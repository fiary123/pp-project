class PetFeatureHydrator:
    """
    数据补全器 - 为候选宠物填充特征，并实现统计学补全 (Statistical Completion)
    如果数据库中缺失结构化特征，则基于品种基准值进行补全。
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service
        
        # 统计学基准特征 (基于品种的常识统计)
        self.species_defaults = {
            "猫咪": {
                "energy_level": "中", "care_level": "容易", "social_level": "独立",
                "companionship_need": "低", "budget_need_level": "低", "beginner_friendly": 1
            },
            "狗狗": {
                "energy_level": "高", "care_level": "中等", "social_level": "友好",
                "companionship_need": "高", "budget_need_level": "中", "beginner_friendly": 1
            },
            "异宠": {
                "energy_level": "低", "care_level": "困难", "social_level": "胆小",
                "companionship_need": "低", "budget_need_level": "中", "beginner_friendly": 0
            }
        }

    async def hydrate(self, query, candidates):
        for candidate in candidates:
            pet_id = candidate.candidate_id
            pet_base = candidate.raw_data.get("pet", {})
            species = pet_base.get("type") or pet_base.get("species") or "猫咪"
            
            # 获取品种默认基准 (统计补全逻辑)
            defaults = self.species_defaults.get(species, self.species_defaults["猫咪"])
            
            # 从数据库获取真实特征
            feature = self.profile_service.get_pet_features(pet_id)
            requirement = self.profile_service.get_pet_requirements(pet_id)

            if not feature: feature = {}
            if not requirement: requirement = {}

            # 填充特征 (优先使用真实数据，缺失则使用统计基准)
            candidate.features["pet"] = {
                "species": pet_base.get("species") or feature.get("species"),
                "age_stage": feature.get("age_stage", "成年"),
                "size_level": feature.get("size_level", "中型"),
                "health_status": feature.get("health_status", "健康"),
                "sterilized": bool(feature.get("sterilized", 0)),
                "energy_level": feature.get("activity_level") or defaults["energy_level"],
                "care_level": feature.get("care_difficulty") or defaults["care_level"],
                "social_level": feature.get("activity_level") or defaults["social_level"], # 映射近似字段
                "temperament_tags": feature.get("temperament_tags", ""),
                "good_with_children": bool(feature.get("good_with_children", 1)),
                "good_with_other_pets": bool(feature.get("good_with_other_pets", 1)),
                "companionship_need": feature.get("companionship_need") or defaults["companionship_need"],
                "budget_need_level": feature.get("budget_need_level") or defaults["budget_need_level"],
                "special_care_flag": bool(feature.get("special_care_flag", 0)),
            }

            # 填充硬约束要求
            candidate.features["requirement"] = {
                "allow_beginner": bool(requirement.get("allow_beginner", defaults["beginner_friendly"])),
                "min_budget_level": requirement.get("min_budget_level", "低"),
                "min_companion_hours": float(requirement.get("min_companion_hours", 0)),
                "required_housing_type": requirement.get("required_housing_type"),
                "forbid_other_pets": bool(requirement.get("forbid_other_pets", 0)),
                "forbid_children": bool(requirement.get("forbid_children", 0)),
                "require_experience": requirement.get("require_experience", "无"),
                "require_stable_housing": bool(requirement.get("require_stable_housing", 1)),
            }
            
            candidate.stage_trace["feature_hydration"] = {
                "stage": "结构化特征补全",
                "method": "RealData + StatisticalImputation",
                "dimensions": ["生理特征", "行为特征", "约束条件"]
            }

        return candidates
