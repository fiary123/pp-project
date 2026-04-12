class HardConstraintFilter:
    """
    硬性约束过滤器 - 升级版 (约束感知架构)
    基于 rizhi.md 的标准化特征矩阵，实现生理、环境与行为的科学匹配。
    """
    async def filter(self, query, candidates):
        result = []
        profile = query.user_profile
        pref = query.user_preferences

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})
            
            # --- 1. 生理安全约束 (过敏拦截) ---
            # 如果家庭成员有过敏史，而宠物掉毛严重
            if profile.get("allergy_history") and pet.get("shedding_level") == "严重":
                candidate.reasons.append("硬约束拦截：家庭成员过敏，不建议领养严重掉毛宠物")
                continue

            # --- 2. 人口结构与行为匹配 (婴幼儿拦截) ---
            # 如果家庭包含婴幼儿，而宠物有护食倾向或分离焦虑攻击风险
            if profile.get("family_structure") == "包含婴幼儿" and (pet.get("guarding_tendency") or pet.get("separation_anxiety")):
                candidate.reasons.append("硬约束拦截：宠物存在护食或焦虑倾向，不建议与婴幼儿共处")
                continue

            # --- 3. 经济负担约束 ---
            # 如果宠物需要特殊护理（医疗/处方粮），而用户预算水平为“低”
            if pet.get("special_care_flag") and profile.get("budget_level") == "低":
                candidate.reasons.append("硬约束拦截：该宠物需长期医疗干预，超出当前预算范围")
                continue

            # --- 4. 空间与运动量约束 ---
            # 独立庭院需求
            if pet.get("energy_level") == "高" and req.get("require_yard") and profile.get("housing_type") == "apartment":
                candidate.reasons.append("硬约束拦截：该宠物需要独立庭院，不适合公寓饲养")
                continue

            # --- 5. 既往经验硬约束 ---
            req_exp = req.get("require_experience", "无")
            user_exp = profile.get("pet_experience", "无")
            if req_exp == "3年以上" and user_exp == "无":
                candidate.reasons.append("硬约束拦截：该宠物照护难度极高，不适合新手")
                continue

            result.append(candidate)

        return result
