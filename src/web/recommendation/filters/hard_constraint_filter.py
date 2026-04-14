class HardConstraintFilter:
    """
    约束过滤器
    在多维评分前先过滤明显不满足领养要求的对象。
    """
    async def filter(self, query, candidates):
        result = []
        profile = query.user_profile

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})
            passed_constraints = []
            failed_constraints = []
            
            if profile.get("allergy_info") and "低敏" not in pet.get("temperament_tags", ""):
                failed_constraints.append("过敏家庭需低敏宠物")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：用户/家庭成员存在过敏史，候选宠物不属于低敏对象")
                continue

            if profile.get("has_children") and not pet.get("good_with_children"):
                failed_constraints.append("家庭有儿童需儿童友好宠物")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：家庭包含儿童，该宠物不适合儿童环境")
                continue

            if req.get("forbid_other_pets") and profile.get("has_other_pets"):
                failed_constraints.append("该宠物不接受多宠家庭")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：该宠物需单宠家庭")
                continue
            if req.get("forbid_children") and profile.get("has_children"):
                failed_constraints.append("该宠物不适合有儿童家庭")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：送养要求不接受有儿童家庭")
                continue

            budget_map = {"低": 1, "中": 2, "高": 3}
            user_budget = budget_map.get(profile.get("budget_level", "中"), 2)
            min_req_budget = budget_map.get(req.get("min_budget_level", "低"), 1)
            if user_budget < min_req_budget:
                failed_constraints.append("预算需达到宠物最低照护要求")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：预算水平低于该宠物的基本照护要求")
                continue

            if profile.get("available_time", 0) < req.get("min_companion_hours", 0):
                failed_constraints.append("陪伴时间需达到最低要求")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append(f"约束过滤未通过：每日陪伴时间不足（要求 {req.get('min_companion_hours')} 小时）")
                continue
            passed_constraints.append("满足预算与陪伴时长要求")

            required_housing_type = req.get("required_housing_type")
            housing_matches = True
            if required_housing_type and profile.get("housing_type") and profile.get("housing_type") != required_housing_type:
                housing_matches = False
                candidate.risk_flags.append("住房条件与送养要求存在差异，建议进入人工核验")
            if required_housing_type and housing_matches:
                passed_constraints.append("住房条件满足送养要求")

            if not req.get("allow_beginner") and profile.get("experience_level", 0) == 0:
                failed_constraints.append("该宠物不接受新手领养")
                candidate.hard_filter_pass = 0
                candidate.stage_trace["constraint_filter"] = {"stage": "约束过滤", "passed": False, "failed_constraints": failed_constraints}
                candidate.reasons.append("约束过滤未通过：该宠物照护难度较高，不适合无经验申请人")
                continue
            if req.get("allow_beginner"):
                passed_constraints.append("新手准入条件允许")

            candidate.hard_filter_pass = 1
            candidate.stage_trace["constraint_filter"] = {
                "stage": "约束过滤",
                "passed": True,
                "matched_constraints": passed_constraints,
                "failed_constraints": failed_constraints,
            }
            result.append(candidate)

        return result
