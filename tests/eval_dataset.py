# 评估数据集：涵盖营养 (Nutrition) 和 分诊 (Triage) 场景

NUTRITION_TEST_CASES = [
    {
        "species": "cat", "age_months": 2, "weight_kg": 0.8, "neutered": False, 
        "goal": "maintain", "activity_level": "medium", "food_kcal_per_100g": 380,
        "desc": "幼猫基础发育"
    },
    {
        "species": "dog", "age_months": 24, "weight_kg": 15.0, "neutered": True, 
        "goal": "lose_weight", "activity_level": "low", "food_kcal_per_100g": 320,
        "desc": "成犬肥胖减重"
    },
    {
        "species": "cat", "age_months": 120, "weight_kg": 4.5, "neutered": True, 
        "goal": "maintain", "activity_level": "low", "food_kcal_per_100g": 350,
        "symptoms": ["关节僵硬"], "desc": "老年猫关节护理"
    },
    {
        "species": "dog", "age_months": 6, "weight_kg": 8.0, "neutered": False, 
        "goal": "gain_weight", "activity_level": "high", "food_kcal_per_100g": 400,
        "desc": "生长期幼犬增重"
    },
    {
        "species": "cat", "age_months": 36, "weight_kg": 5.0, "neutered": True, 
        "goal": "maintain", "activity_level": "medium", "food_kcal_per_100g": 360,
        "symptoms": ["频繁干呕"], "desc": "成猫毛球症风险"
    }
]

TRIAGE_TEST_CASES = [
    {"symptom": "我家狗狗今天早上吐了三次，没精神", "expected_risk": "high", "keywords": ["呕吐", "精神萎靡"]},
    {"symptom": "猫咪耳朵有点红，一直在抓", "expected_risk": "medium", "keywords": ["耳螨", "过敏"]},
    {"symptom": "猫咪最近食欲很好，就是有点掉毛", "expected_risk": "low", "keywords": ["季节性掉毛", "营养"]},
    {"symptom": "狗狗误食了巧克力，现在呼吸急促", "expected_risk": "emergency", "keywords": ["中毒", "立即就医"]},
    {"symptom": "宠物猫眼睛有分泌物", "expected_risk": "medium", "keywords": ["结膜炎", "清洁"]},
]

def get_expanded_dataset():
    """生成 100 条测试数据用于大规模评估"""
    # 增加一些变体以使数据更多样
    expanded_nutrition = NUTRITION_TEST_CASES * 10 
    expanded_triage = TRIAGE_TEST_CASES * 10       
    return expanded_nutrition, expanded_triage
