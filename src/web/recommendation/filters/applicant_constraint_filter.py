class ApplicantConstraintFilter:
    """
    申请人约束过滤器 - 在进入评分前，过滤掉不满足送养人硬性条件的申请人
    """
    async def filter(self, query, candidates):
        result = []

        for candidate in candidates:
            profile = candidate.features.get("applicant_profile", {})
            app = candidate.features.get("application", {})
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            # 1. 经验要求 (需要经验但申请人无经验)
            if req.get("require_experience") and req["require_experience"] != "无" and not profile.get("pet_experience"):
                candidate.reasons.append("申请人不满足养宠经验硬性要求")
                continue

            # 2. 稳定住房要求 (要求稳定住房但申请人是租房且无家庭支持)
            if req.get("require_stable_housing") and profile.get("rental_status") == "租房" and not profile.get("family_support"):
                candidate.reasons.append("申请人当前居住环境稳定性不达标")
                continue

            # 3. 回访要求 (送养人要求回访但申请人不接受)
            if req.get("require_return_visit") and not app.get("accept_return_visit"):
                candidate.reasons.append("申请人不接受必要的领养后回访")
                continue

            # 4. 特殊护理风险提示 (不直接过滤，但打上风险标签)
            if pet.get("special_care_flag") and not profile.get("pet_experience"):
                candidate.risk_flags.append("特殊护理宠物与申请人经验存在风险")

            result.append(candidate)

        return result
