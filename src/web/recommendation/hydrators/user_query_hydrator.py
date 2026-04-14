import logging
import asyncio
from src.agents.agents import analyze_pet_interview

logger = logging.getLogger(__name__)

class UserQueryHydrator:
    """
    用户上下文补全器 - 增强版 (支持 Enum 归一化与 Agent 语义提取)
    1. 从 ProfileService 获取结构化画像。
    2. 如果核心字段缺失且存在用户输入描述 (user_query)，调用 Agent 进行实时特征提取。
    3. 统一枚举值映射 (Enum Mapping)。
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service
        # 枚举值统一映射层 (兼容前端英文值与后端逻辑)
        self.enum_map = {
            "apartment": "公寓", "house": "别墅", "flat": "平房",
            "low": "低", "medium": "中", "high": "高",
            "none": "无", "1-3years": "1-3年", "3+years": "3年以上"
        }

    def _normalize_profile(self, profile: dict) -> dict:
        """归一化特征值"""
        if not profile: return {}
        normalized = profile.copy()
        for k, v in normalized.items():
            if isinstance(v, str) and v.lower() in self.enum_map:
                normalized[k] = self.enum_map[v.lower()]
        return normalized

    async def hydrate(self, query):
        # 1. 尝试从数据库获取持久化画像
        profile = self.profile_service.get_user_profile(query.user_id) or {}
        preference = self.profile_service.get_user_preferences(query.user_id) or {}

        # 2. 冷启动逻辑：如果画像核心字段缺失且有 user_query，则调用 Agent 动态分析
        dynamic_traits = {}
        if (not profile or not profile.get("housing_type")) and query.user_query:
            try:
                logger.info(f"触发推荐冷启动特征提取，用户 ID: {query.user_id}")
                # 调用 agents.py 中的分析函数进行语义提取
                analysis = await analyze_pet_interview(
                    user_msg=query.user_query,
                    pet_name="系统推荐引擎",
                    pet_species="所有",
                    pet_desc="推荐画像提取请求"
                )
                dynamic_traits = analysis
                logger.info(f"语义特征提取成功: {dynamic_traits.get('user_traits')}")
            except Exception as e:
                logger.error(f"语义特征提取失败: {str(e)}")

        # 3. 组装结构化 Profile (数据库优先，Agent 补充)
        inferred_experience = profile.get("experience_level")
        if inferred_experience is None:
            # 基于语义提取结果进行经验推断
            t_str = str(dynamic_traits).lower()
            if "专家" in t_str or "资深" in t_str: inferred_experience = 2
            elif "有经验" in t_str or "养过" in t_str: inferred_experience = 1
            else: inferred_experience = 0

        # 归一化处理并填充到 Query
        query.user_profile = self._normalize_profile({
            "age_range": profile.get("age_range") or "26-35",
            "housing_type": profile.get("housing_type") or ("别墅" if "别墅" in str(dynamic_traits) else "公寓"),
            "has_yard": bool(profile.get("has_yard", 0)) or ("院子" in str(dynamic_traits)),
            "family_size": profile.get("family_size", 1),
            "has_children": bool(profile.get("has_children", 0)) or ("孩子" in str(dynamic_traits)),
            "has_other_pets": bool(profile.get("has_other_pets", 0)) or ("养了" in str(dynamic_traits)),
            "housing_size": profile.get("housing_size") or (100.0 if "大房子" in str(dynamic_traits) else 50.0),
            "rental_status": profile.get("rental_status") or ("租房" if "租" in str(dynamic_traits) else "自购"),
            "pet_experience": profile.get("pet_experience") or ("无" if inferred_experience == 0 else "1-3年"),
            "experience_level": inferred_experience,
            "available_time": profile.get("available_time") or 3.0,
            "family_support": bool(profile.get("family_support", 1)),
            "budget_level": profile.get("budget_level") or "中",
            "allergy_info": profile.get("allergy_info", ""),
            "family_structure": profile.get("family_structure", "纯成年人"),
            "activity_level": profile.get("activity_level", "宅家型"),
            "agent_inferred": bool(dynamic_traits) # 标记是否使用了 Agent 推断
        })

        query.user_preferences = self._normalize_profile({
            "preferred_pet_type": preference.get("preferred_pet_type") or "不限",
            "preferred_age_range": preference.get("preferred_age_range") or "成年",
            "preferred_size": preference.get("preferred_size") or "中型",
            "accept_special_care": bool(preference.get("accept_special_care", 0)),
            "accept_high_energy": bool(preference.get("accept_high_energy", 1)),
            "preferred_temperament": preference.get("preferred_temperament") or "温顺"
        })

        return query
