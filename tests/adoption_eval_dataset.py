# 领养评估系统专用实验数据集 (Adoption Evaluation Gold Dataset)
# 对应论文第六章：实验设计与结果分析

EVAL_SAMPLES = [
    # --- Category A: 理想领养人 (Ideal Applicants) ---
    {
        "id": "A1",
        "data": {
            "age": 30, "monthly_budget": 2000, "housing_type": "别墅", "has_yard": True,
            "has_pet_experience": True, "daily_companion_hours": 6, "family_support": True,
            "application_reason": "资深猫奴，家里有充足空间和草坪，工作弹性大能长期陪伴。"
        },
        "ground_truth": {
            "decision": "approved",
            "min_score": 90,
            "key_factors": ["High_Budget", "Experienced", "Yard_Available"]
        }
    },
    # --- Category B: 高风险拦截 (High Risk - Should be rejected by Rules) ---
    {
        "id": "B1",
        "data": {
            "age": 16, "monthly_budget": 100, "housing_type": "公寓", "has_yard": False,
            "has_pet_experience": False, "daily_companion_hours": 1, "family_support": False,
            "application_reason": "学生，想养一只猫陪我写作业，但是爸妈不太同意。"
        },
        "ground_truth": {
            "decision": "rejected",
            "拦截层": "Rule_Engine",
            "key_factors": ["Underage", "Low_Budget", "No_Family_Support"]
        }
    },
    # --- Category C: 模糊地带 (Ambiguous - Needs Multi-Agent Consensus) ---
    {
        "id": "C1",
        "data": {
            "age": 25, "monthly_budget": 600, "housing_type": "公寓", "has_yard": False,
            "has_pet_experience": False, "daily_companion_hours": 4, "family_support": True,
            "application_reason": "刚工作的职场新人，租房住，虽然没养过但非常有爱心，愿意学习。"
        },
        "ground_truth": {
            "decision": "probing", # 理论上应该触发追问或建议通过
            "min_score": 60,
            "key_factors": ["Novice", "Renting_Risk", "High_Commitment"]
        }
    },
    # --- Category D: 记忆增强典型案例 (Memory Match) ---
    {
        "id": "D1",
        "data": {
            "age": 40, "monthly_budget": 1500, "housing_type": "公寓", "has_yard": False,
            "has_pet_experience": True, "daily_companion_hours": 3, "family_support": True,
            "application_reason": "之前领养过一只流浪狗，后来它老死了，现在想再给一个生命一个家。"
        },
        "ground_truth": {
            "decision": "approved",
            "memory_hit": True, # 应该匹配到历史成功案例
            "key_factors": ["Previous_Success", "Stable_Life"]
        }
    }
    # (此处省略其余 16 条，保持逻辑结构清晰)
]
