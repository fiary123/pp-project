from src.web.recommendation.query import RecommendationQuery
from src.web.recommendation.pipeline import RecommendationPipeline
from src.web.recommendation.sources.available_pet_source import AvailablePetSource
from src.web.recommendation.sources.pet_application_source import PetApplicationSource
from src.web.recommendation.hydrators.user_query_hydrator import UserQueryHydrator
from src.web.recommendation.hydrators.pet_feature_hydrator import PetFeatureHydrator
from src.web.recommendation.hydrators.applicant_context_hydrator import ApplicantContextHydrator
from src.web.recommendation.filters.hard_constraint_filter import HardConstraintFilter
from src.web.recommendation.filters.applicant_constraint_filter import ApplicantConstraintFilter
from src.web.recommendation.scorers.multi_feature_scorer import MultiFeatureScorer
from src.web.recommendation.scorers.applicant_match_scorer import ApplicantMatchScorer
from src.web.recommendation.selectors.topk_selector import TopKSelector
from src.web.services.pet_service import PetService
from src.web.services.application_service import ApplicationService

class RecommendationService:
    """
    推荐系统服务层 - 负责组装和执行特定的推荐流水线
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service
        self.pet_service = PetService()
        self.application_service = ApplicationService()

    async def recommend_pets_for_user(self, user_id: int):
        """场景1: 给领养用户推荐宠物 (Pet Discovery)"""
        # 1. 创建初始 Query
        query = RecommendationQuery(user_id=user_id, scene="pet_for_user")

        # 2. 组装流水线
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

    async def rank_applicants_for_pet(self, pet_id: int):
        """场景2: 给发布者排序申请人 (Applicant Ranking)"""
        # 1. 创建初始 Query (user_id=0 表示不针对特定用户，而是针对宠物)
        query = RecommendationQuery(user_id=0, scene="applicant_for_pet", pet_id=pet_id)

        # 2. 组装流水线
        pipeline = RecommendationPipeline(
            query_hydrators=[], # 申请场景主要补全候选人
            sources=[
                PetApplicationSource(self.application_service),
            ],
            hydrators=[
                ApplicantContextHydrator(
                    self.profile_service,
                    self.pet_service
                ),
            ],
            filters=[
                ApplicantConstraintFilter(),
            ],
            scorers=[
                ApplicantMatchScorer(),
            ],
            selector=TopKSelector(k=10),
        )

        # 3. 执行流水线并返回结果
        return await pipeline.execute(query)
