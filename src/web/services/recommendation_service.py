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
from src.web.recommendation.scorers.agent_decision_auditor import AgentDecisionAuditor
from src.web.recommendation.selectors.topk_selector import TopKSelector
from src.web.services.pet_service import PetService
from src.web.services.application_service import ApplicationService
from src.web.services.db_service import save_recommendation_log

class RecommendationService:
    """
    推荐系统服务层 - 负责组装和执行特定的推荐流水线，并持久化日志
    """
    def __init__(self, profile_service):
        self.profile_service = profile_service
        self.pet_service = PetService()
        self.application_service = ApplicationService()

    async def recommend_pets_for_user(self, user_id: int, user_query: str = ""):
        """场景1: 给领养用户推荐宠物 (Pet Discovery)"""
        # 1. 检查画像完整度 (冷启动检测)
        profile = self.profile_service.get_user_profile(user_id)
        needs_cold_start = False
        if (not profile or not profile.get("housing_type")) and not user_query:
            needs_cold_start = True

        # 2. 创建初始 Query
        query = RecommendationQuery(user_id=user_id, scene="pet_for_user", user_query=user_query)

        # 3. 组装流水线 (多阶段：生成->过滤->评分->Agent审计->排序)
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
                AgentDecisionAuditor(), # [重构新增]：多智能体决策审计阶段
            ],
            selector=TopKSelector(k=10),
        )

        # 4. 执行流水线
        results = await pipeline.execute(query)

        # 5. 持久化推荐日志
        for res in results:
            save_recommendation_log(
                scene="pet_recommendation",
                target_id=0,
                user_id=user_id,
                candidate_id=res.candidate_id,
                hard_filter_pass=getattr(res, 'hard_filter_pass', 1),
                score_detail=getattr(res, 'scores', {}),
                final_score=getattr(res, 'final_score', 0.0),
                reason_text="; ".join(res.reasons)
            )

        return {
            "results": results,
            "needs_cold_start": needs_cold_start,
            "query_obj": query # 导出 query 以便演示接口提取 trace
        }

    async def rank_applicants_for_pet(self, pet_id: int):
        """场景2: 给发布者排序申请人 (Applicant Ranking)"""
        # 1. 创建初始 Query
        query = RecommendationQuery(user_id=0, scene="applicant_for_pet", pet_id=pet_id)

        # 2. 组装流水线
        pipeline = RecommendationPipeline(
            query_hydrators=[], 
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
            selector=TopKSelector(k=20),
        )

        # 3. 执行流水线
        results = await pipeline.execute(query)

        # 4. 持久化日志 (场景：审核排序)
        for res in results:
            save_recommendation_log(
                scene="applicant_ranking",
                target_id=pet_id,
                user_id=res.candidate_id, # 申请人ID
                candidate_id=res.candidate_id,
                hard_filter_pass=getattr(res, 'hard_filter_pass', 1),
                score_detail=getattr(res, 'scores', {}),
                final_score=getattr(res, 'final_score', 0.0),
                reason_text="; ".join(res.reasons)
            )

        return results
