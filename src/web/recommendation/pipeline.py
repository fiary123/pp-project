from typing import List
from src.web.recommendation.query import RecommendQuery, PetCandidate
from src.web.recommendation.sources.available_pet_source import AvailablePetSource
from src.web.recommendation.hydrators.pet_feature_hydrator import PetFeatureHydrator
from src.web.recommendation.filters.hard_constraint_filter import HardConstraintFilter
from src.web.services.profile_service import ProfileService

class RecommendPipeline:
    """
    推荐流水线 - 协调数据源、数据补全、过滤、打分、选择
    """
    def __init__(self, user_id: int):
        self.query = RecommendQuery(user_id)
        
    def _prepare_query(self):
        # 1. 加载用户画像与偏好
        self.query.profile = ProfileService.get_user_profile(self.query.user_id) or {}
        self.query.preferences = ProfileService.get_user_preferences(self.query.user_id) or {}
        
    def run(self) -> List[PetCandidate]:
        # 0. 准备请求上下文
        self._prepare_query()
        
        # 1. 召回阶段 (Source)
        candidates = AvailablePetSource.get_candidates()
        
        # 2. 补全阶段 (Hydration)
        candidates = PetFeatureHydrator.hydrate(candidates)
        
        # 3. 过滤阶段 (Filtering)
        candidates = HardConstraintFilter.filter(self.query, candidates)
        
        # 4. 打分阶段 (Scoring - 待实现)
        # candidates = MultiFeatureScorer.score(self.query, candidates)
        
        # 5. 选择阶段 (Selection - 待实现)
        # candidates = TopKSelector.select(candidates, k=10)
        
        return candidates
