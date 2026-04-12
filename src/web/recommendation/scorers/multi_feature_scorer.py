class MultiFeatureScorer:
    """
    多维精排评分器 - 科学加权版
    基于 rizhi.md 统计学洞察：疫苗披露(+54%), 排泄训练(+59%), 兼容性(+56%)。
    """
    async def score(self, query, candidates):
        profile = query.user_profile
        pref = query.user_preferences

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})

            # 基础分
            base_score = 50.0
            
            # --- 1. 统计学显著性补偿 (核心优化) ---
            statistical_bonus = 0.0
            # 疫苗接种补偿 (+54% 概率)
            if pet.get("vaccine_coverage"):
                statistical_bonus += 15.0
                candidate.reasons.append("健康披露详尽 (疫苗全覆盖)")
            
            # 排泄训练补偿 (+59% 概率 - 针对犬类显著)
            if pet.get("housetrained"):
                statistical_bonus += 18.0
                candidate.reasons.append("行为习惯极佳 (已接受排泄训练)")
            
            # 兼容性补偿 (+56% 概率)
            if pet.get("child_friendly") or pet.get("other_pet_friendly"):
                statistical_bonus += 16.0
                candidate.reasons.append("社交兼容性高 (对儿童/宠物友好)")

            # --- 2. 行为与性格匹配 ---
            behavior_score = 0.0
            # 分离焦虑与可用时间匹配
            if pet.get("separation_anxiety") and profile.get("available_time", 0) < 4.0:
                behavior_score -= 20.0 # 惩罚项
            elif not pet.get("separation_anxiety") and profile.get("available_time", 0) >= 2.0:
                behavior_score += 10.0

            # --- 3. 环境与活跃度匹配 ---
            environment_score = 0.0
            # 用户活跃度 vs 宠物能量
            if profile.get("activity_level") == "户外型" and pet.get("energy_level") == "高":
                environment_score += 15.0
                candidate.reasons.append("运动需求契合")
            
            # 居住面积加分
            if profile.get("housing_size", 0) > 60:
                environment_score += 10.0

            # --- 4. 经验适配 ---
            experience_score = 0.0
            if profile.get("pet_experience") != "无":
                experience_score += 10.0
            if pet.get("beginner_friendly"):
                experience_score += 10.0

            # 最终权重计算
            candidate.final_score = (
                base_score + 
                statistical_bonus + 
                behavior_score + 
                environment_score + 
                experience_score
            )
            
            # 映射到 0-100
            candidate.final_score = max(0.0, min(100.0, candidate.final_score))
            
            candidate.scores = {
                "statistical": statistical_bonus,
                "behavior": behavior_score,
                "environment": environment_score,
                "experience": experience_score
            }

        return candidates
