class HardConstraintFilter:
    """
    硬性约束过滤器 - 增强演示版
    支持返回拦截详情，以便在演示界面展示“约束感知”的决策过程。
    """
    async def filter(self, query, candidates):
        res, _ = await self.filter_with_details(query, candidates)
        return res

    async def filter_with_details(self, query, candidates):
        result = []
        intercepted = []
        profile = query.user_profile
        
        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})
            
            # 1. 过敏约束
            if profile.get("allergy_info") and "低敏" not in str(pet.get("temperament_tags", "")):
                # 如果用户有过敏史且宠物不是低敏品种，在严格模式下应拦截，此处记录理由
                candidate.hard_filter_pass = 0
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": pet.get("name", "未知"),
                    "reason": "生理约束拦截：领养人有过敏史，候选宠物不属于低敏品种"
                })
                continue

            # 2. 家庭结构约束
            if profile.get("has_children") and req.get("forbid_children"):
                candidate.hard_filter_pass = 0
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": pet.get("name", "未知"),
                    "reason": "环境约束拦截：领养人家庭有儿童，送养方明确禁止有娃家庭申请"
                })
                continue

            # 3. 经济/预算约束
            budget_map = {"低": 1, "中": 2, "高": 3}
            user_budget = budget_map.get(profile.get("budget_level", "中"), 2)
            required_budget = budget_map.get(req.get("min_budget_level", "低"), 1)
            if user_budget < required_budget:
                candidate.hard_filter_pass = 0
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": pet.get("name", "未知"),
                    "reason": f"经济约束拦截：领养人预算水平({profile.get('budget_level')})低于该宠物最低照护要求({req.get('min_budget_level')})"
                })
                continue

            # 4. 时间/陪伴约束
            user_time = float(profile.get("available_time", 0))
            min_time = float(req.get("min_companion_hours", 0))
            if user_time < min_time and min_time > 4.0: # 仅对高陪伴要求的宠物执行硬拦截
                candidate.hard_filter_pass = 0
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": pet.get("name", "未知"),
                    "reason": f"陪伴约束拦截：领养人每日陪伴时长({user_time}h)无法满足该宠物的高社交需求({min_time}h)"
                })
                continue

            # 5. 经验门槛
            if not req.get("allow_beginner") and profile.get("experience_level", 0) == 0:
                candidate.hard_filter_pass = 0
                intercepted.append({
                    "id": candidate.candidate_id,
                    "name": pet.get("name", "未知"),
                    "reason": "准入约束拦截：该宠物照护难度大，送养方明确要求必须有养宠经验"
                })
                continue

            candidate.hard_filter_pass = 1
            result.append(candidate)

        return result, intercepted
