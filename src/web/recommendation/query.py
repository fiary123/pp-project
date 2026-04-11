from typing import Optional, Dict, Any

class RecommendQuery:
    """推荐系统请求对象 - 封装用户画像与偏好"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.profile: Dict[str, Any] = {}
        self.preferences: Dict[str, Any] = {}
        
    def __repr__(self):
        return f"<RecommendQuery(user_id={self.user_id})>"

class PetCandidate:
    """推荐系统候选对象 - 封装宠物实体及其扩展特征"""
    def __init__(self, pet_id: int, base_info: Dict[str, Any]):
        self.pet_id = pet_id
        self.base_info = base_info
        
        # 扩展特征 (将在 Hydration 阶段由 ProfileService 填充)
        self.features: Dict[str, Any] = {}
        self.requirements: Dict[str, Any] = {}
        
        # 评分与阶段状态
        self.score: float = 0.0
        self.filter_reason: Optional[str] = None
        
    def __repr__(self):
        return f"<PetCandidate(id={self.pet_id}, score={self.score})>"
