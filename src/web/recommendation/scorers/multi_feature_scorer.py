class MultiFeatureScorer:
    """
    多维精排评分器 - 科学加权版
    基于 rizhi.md 统计学洞察：健康披露、行为习惯、社交兼容性。
    """
    async def score(self, query, candidates):
        profile = query.user_profile
        pref = query.user_preferences

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            # req = candidate.features.get("requirement", {})

            # 基础分
            base_score = 50.0
            
            # --- 1. 统计学显著性补偿 ---
            statistical_bonus = 0.0
            # 健康披露补偿 (如果标记为健康或已绝育)
            if pet.get("health_status") == "健康":
                statistical_bonus += 10.0
            if pet.get("sterilized"):
                statistical_bonus += 10.0
                candidate.reasons.append("健康披露详尽 (已完成绝育)")
            
            # 性格与社交补偿
            if pet.get("social_level") == "极其亲人":
                statistical_bonus += 10.0
            if pet.get("good_with_children") and profile.get("has_children"):
                statistical_bonus += 10.0
                candidate.reasons.append("社交兼容性高 (对儿童友好)")

            # --- 2. 行为与性格匹配 ---
            behavior_score = 0.0
            # 陪伴需求匹配
            time_map = {"低": 1.0, "中": 3.0, "高": 6.0}
            pet_need_time = time_map.get(pet.get("companionship_need", "中"), 3.0)
            user_avail_time = profile.get("available_time", 3.0)
            
            if user_avail_time >= pet_need_time:
                behavior_score += 15.0
                candidate.reasons.append("陪伴时间高度匹配")
            else:
                behavior_score -= 10.0

            # 偏好性格匹配 (简单包含逻辑)
            if pref.get("preferred_temperament") and pref.get("preferred_temperament") in pet.get("temperament_tags", ""):
                behavior_score += 15.0
                candidate.reasons.append(f"性格契合 ({pref.get('preferred_temperament')})")

            # --- 3. 环境与活跃度匹配 ---
            environment_score = 0.0
            # 空间匹配
            if profile.get("has_yard") and pet.get("energy_level") == "高":
                environment_score += 15.0
                candidate.reasons.append("运动空间契合 (有院子)")
            
            # 面积补偿
            if profile.get("housing_size", 0) > 80:
                environment_score += 5.0

            # --- 4. 经验适配 ---
            experience_score = 0.0
            if profile.get("experience_level", 0) >= 1: # 有经验或专家
                experience_score += 10.0
            
            # 难度对齐
            if pet.get("care_difficulty") == "容易" and profile.get("experience_level", 0) == 0:
                experience_score += 10.0
                candidate.reasons.append("难度适配 (新手友好)")

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
