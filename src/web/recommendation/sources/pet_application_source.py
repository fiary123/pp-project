from src.web.recommendation.candidate import RecommendationCandidate

class PetApplicationSource:
    """
    推荐系统数据源 - 获取某只宠物下的全部申请人作为候选集
    """
    def __init__(self, application_service):
        self.application_service = application_service

    async def get_candidates(self, query):
        # 这里的 query.pet_id 是发布者正在查看的宠物
        applications = self.application_service.list_by_pet_id(query.pet_id)

        return [
            RecommendationCandidate(
                candidate_id=app['user_id'], # 候选人是申请用户
                candidate_type="applicant",
                raw_data={"application": app},
            )
            for app in applications
        ]
