class MultiFeatureScorer:
    """
    多维评分器 - 根据用户画像和宠物特征计算匹配得分
    """
    async def score(self, query, candidates):
        profile = query.user_profile
        pref = query.user_preferences

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            condition_score = 0.0
            preference_score = 0.0
            experience_score = 0.0
            stability_score = 0.0
            risk_penalty = 0.0

            # 1. 领养条件匹配 (35%)
            # 经验适配
            if req.get("require_experience") == profile.get("pet_experience"):
                condition_score += 20
            # 住房匹配 (自有住房或家庭支持)
            if not req.get("require_stable_housing") or profile.get("rental_status") == "自购" or profile.get("family_support"):
                condition_score += 15

            # 2. 用户偏好匹配 (25%)
            # 种类匹配
            if pref.get("preferred_pet_type") == pet.get("species"):
                preference_score += 20
                candidate.reasons.append("宠物类型与您的偏好一致")
            
            # 3. 经验与难度适配 (20%)
            if profile.get("pet_experience") and profile["pet_experience"] != "无":
                experience_score += 20
                candidate.reasons.append("您具备丰富的养宠经验")
            elif pet.get("beginner_friendly"):
                experience_score += 10
                candidate.reasons.append("该宠物非常适合新手饲养")

            # 4. 环境与稳定性 (20%)
            if profile.get("family_support"):
                stability_score += 10
                candidate.reasons.append("家庭环境支持养宠")
            if profile.get("available_time", 0) >= 2.0:
                stability_score += 10
                candidate.reasons.append("您有充足的陪伴时间")

            # 5. 风险扣分
            if pet.get("special_care_flag") and not profile.get("pet_experience"):
                risk_penalty += 15
                candidate.risk_flags.append("特殊护理需求与用户经验不匹配")

            candidate.scores = {
                "condition_score": condition_score,
                "preference_score": preference_score,
                "experience_score": experience_score,
                "stability_score": stability_score,
                "risk_penalty": risk_penalty,
            }

            # 最终权重得分
            candidate.final_score = (
                0.35 * condition_score +
                0.25 * preference_score +
                0.20 * experience_score +
                0.20 * stability_score -
                risk_penalty
            )
            
            # 基础分偏移，确保分段感
            candidate.final_score = max(0.0, candidate.final_score * 5) # 放大到 100 分量级

        return candidates
