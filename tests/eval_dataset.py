# 评估数据集：涵盖营养 (Nutrition) 和 分诊 (Triage) 场景

NUTRITION_TEST_CASES = [
    # --- 幼猫 ---
    {"species": "cat", "age_months": 2,   "weight_kg": 0.8,  "neutered": False, "goal": "maintain",     "activity_level": "medium", "food_kcal_per_100g": 380, "desc": "幼猫基础发育"},
    {"species": "cat", "age_months": 3,   "weight_kg": 1.0,  "neutered": False, "goal": "gain_weight",  "activity_level": "high",   "food_kcal_per_100g": 400, "desc": "幼猫增重期"},
    {"species": "cat", "age_months": 4,   "weight_kg": 1.5,  "neutered": False, "goal": "maintain",     "activity_level": "high",   "food_kcal_per_100g": 370, "desc": "幼猫活跃期"},
    {"species": "cat", "age_months": 5,   "weight_kg": 2.0,  "neutered": False, "goal": "maintain",     "activity_level": "medium", "food_kcal_per_100g": 360, "desc": "幼猫发育中期"},
    {"species": "cat", "age_months": 6,   "weight_kg": 2.5,  "neutered": False, "goal": "maintain",     "activity_level": "medium", "food_kcal_per_100g": 355, "desc": "幼猫发育后期"},
    # --- 成猫 ---
    {"species": "cat", "age_months": 24,  "weight_kg": 4.0,  "neutered": True,  "goal": "maintain",     "activity_level": "low",    "food_kcal_per_100g": 350, "desc": "成猫绝育低活动"},
    {"species": "cat", "age_months": 36,  "weight_kg": 5.0,  "neutered": True,  "goal": "maintain",     "activity_level": "medium", "food_kcal_per_100g": 360, "desc": "成猫毛球症风险", "symptoms": ["频繁干呕"]},
    {"species": "cat", "age_months": 48,  "weight_kg": 6.5,  "neutered": True,  "goal": "lose_weight",  "activity_level": "low",    "food_kcal_per_100g": 320, "desc": "成猫超重减重"},
    {"species": "cat", "age_months": 30,  "weight_kg": 3.5,  "neutered": False, "goal": "maintain",     "activity_level": "high",   "food_kcal_per_100g": 380, "desc": "活跃未绝育成猫"},
    {"species": "cat", "age_months": 60,  "weight_kg": 4.2,  "neutered": True,  "goal": "maintain",     "activity_level": "medium", "food_kcal_per_100g": 345, "desc": "中年猫健康维护"},
    # --- 老年猫 ---
    {"species": "cat", "age_months": 120, "weight_kg": 4.5,  "neutered": True,  "goal": "maintain",     "activity_level": "low",    "food_kcal_per_100g": 350, "desc": "老年猫关节护理", "symptoms": ["关节僵硬"]},
    {"species": "cat", "age_months": 144, "weight_kg": 3.8,  "neutered": True,  "goal": "gain_weight",  "activity_level": "low",    "food_kcal_per_100g": 390, "desc": "老年猫消瘦补营养"},
    {"species": "cat", "age_months": 108, "weight_kg": 5.2,  "neutered": True,  "goal": "lose_weight",  "activity_level": "low",    "food_kcal_per_100g": 310, "desc": "老年猫体重管理"},
    {"species": "cat", "age_months": 132, "weight_kg": 4.0,  "neutered": True,  "goal": "maintain",     "activity_level": "low",    "food_kcal_per_100g": 340, "desc": "老年猫肾脏护理", "symptoms": ["饮水增多"]},
    {"species": "cat", "age_months": 156, "weight_kg": 3.2,  "neutered": True,  "goal": "gain_weight",  "activity_level": "low",    "food_kcal_per_100g": 400, "desc": "高龄猫增重"},
    # --- 幼犬 ---
    {"species": "dog", "age_months": 3,   "weight_kg": 5.0,  "neutered": False, "goal": "gain_weight",  "activity_level": "high",   "food_kcal_per_100g": 420, "desc": "幼犬快速生长期"},
    {"species": "dog", "age_months": 6,   "weight_kg": 8.0,  "neutered": False, "goal": "gain_weight",  "activity_level": "high",   "food_kcal_per_100g": 400, "desc": "生长期幼犬增重"},
    {"species": "dog", "age_months": 4,   "weight_kg": 3.0,  "neutered": False, "goal": "maintain",     "activity_level": "high",   "food_kcal_per_100g": 410, "desc": "小型幼犬发育"},
    {"species": "dog", "age_months": 8,   "weight_kg": 12.0, "neutered": False, "goal": "maintain",     "activity_level": "high",   "food_kcal_per_100g": 395, "desc": "中型幼犬发育"},
    {"species": "dog", "age_months": 10,  "weight_kg": 18.0, "neutered": False, "goal": "gain_weight",  "activity_level": "high",   "food_kcal_per_100g": 385, "desc": "大型幼犬增重"},
    # --- 成犬 ---
    {"species": "dog", "age_months": 24,  "weight_kg": 15.0, "neutered": True,  "goal": "lose_weight",  "activity_level": "low",    "food_kcal_per_100g": 320, "desc": "成犬肥胖减重"},
    {"species": "dog", "age_months": 36,  "weight_kg": 10.0, "neutered": True,  "goal": "maintain",     "activity_level": "medium", "food_kcal_per_100g": 360, "desc": "中型绝育成犬"},
    {"species": "dog", "age_months": 48,  "weight_kg": 25.0, "neutered": False, "goal": "maintain",     "activity_level": "high",   "food_kcal_per_100g": 370, "desc": "大型活跃成犬"},
    {"species": "dog", "age_months": 30,  "weight_kg": 6.0,  "neutered": True,  "goal": "maintain",     "activity_level": "low",    "food_kcal_per_100g": 340, "desc": "小型绝育懒散犬"},
    {"species": "dog", "age_months": 60,  "weight_kg": 20.0, "neutered": True,  "goal": "lose_weight",  "activity_level": "medium", "food_kcal_per_100g": 310, "desc": "中年犬体重管理"},
    # --- 老年犬 ---
    {"species": "dog", "age_months": 96,  "weight_kg": 12.0, "neutered": True,  "goal": "maintain",     "activity_level": "low",    "food_kcal_per_100g": 330, "desc": "老年犬关节护理", "symptoms": ["行动迟缓"]},
    {"species": "dog", "age_months": 120, "weight_kg": 8.0,  "neutered": True,  "goal": "gain_weight",  "activity_level": "low",    "food_kcal_per_100g": 380, "desc": "老年犬营养补充"},
    {"species": "dog", "age_months": 108, "weight_kg": 30.0, "neutered": True,  "goal": "lose_weight",  "activity_level": "low",    "food_kcal_per_100g": 300, "desc": "大型老年犬减重"},
    {"species": "dog", "age_months": 132, "weight_kg": 5.0,  "neutered": True,  "goal": "maintain",     "activity_level": "low",    "food_kcal_per_100g": 350, "desc": "小型高龄犬维护"},
    {"species": "dog", "age_months": 144, "weight_kg": 15.0, "neutered": True,  "goal": "gain_weight",  "activity_level": "low",    "food_kcal_per_100g": 390, "desc": "中型高龄犬增重"},
]

