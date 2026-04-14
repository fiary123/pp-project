import logging

logger = logging.getLogger(__name__)

class UserQueryHydrator:
    """
    请求补全器 - 获取用户的画像和偏好，填充到 Query 对象中。
    支持冷启动：若数据库画像缺失，则调用 AI Agent 从用户查询文本中动态提取特征。
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service

    async def hydrate(self, query):
        # 1. 尝试从数据库获取持久化画像
        profile = self.profile_service.get_user_profile(query.user_id)
        preference = self.profile_service.get_user_preferences(query.user_id)

        # 2. 冷启动逻辑：如果画像核心字段缺失且有 user_query，则调用 Agent 动态分析
        dynamic_traits = {}
        if (not profile or not profile.get("housing_type")) and query.user_query:
            try:
                from src.agents.agents import analyze_pet_interview
                logger.info(f"触发冷启动特征提取，用户 ID: {query.user_id}")
                # 调用 agents.py 中的分析函数
                analysis = await analyze_pet_interview(
                    user_msg=query.user_query,
                    pet_name="未知",
                    pet_species="所有",
                    pet_desc="推荐请求"
                )
                dynamic_traits = analysis
                logger.info(f"动态特征提取成功: {dynamic_traits.get('user_traits')}")
            except Exception as e:
                logger.error(f"动态特征提取失败: {str(e)}")

        # 3. 组装结构化 Profile (数据库优先，Agent 补充)
        if not profile:
            profile = {}
            
        inferred_experience = profile.get("experience_level")
        if inferred_experience is None:
            pet_experience = profile.get("pet_experience") or self._infer_experience(dynamic_traits)
            inferred_experience = 2 if pet_experience == "3年以上" else (1 if pet_experience and pet_experience != "无" else 0)

        query.user_profile = {
            "age_range": profile.get("age_range") or self._infer_age(dynamic_traits),
            "housing_type": profile.get("housing_type") or self._infer_housing(dynamic_traits),
            "has_yard": bool(profile.get("has_yard", 0)) if "has_yard" in profile else ("院子" in str(dynamic_traits)),
            "family_size": profile.get("family_size", 1),
            "has_children": bool(profile.get("has_children", 0)) if "has_children" in profile else ("孩子" in str(dynamic_traits) or "小孩" in str(dynamic_traits)),
            "has_other_pets": bool(profile.get("has_other_pets", 0)) if "has_other_pets" in profile else ("原住民" in str(dynamic_traits) or "养了" in str(dynamic_traits)),
            "housing_size": profile.get("housing_size") or self._infer_size(dynamic_traits),
            "rental_status": profile.get("rental_status") or ("租房" if "租" in str(dynamic_traits) else "未知"),
            "pet_experience": profile.get("pet_experience") or self._infer_experience(dynamic_traits),
            "experience_level": inferred_experience,
            "available_time": profile.get("available_time") or self._infer_time(dynamic_traits),
            "family_support": bool(profile.get("family_support", 0)) if "family_support" in profile else ("支持" in str(dynamic_traits)),
            "budget_level": profile.get("budget_level") or self._infer_budget(dynamic_traits),
            "allergy_info": profile.get("allergy_info") or ("过敏" if "过敏" in str(dynamic_traits) else ""),
            "family_structure": profile.get("family_structure", "纯成年人"),
            "activity_level": profile.get("activity_level", "宅家型"),
            "risk_flags": dynamic_traits.get("risk_flags", []),
            "strengths": dynamic_traits.get("strengths", [])
        }

        # 4. 组装偏好 Preference
        if not preference:
            preference = {}
            
        query.user_preferences = {
            "preferred_pet_type": preference.get("preferred_pet_type"),
            "preferred_age_range": preference.get("preferred_age_range"),
            "preferred_size": preference.get("preferred_size"),
            "accept_special_care": bool(preference.get("accept_special_care", 0)),
            "accept_high_energy": bool(preference.get("accept_high_energy", 1)),
            "preferred_temperament": preference.get("preferred_temperament") or profile.get("preferred_temperament")
        }

        return query

    def _infer_age(self, traits):
        t_str = str(traits).lower()
        if "学生" in t_str: return "18-25"
        if "上班族" in t_str: return "26-35"
        if "退休" in t_str: return "50+"
        return "未知"

    def _infer_housing(self, traits):
        t_str = str(traits).lower()
        if "别墅" in t_str: return "别墅"
        if "公寓" in t_str or "楼房" in t_str: return "公寓"
        return "未知"

    def _infer_size(self, traits):
        if "大房子" in str(traits): return 100.0
        return 50.0

    def _infer_experience(self, traits):
        t_str = str(traits).lower()
        if "有经验" in t_str or "养过" in t_str: return "1-3年"
        return "无"

    def _infer_time(self, traits):
        if "全职" in str(traits): return 8.0
        if "加班" in str(traits): return 1.0
        return 3.0

    def _infer_budget(self, traits):
        if "高薪" in str(traits) or "不差钱" in str(traits): return "高"
        return "中"

