class ApplicantMatchScorer:
    """
    申请人评分器 - 衡量申请人与特定宠物及送养要求的匹配程度
    """
    async def score(self, query, candidates):
        for candidate in candidates:
            profile = candidate.features.get("applicant_profile", {})
            pref = candidate.features.get("applicant_preference", {})
            app = candidate.features.get("application", {})
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            condition_score = 0.0
            care_score = 0.0
            preference_score = 0.0
            stability_score = 0.0
            risk_penalty = 0.0

            # 1. 条件匹配分 (35%)
            if req.get("require_experience") == profile.get("pet_experience"):
                condition_score += 20
            if req.get("require_return_visit") == app.get("accept_return_visit"):
                condition_score += 15

            # 2. 照护能力分 (30%)
            if profile.get("available_time", 0) >= 2.0:
                care_score += 15
                candidate.reasons.append("申请人具备较稳定照护时间")
            if profile.get("pet_experience") and profile["pet_experience"] != "无":
                care_score += 20
                candidate.reasons.append("申请人具备养宠经验")
            elif pet.get("beginner_friendly"):
                care_score += 10
                candidate.reasons.append("宠物适合新手照护")

            # 3. 偏好一致性 (15%)
            if pref.get("preferred_pet_type") == pet.get("species"):
                preference_score += 15
                candidate.reasons.append("申请人偏好与宠物类型一致")

            # 4. 稳定性参考 (20%)
            if profile.get("family_support"):
                stability_score += 10
                candidate.reasons.append("申请人家庭支持养宠")
            if profile.get("rental_status") == "自购":
                stability_score += 10
                candidate.reasons.append("申请人居住条件相对稳定")

            # 5. 风险扣分
            if pet.get("energy_level") == "高" and profile.get("available_time", 0) < 1.0:
                risk_penalty += 10
                candidate.risk_flags.append("高活动量宠物与申请人时间投入不匹配")

            if pet.get("special_care_flag") and not profile.get("pet_experience"):
                risk_penalty += 15
                candidate.risk_flags.append("特殊护理需求与申请人经验不匹配")

            candidate.scores = {
                "condition_score": condition_score,
                "care_score": care_score,
                "preference_score": preference_score,
                "stability_score": stability_score,
                "risk_penalty": risk_penalty,
            }

            candidate.final_score = (
                0.35 * condition_score +
                0.30 * care_score +
                0.15 * preference_score +
                0.20 * stability_score -
                risk_penalty
            )
            
            # 基础分偏移，确保分段感
            candidate.final_score = max(0.0, candidate.final_score * 5)

        return candidates