TRIAGE_TEST_CASES = [
    # --- 紧急 ---
    {"symptom": "狗狗误食了巧克力，现在呼吸急促", "expected_risk": "emergency", "keywords": ["中毒", "立即就医"]},
    {"symptom": "猫咪突然倒地抽搐，不省人事", "expected_risk": "emergency", "keywords": ["癫痫", "紧急"]},
    {"symptom": "狗狗被车撞了，腿在流血", "expected_risk": "emergency", "keywords": ["外伤", "紧急就医"]},
    {"symptom": "猫咪误食了百合花，开始呕吐", "expected_risk": "emergency", "keywords": ["中毒", "肾衰竭"]},
    {"symptom": "狗狗突然站不起来，后腿瘫痪", "expected_risk": "emergency", "keywords": ["脊椎", "神经"]},
    {"symptom": "宠物猫剧烈喘气，嘴唇发紫", "expected_risk": "emergency", "keywords": ["缺氧", "心肺"]},
    {"symptom": "狗狗误食老鼠药，精神差", "expected_risk": "emergency", "keywords": ["中毒", "紧急"]},
    {"symptom": "猫咪腹部膨胀，呼吸困难", "expected_risk": "emergency", "keywords": ["腹水", "紧急"]},
    # --- 建议就医 ---
    {"symptom": "我家狗狗今天早上吐了三次，没精神", "expected_risk": "high", "keywords": ["呕吐", "精神萎靡"]},
    {"symptom": "猫咪连续三天不吃东西，越来越消瘦", "expected_risk": "high", "keywords": ["厌食", "消瘦"]},
    {"symptom": "狗狗腹泻带血已经两天", "expected_risk": "high", "keywords": ["血便", "感染"]},
    {"symptom": "猫咪尿频，每次只有几滴", "expected_risk": "high", "keywords": ["泌尿", "堵塞"]},
    {"symptom": "狗狗眼睛红肿，分泌物很多", "expected_risk": "high", "keywords": ["结膜炎", "感染"]},
    {"symptom": "猫咪最近咳嗽很厉害，还发出喘鸣声", "expected_risk": "high", "keywords": ["呼吸道", "感染"]},
    {"symptom": "狗狗发烧39.5度，精神萎靡", "expected_risk": "high", "keywords": ["发热", "感染"]},
    {"symptom": "猫咪头部歪斜，走路打圈", "expected_risk": "high", "keywords": ["前庭", "神经"]},
    {"symptom": "狗狗腿部出现肿块，逐渐变大", "expected_risk": "high", "keywords": ["肿瘤", "活检"]},
    {"symptom": "猫咪皮肤大片脱毛，有红疹", "expected_risk": "high", "keywords": ["真菌", "皮肤病"]},
    # --- 观察处理 ---
    {"symptom": "猫咪耳朵有点红，一直在抓", "expected_risk": "medium", "keywords": ["耳螨", "过敏"]},
    {"symptom": "宠物猫眼睛有分泌物", "expected_risk": "medium", "keywords": ["结膜炎", "清洁"]},
    {"symptom": "狗狗最近放屁很多，肚子咕噜叫", "expected_risk": "medium", "keywords": ["消化", "肠道"]},
    {"symptom": "猫咪喝水量明显增加", "expected_risk": "medium", "keywords": ["肾病", "糖尿病"]},
    {"symptom": "狗狗爪子一直舔，有点红肿", "expected_risk": "medium", "keywords": ["过敏", "皮炎"]},
    {"symptom": "猫咪牙龈有点红，口臭", "expected_risk": "medium", "keywords": ["牙周", "口腔"]},
    {"symptom": "狗狗最近睡眠增多，不爱玩耍", "expected_risk": "medium", "keywords": ["甲减", "贫血"]},
    {"symptom": "猫咪尾巴基部有脱毛，偶尔抓挠", "expected_risk": "medium", "keywords": ["跳蚤", "寄生虫"]},
    # --- 日常关注 ---
    {"symptom": "猫咪最近食欲很好，就是有点掉毛", "expected_risk": "low", "keywords": ["季节性掉毛", "营养"]},
    {"symptom": "狗狗偶尔打喷嚏，没有其他症状", "expected_risk": "low", "keywords": ["灰尘", "过敏原"]},
    {"symptom": "猫咪最近比较安静，没有往常活泼", "expected_risk": "low", "keywords": ["情绪", "环境"]},
    {"symptom": "狗狗指甲有点长，走路声音大", "expected_risk": "low", "keywords": ["修甲", "护理"]},
]

def get_expanded_dataset():
    """返回完整评估数据集（营养30条 + 分诊30条）"""
    return NUTRITION_TEST_CASES, TRIAGE_TEST_CASES
