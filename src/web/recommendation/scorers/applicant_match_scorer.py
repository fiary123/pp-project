class ApplicantMatchScorer:
    """
    申请审核精排评分器 - 结构化匹配版
    对齐维度键值：condition, preference, experience, penalty
    """

    async def score(self, query, candidates):
        budget_map = {"低": 1, "中": 2, "高": 3}

        for candidate in candidates:
            profile = candidate.features.get("applicant_profile", {})
            pref = candidate.features.get("applicant_preference", {})
            # app = candidate.features.get("application", {})
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            # 初始化四个统一维度分
            preference_score = 50.0
            experience_score = 50.0
            condition_score = 50.0
            penalty = 0.0

            # 1. 偏好对齐 (Preference)
            if pref.get("preferred_pet_type") == pet.get("species"):
                preference_score += 20.0
                candidate.reasons.append("匹配点：品种高度符合申请人预期")
            
            if pref.get("preferred_temperament") and pref.get("preferred_temperament") in str(pet.get("temperament_tags", "")):
                preference_score += 15.0
                candidate.reasons.append("匹配点：宠物性格命中申请人理想标签")

            # 2. 经验适配 (Experience)
            exp_level = profile.get("experience_level", 0)
            req_exp = req.get("require_experience", "无")
            if req_exp != "无" and exp_level >= 1:
                experience_score += 25.0
                candidate.reasons.append("匹配点：申请人经验满足该宠物特定要求")
            elif exp_level >= 1:
                experience_score += 15.0
                candidate.reasons.append("匹配点：申请人具备基础照护经验")
            
            if not req.get("allow_beginner") and exp_level == 0:
                experience_score -= 30.0
                penalty += 15.0

            # 3. 居住契合 (Condition)
            if profile.get("rental_status") == "自购":
                condition_score += 20.0
                candidate.reasons.append("稳定点：申请人拥有自有住房，安置更稳健")
            
            if profile.get("has_yard") and pet.get("energy_level") == "高":
                condition_score += 15.0
                candidate.reasons.append("稳定点：环境适配高能量宠物的活动需求")

            applicant_budget = budget_map.get(profile.get("budget_level") or "中", 2)
            required_budget = budget_map.get(req.get("min_budget_level") or "低", 1)
            if applicant_budget >= required_budget:
                condition_score += 10.0
            else:
                penalty += 10.0
                candidate.risk_flags.append("经济支持能力存疑")

            # 4. 风险抵扣 (Penalty)
            if profile.get("has_children") and not pet.get("good_with_children"):
                penalty += 20.0
                candidate.risk_flags.append("儿童相处潜在风险")
            
            if profile.get("has_other_pets") and not pet.get("good_with_other_pets"):
                penalty += 15.0
                candidate.risk_flags.append("多宠环境兼容性风险")

            # 最终权重计算
            candidate.final_score = (
                preference_score * 0.3 +
                experience_score * 0.3 +
                condition_score * 0.4 -
                penalty
            )
            candidate.final_score = round(max(0.0, min(100.0, candidate.final_score)), 2)

            # 结构化分数供前端展示
            candidate.scores = {
                "condition": round(max(0.0, min(100.0, condition_score)), 2),
                "preference": round(max(0.0, min(100.0, preference_score)), 2),
                "experience": round(max(0.0, min(100.0, experience_score)), 2),
                "penalty": round(penalty, 2)
            }

            candidate.stage_trace["multi_dimensional_scoring"] = {
                "stage": "审核精排评分",
                "dimensions": candidate.scores,
                "summary": "基于申请人画像与宠物约束的精准匹配计算"
            }

        return candidates
