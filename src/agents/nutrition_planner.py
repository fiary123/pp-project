from typing import Dict, List


def _activity_factor(activity_level: str) -> float:
    return {
        'low': 1.15,
        'medium': 1.3,
        'high': 1.5
    }.get((activity_level or 'medium').lower(), 1.3)


def _goal_factor(goal: str) -> float:
    return {
        'maintain': 1.0,
        'lose_weight': 0.85,
        'gain_weight': 1.15
    }.get((goal or 'maintain').lower(), 1.0)


def _age_factor(species: str, age_months: int) -> float:
    is_cat = (species or '').lower() == 'cat'
    if age_months <= 6:
        return 2.2 if is_cat else 2.0
    if age_months <= 12:
        return 1.6 if is_cat else 1.5
    return 1.0


def build_nutrition_plan(
    species: str,
    age_months: int,
    weight_kg: float,
    neutered: bool,
    activity_level: str,
    goal: str,
    food_kcal_per_100g: float,
    symptoms: List[str] | None = None,
) -> Dict:
    species_norm = (species or 'cat').lower()
    rer = 70 * (weight_kg ** 0.75)

    der = rer * _activity_factor(activity_level) * _goal_factor(goal) * _age_factor(species_norm, age_months)
    if neutered and age_months >= 12:
        der *= 0.9

    daily_kcal = max(80, round(der))
    kcal_density = food_kcal_per_100g if food_kcal_per_100g > 0 else 360
    daily_food_g = round(daily_kcal / kcal_density * 100)

    if age_months <= 6:
        feedings = 4
    elif age_months <= 12:
        feedings = 3
    else:
        feedings = 2 if activity_level == 'low' else 3

    per_meal_base = daily_food_g // feedings
    per_meal = [per_meal_base] * feedings
    per_meal[-1] += daily_food_g - sum(per_meal)

    daily_water_min = round(weight_kg * 50)
    daily_water_max = round(weight_kg * 60)

    forbidden = ['巧克力', '洋葱', '葡萄', '木糖醇', '酒精', '高盐高油剩饭']
    if species_norm == 'cat':
        forbidden.extend(['狗粮长期替代', '生鱼生肉长期单一喂食'])
    if species_norm == 'dog':
        forbidden.extend(['熟骨头', '夏威夷果'])

    risk_alerts = ['若持续24小时拒食、反复呕吐或腹泻带血，请立即就医。']
    symptom_text = '、'.join(symptoms or [])
    if symptom_text:
        risk_alerts.append(f'已识别到特殊情况：{symptom_text}，建议先少量多餐并观察48小时。')

    return {
        'daily_kcal': daily_kcal,
        'daily_food_g': daily_food_g,
        'feedings_per_day': feedings,
        'per_meal_g': per_meal,
        'daily_water_ml': f'{daily_water_min}-{daily_water_max}',
        'forbidden_foods': forbidden,
        'transition_7days': [
            'D1-D2: 新粮25% + 旧粮75%',
            'D3-D4: 新粮50% + 旧粮50%',
            'D5-D6: 新粮75% + 旧粮25%',
            'D7: 新粮100%'
        ],
        'risk_alerts': risk_alerts,
    }


def render_nutrition_markdown(species: str, plan: Dict) -> str:
    return (
        f"### {species.upper()} 营养喂养方案\n"
        f"- 每日总热量：**{plan['daily_kcal']} kcal**\n"
        f"- 每日总喂食量：**{plan['daily_food_g']} g**\n"
        f"- 喂食频次：**{plan['feedings_per_day']} 次/天**\n"
        f"- 每餐建议：**{', '.join([str(x)+'g' for x in plan['per_meal_g']])}**\n"
        f"- 饮水建议：**{plan['daily_water_ml']} ml/天**\n\n"
        f"#### 禁忌清单\n"
        + '\n'.join([f"- {item}" for item in plan['forbidden_foods']])
        + "\n\n#### 7日换粮计划\n"
        + '\n'.join([f"- {item}" for item in plan['transition_7days']])
        + "\n\n#### 风险提示\n"
        + '\n'.join([f"- {item}" for item in plan['risk_alerts']])
    )
