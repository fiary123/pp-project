class HardConstraintFilter:
    """
    硬性约束过滤器 - 升级版 (约束感知架构)
    基于 rizhi.md 的标准化特征矩阵，实现生理、环境与行为的科学匹配。
    """
    async def filter(self, query, candidates):
        result = []
        profile = query.user_profile
        # pref = query.user_preferences

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})
            
            # --- 1. 生理安全约束 (过敏拦截) ---
            # 如果用户有提到过敏信息，而宠物非低敏 (此处简化逻辑: 除非标记为低敏，否则拦截)
            if profile.get("allergy_info") and "低敏" not in pet.get("temperament_tags", ""):
                candidate.reasons.append("硬约束拦截：用户/家庭成员有过敏史，候选宠物非低敏品种")
                candidate.hard_filter_pass = 0
                continue

            # --- 2. 人口结构与行为匹配 (婴幼儿/其他宠物拦截) ---
            # 如果家庭有小孩，而宠物不适合与小孩相处
            if profile.get("has_children") and not pet.get("good_with_children"):
                candidate.reasons.append("硬约束拦截：家庭包含儿童，该宠物历史行为显示对儿童不友好")
                candidate.hard_filter_pass = 0
                continue
            
            # 如果禁止有其他宠物，而用户家已有宠物
            if req.get("forbid_other_pets") and profile.get("has_other_pets"):
                candidate.reasons.append("硬约束拦截：该宠物需独占领养，不接受已有宠物的家庭")
                candidate.hard_filter_pass = 0
                continue

            # --- 3. 经济负担约束 ---
            # 预算等级匹配: 低 < 中 < 高
            budget_map = {"低": 1, "中": 2, "高": 3}
            user_budget = budget_map.get(profile.get("budget_level", "中"), 2)
            min_req_budget = budget_map.get(req.get("min_budget_level", "低"), 1)
            
            if user_budget < min_req_budget:
                candidate.reasons.append("硬约束拦截：用户预算水平低于该宠物预估的月均开销要求")
                candidate.hard_filter_pass = 0
                continue

            # --- 4. 空间与陪伴约束 ---
            # 陪伴时长拦截
            if profile.get("available_time", 0) < req.get("min_companion_hours", 0):
                candidate.reasons.append(f"硬约束拦截：每日陪伴时间不足 (要求 {req.get('min_companion_hours')}h)")
                candidate.hard_filter_pass = 0
                continue

            # --- 5. 既往经验硬约束 ---
            if not req.get("allow_beginner") and profile.get("experience_level", 0) == 0:
                candidate.reasons.append("硬约束拦截：该宠物照护难度大，不适合无经验的新手")
                candidate.hard_filter_pass = 0
                continue

            candidate.hard_filter_pass = 1
            result.append(candidate)

        return result
