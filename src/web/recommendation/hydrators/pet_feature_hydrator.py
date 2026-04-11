from typing import List
from src.web.recommendation.query import PetCandidate
from src.web.services.profile_service import ProfileService

class PetFeatureHydrator:
    """
    数据补全器 - 为候选宠物填充详细的推荐特征和领养要求
    """
    @staticmethod
    def hydrate(candidates: List[PetCandidate]):
        for cand in candidates:
            # 补全宠物特征
            features = ProfileService.get_pet_features(cand.pet_id)
            cand.features = features if features else {}
            
            # 补全领养要求
            requirements = ProfileService.get_pet_requirements(cand.pet_id)
            cand.requirements = requirements if requirements else {}
            
        return candidates
