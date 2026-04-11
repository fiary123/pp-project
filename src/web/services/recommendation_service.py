from src.web.recommendation.query import RecommendationQuery
from src.web.recommendation.pipeline import RecommendationPipeline
from src.web.recommendation.sources.available_pet_source import AvailablePetSource
from src.web.recommendation.hydrators.user_query_hydrator import UserQueryHydrator
from src.web.recommendation.hydrators.pet_feature_hydrator import PetFeatureHydrator
from src.web.recommendation.filters.hard_constraint_filter import HardConstraintFilter
from src.web.recommendation.scorers.multi_feature_scorer import MultiFeatureScorer
from src.web.recommendation.selectors.topk_selector import TopKSelector

class RecommendationService:
    """
    推荐系统服务层 - 负责组装和执行特定的推荐流水线
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service

    async def recommend_pets_for_user(self, user_id: int):
        # 1. 创建初始 Query
        query = RecommendationQuery(user_id=user_id, scene="pet_for_user")

        # 2. 组装流水线 (借鉴 X 核心逻辑)
        pipeline = RecommendationPipeline(
            query_hydrators=[
                UserQueryHydrator(self.profile_service),
            ],
            sources=[
                AvailablePetSource(),
            ],
            hydrators=[
                PetFeatureHydrator(self.profile_service),
            ],
            filters=[
                HardConstraintFilter(),
            ],
            scorers=[
                MultiFeatureScorer(),
            ],
            selector=TopKSelector(k=5),
        )

        # 3. 执行流水线并返回结果
        return await pipeline.execute(query)
