class MultiFeatureScorer:
    """
    多维精排评分器 - 结构化匹配与可解释性增强版
    对齐前端维度：condition (居住契合), preference (偏好对齐), experience (经验适配), penalty (风险抵扣)
    """

    async def score(self, query, candidates):
        profile = query.user_profile
        pref = query.user_preferences
        budget_map = {"低": 1, "中": 2, "高": 3}
        size_order = {"小型": 1, "中型": 2, "大型": 3}

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            # 初始化四个对齐前端的维度分
            preference_score = 50.0
            condition_score = 50.0
            experience_score = 50.0
            penalty = 0.0

            # 1. 偏好对齐 (Preference)
            if pref.get("preferred_pet_type") == pet.get("species"):
                preference_score += 20.0
                candidate.reasons.append(f"品种契合：符合您对 {pet.get('species')} 的偏好")

            if pref.get("preferred_age_range") == pet.get("age_stage"):
                preference_score += 10.0
                candidate.reasons.append("年龄匹配：正处于您期待的成长阶段")

            user_size = size_order.get(pref.get("preferred_size"))
            pet_size = size_order.get(pet.get("size_level"))
            if user_size and pet_size and abs(user_size - pet_size) <= 1:
                preference_score += 10.0
            
            if pref.get("preferred_temperament") and pref.get("preferred_temperament") in str(pet.get("temperament_tags", "")):
                preference_score += 10.0
                candidate.reasons.append(f"性格契合：宠物特质命中您的理想标签")

            # 2. 居住契合 (Condition)
            # 空间匹配
            if profile.get("has_yard") and pet.get("energy_level") == "高":
                condition_score += 20.0
                candidate.reasons.append("环境契合：高能量宠物适配院子环境")
            elif profile.get("housing_size", 0) > 80:
                condition_score += 10.0
            
            if profile.get("housing_type") == req.get("required_housing_type"):
                condition_score += 10.0
                candidate.reasons.append("住房匹配：满足该宠物对居住环境的要求")

            # 陪伴时间
            available_time = profile.get("available_time") or 0
            min_time = req.get("min_companion_hours") or 2.0
            if available_time >= min_time:
                condition_score += 10.0
            else:
                condition_score -= 20.0
                penalty += 10.0

            # 3. 经验适配 (Experience)
            exp_level = profile.get("experience_level", 0)
            if pet.get("care_level") == "容易" and exp_level == 0:
                experience_score += 30.0
                candidate.reasons.append("经验适配：该宠物非常适合新手起步")
            elif exp_level >= 1:
                experience_score += 20.0
                candidate.reasons.append("经验适配：您丰富的经验能应对此类宠物")
            
            if not req.get("allow_beginner") and exp_level == 0:
                experience_score -= 30.0
                penalty += 15.0

            # 4. 风险抵扣 (Penalty)
            if profile.get("allergy_info") and "低敏" not in str(pet.get("temperament_tags", "")):
                penalty += 20.0
                candidate.risk_flags.append("潜在过敏风险")
            
            if profile.get("has_children") and not pet.get("good_with_children"):
                penalty += 15.0
                candidate.risk_flags.append("儿童相处风险")

            if profile.get("has_other_pets") and not pet.get("good_with_other_pets"):
                penalty += 10.0
                candidate.risk_flags.append("多宠兼容风险")

            # 最终分数计算 (加权融合)
            candidate.final_score = (
                preference_score * 0.4 +
                condition_score * 0.3 +
                experience_score * 0.3 -
                penalty
            )
            candidate.final_score = round(max(0.0, min(100.0, candidate.final_score)), 2)

            # 导出结构化分数供前端展示
            candidate.scores = {
                "condition": round(max(0.0, min(100.0, condition_score)), 2),
                "preference": round(max(0.0, min(100.0, preference_score)), 2),
                "experience": round(max(0.0, min(100.0, experience_score)), 2),
                "penalty": round(penalty, 2)
            }

            candidate.stage_trace["multi_dimensional_scoring"] = {
                "stage": "多维精排评分",
                "dimensions": candidate.scores,
                "summary": "基于居住、偏好、经验和风险四维度综合建模"
            }

        return candidates
