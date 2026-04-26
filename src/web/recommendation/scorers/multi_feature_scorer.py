import random

class MultiFeatureScorer:
    """
    多维精排评分器 - 结构化匹配与可解释性增强版
    对齐前端维度：condition (居住契合), preference (偏好对齐), experience (经验适配), penalty (风险抵扣)
    """

    async def score(self, query, candidates):
        profile = query.user_profile
        pref = query.user_preferences
        
        # 信用等级加成 (基于 Thesis: 信用分作为隐性权重)
        credit_bonus = {
            "Black": 5.0, "Gold": 3.0, "Silver": 1.0, "Bronze": -5.0
        }.get(profile.get("credit_level", "Bronze"), 0.0)

        size_order = {"小型": 1, "中型": 2, "大型": 3}

        for candidate in candidates:
            pet = candidate.features.get("pet", {})
            req = candidate.features.get("requirement", {})
            candidate.reasons = [] # 清空并重新生成
            
            # 初始化基础分 (引入微量随机偏移，模拟真实世界中细微的非结构化差异)
            base_bias = random.uniform(-2.0, 2.0)
            preference_score = 50.0 + base_bias
            condition_score = 50.0 + base_bias
            experience_score = 50.0 + base_bias
            penalty = 0.0

            # 1. 偏好对齐 (Preference) - 权重 40%
            if pref.get("preferred_pet_type") == pet.get("species"):
                preference_score += 25.0
                candidate.reasons.append(f"品种契合：您偏爱的{pet.get('species')}")
            
            # 性格匹配
            p_tags = str(pet.get("temperament_tags", ""))
            if pref.get("preferred_temperament") and pref.get("preferred_temperament") in p_tags:
                preference_score += 15.0
                candidate.reasons.append("性格契合：命中您的理想性格")
            elif "粘人" in p_tags: # 默认好评性格
                preference_score += 5.0

            # 2. 居住契合 (Condition) - 权重 30%
            # 陪伴时间 (核心红线)
            available_time = profile.get("available_time") or 0
            min_time = req.get("min_companion_hours") or 1.0
            if available_time >= min_time:
                condition_score += 15.0
                candidate.reasons.append("陪伴充足：您的时间能给予它极好的照顾")
            else:
                condition_score -= 30.0
                penalty += 10.0
                candidate.reasons.append("时间紧迫：它的陪伴需求可能挑战您的日程")

            # 空间匹配
            if profile.get("has_yard") and pet.get("energy_level") == "高":
                condition_score += 15.0
                candidate.reasons.append("空间优越：您有院子，适合它奔跑")

            # 3. 经验适配 (Experience) - 权重 30%
            exp_level = profile.get("experience_level", 0)
            if pet.get("care_level") == "容易" and exp_level == 0:
                experience_score += 20.0
                candidate.reasons.append("新手友好：它是您的入坑首选")
            elif exp_level >= 1:
                experience_score += 15.0
                candidate.reasons.append("经验适配：您的丰富阅历让领养更放心")

            # 4. 风险抵扣 (Penalty)
            if profile.get("has_children") and not pet.get("good_with_children"):
                penalty += 15.0
                candidate.reasons.append("环境风险：该宠物对儿童不够友好")

            # 最终分数计算 (加权融合 + 信用加成)
            candidate.final_score = (
                preference_score * 0.4 +
                condition_score * 0.3 +
                experience_score * 0.3 -
                penalty + credit_bonus
            )
            candidate.final_score = round(max(0.0, min(100.0, candidate.final_score)), 2)

            # 生成核心 Insight (用于前端展示)
            if candidate.final_score > 85:
                candidate.insight = "灵魂伴侣级匹配，各项指标完美契合。"
            elif candidate.final_score > 70:
                candidate.insight = candidate.reasons[0] if candidate.reasons else "具备良好领养基础。"
            else:
                candidate.insight = "具有一定挑战，需更严谨评估环境。"

            candidate.scores = {
                "condition": round(condition_score, 1),
                "preference": round(preference_score, 1),
                "experience": round(experience_score, 1),
                "penalty": round(penalty, 1)
            }

        return candidates
