class HardConstraintFilter:
    """
    硬性约束过滤器 - 过滤掉不满足发布者领养条件或用户偏好的候选对象
    """
    async def filter(self, query, candidates):
        result = []
        profile = query.user_profile
        pref = query.user_preferences

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            # 1. 经验要求 (需要经验且用户无经验，直接过滤)
            if req.get("require_experience") and req["require_experience"] != "无" and not profile.get("pet_experience"):
                candidate.reasons.append("不满足养宠经验要求")
                continue

            # 2. 特殊护理 (宠物需要特殊照护，但用户在偏好中明确表示不接受)
            if pet.get("special_care_flag") and not pref.get("accept_special_care"):
                candidate.reasons.append("用户不接受特殊照护宠物")
                continue

            # 3. 活力度与时间投入 (高活力宠物需要较多时间，如果用户可用时间极低则过滤)
            # 假设 available_time < 1 小时被视为 low
            if pet.get("energy_level") == "高" and profile.get("available_time", 0) < 1.0:
                candidate.reasons.append("用户可用时间不足以照护高活力宠物")
                continue

            result.append(candidate)

        return result
