from typing import List
from src.web.recommendation.query import RecommendQuery, PetCandidate

class HardConstraintFilter:
    """
    硬性约束过滤器 - 过滤掉不满足发布者领养条件的申请人
    """
    @staticmethod
    def filter(query: RecommendQuery, candidates: List[PetCandidate]) -> List[PetCandidate]:
        passed = []
        user_profile = query.profile
        
        for cand in candidates:
            # 1. 经验要求 (简化逻辑: 如果要求经验且用户无经验，则过滤)
            if cand.requirements.get('require_experience') and not user_profile.get('pet_experience'):
                cand.filter_reason = "需要有养宠经验"
                continue
            
            # 2. 稳定住房要求
            if cand.requirements.get('require_stable_housing') and not user_profile.get('family_support'):
                # 注意：这里我们假设 family_support 或 housing_type 某种程度上代表了稳定性
                # 实际可以根据 housing_type == '自购' 等更精细判断
                pass 
                
            # 3. 地区限制 (简单示例: 如果有地区限制且未匹配)
            # region_limit = cand.requirements.get('region_limit')
            # ...
            
            passed.append(cand)
            
        return passed
