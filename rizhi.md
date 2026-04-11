可以，下一步就做：

把同一套流水线改成“给发布者排序申请人”

也就是新增这条链：

PetQuery → ApplicationSource → ApplicantHydrator → ApplicantConstraintFilter → ApplicantMatchScorer → TopKSelector

这一步做完后，你的项目就不只是“给用户推荐宠物”，而是已经进入你论文里更有分量的部分：

推荐结果参与审核辅助。

一、这一步新增的文件
app/recommendation/sources/pet_application_source.py
app/recommendation/hydrators/applicant_context_hydrator.py
app/recommendation/filters/applicant_constraint_filter.py
app/recommendation/scorers/applicant_match_scorer.py

然后修改：

app/service/recommendation_service.py
app/router/recommendation.py
二、先约定这一条链依赖哪些数据

这一步默认你已经有这些：

applications 表
user_profiles
user_preferences
pet_features
pet_requirements

如果你的申请表里还没有这些字段，至少先保证 applications 里能拿到：

user_id
pet_id
accept_return_visit
application_reason
status

如果没有 accept_return_visit，这一版先删掉对应判断也可以。
三、Source：先取某只宠物下的全部申请人
app/recommendation/sources/pet_application_source.py
from app.recommendation.candidate import RecommendationCandidate


class PetApplicationSource:
    def __init__(self, application_service):
        self.application_service = application_service

    async def get_candidates(self, query):
        applications = self.application_service.list_by_pet_id(query.pet_id)

        return [
            RecommendationCandidate(
                candidate_id=app.user_id,
                candidate_type="applicant",
                raw_data={"application": app},
            )
            for app in applications
        ]

这一步对应 X 里的 candidate source，只不过你的候选不是帖子，而是申请人。

四、Hydrator：补全申请人上下文
app/recommendation/hydrators/applicant_context_hydrator.py
class ApplicantContextHydrator:
    def __init__(self, profile_service, pet_service, pet_feature_service):
        self.profile_service = profile_service
        self.pet_service = pet_service
        self.pet_feature_service = pet_feature_service

    async def hydrate(self, query, candidates):
        pet = self.pet_service.get_pet_by_id(query.pet_id)
        pet_feature = self.pet_feature_service.get_feature_by_pet_id(query.pet_id)
        pet_requirement = self.pet_feature_service.get_requirement_by_pet_id(query.pet_id)

        for candidate in candidates:
            application = candidate.raw_data["application"]

            profile = self.profile_service.get_profile_by_user_id(application.user_id)
            preference = self.profile_service.get_preference_by_user_id(application.user_id)

            candidate.features["applicant_profile"] = {
                "housing_type": getattr(profile, "housing_type", None),
                "housing_size": getattr(profile, "housing_size", None),
                "rental_status": getattr(profile, "rental_status", None),
                "pet_experience": getattr(profile, "pet_experience", False),
                "available_time": getattr(profile, "available_time", None),
                "family_support": getattr(profile, "family_support", False),
                "budget_level": getattr(profile, "budget_level", None),
            }

            candidate.features["applicant_preference"] = {
                "preferred_pet_type": getattr(preference, "preferred_pet_type", None),
                "preferred_age_range": getattr(preference, "preferred_age_range", None),
                "preferred_size": getattr(preference, "preferred_size", None),
                "accept_special_care": getattr(preference, "accept_special_care", False),
                "accept_high_energy": getattr(preference, "accept_high_energy", False),
            }

            candidate.features["application"] = {
                "accept_return_visit": getattr(application, "accept_return_visit", False),
                "application_reason": getattr(application, "application_reason", ""),
                "status": getattr(application, "status", None),
            }

            candidate.features["pet"] = {
                "pet_type": getattr(pet, "pet_type", None),
                "age": getattr(pet, "age", None),
                "energy_level": getattr(pet_feature, "energy_level", None),
                "care_level": getattr(pet_feature, "care_level", None),
                "beginner_friendly": getattr(pet_feature, "beginner_friendly", True),
                "social_level": getattr(pet_feature, "social_level", None),
                "special_care_flag": getattr(pet_feature, "special_care_flag", False),
            }

            candidate.features["requirement"] = {
                "require_experience": getattr(pet_requirement, "require_experience", False),
                "require_stable_housing": getattr(pet_requirement, "require_stable_housing", False),
                "require_return_visit": getattr(pet_requirement, "require_return_visit", False),
                "region_limit": getattr(pet_requirement, "region_limit", None),
            }

        return candidates

这里的重点是：
把申请人、申请表、宠物、送养要求全补到一个 candidate 上。
五、Filter：先做审核前的硬性筛查
app/recommendation/filters/applicant_constraint_filter.py
class ApplicantConstraintFilter:
    async def filter(self, query, candidates):
        result = []

        for candidate in candidates:
            profile = candidate.features["applicant_profile"]
            app = candidate.features["application"]
            pet = candidate.features["pet"]
            req = candidate.features["requirement"]

            # 需要经验，但申请人无经验
            if req["require_experience"] and not profile.get("pet_experience", False):
                continue

            # 要求稳定住房，但申请人是租房且条件不稳定
            if req["require_stable_housing"] and profile.get("rental_status") == "rent":
                continue

            # 要求接受回访，但申请人不接受
            if req["require_return_visit"] and not app.get("accept_return_visit", False):
                continue

            # 特殊护理宠物，但申请人不具备基础接受意愿
            if pet.get("special_care_flag", False) and not profile.get("pet_experience", False):
                # 这里先不过滤，也可只打风险标签
                candidate.risk_flags.append("特殊护理宠物与申请人经验存在风险")

            result.append(candidate)

        return result

这一层就是你论文里非常好写的：

审核前的规则前置筛查。
六、Scorer：对申请人做匹配排序
app/recommendation/scorers/applicant_match_scorer.py
class ApplicantMatchScorer:
    async def score(self, query, candidates):
        for candidate in candidates:
            profile = candidate.features["applicant_profile"]
            pref = candidate.features["applicant_preference"]
            app = candidate.features["application"]
            pet = candidate.features["pet"]
            req = candidate.features["requirement"]

            condition_score = 0.0
            care_score = 0.0
            preference_score = 0.0
            stability_score = 0.0
            risk_penalty = 0.0

            # 1. 条件匹配分
            if req["require_experience"] == bool(profile.get("pet_experience", False)):
                condition_score += 20
            if req["require_return_visit"] == bool(app.get("accept_return_visit", False)):
                condition_score += 15

            # 2. 照护能力分
            if profile.get("available_time") in ["medium", "high"]:
                care_score += 15
                candidate.reasons.append("申请人具备较稳定照护时间")
            if profile.get("pet_experience", False):
                care_score += 20
                candidate.reasons.append("申请人具备养宠经验")
            elif pet.get("beginner_friendly", True):
                care_score += 10
                candidate.reasons.append("宠物适合新手照护")

            # 3. 偏好一致性
            if pref.get("preferred_pet_type") == pet.get("pet_type"):
                preference_score += 15
                candidate.reasons.append("申请人偏好与宠物类型一致")

            # 4. 稳定性参考
            if profile.get("family_support", False):
                stability_score += 10
                candidate.reasons.append("申请人家庭支持养宠")
            if profile.get("rental_status") in ["own", "family"]:
                stability_score += 10
                candidate.reasons.append("申请人居住条件相对稳定")

            # 5. 风险扣分
            if pet.get("energy_level") == "high" and profile.get("available_time") == "low":
                risk_penalty += 10
                candidate.risk_flags.append("高活动量宠物与申请人时间投入不匹配")

            if pet.get("special_care_flag", False) and not profile.get("pet_experience", False):
                risk_penalty += 15
                candidate.risk_flags.append("特殊护理需求与申请人经验不匹配")

            candidate.scores = {
                "condition_score": condition_score,
                "care_score": care_score,
                "preference_score": preference_score,
                "stability_score": stability_score,
                "risk_penalty": risk_penalty,
            }

            candidate.final_score = (
                0.35 * condition_score
                + 0.30 * care_score
                + 0.15 * preference_score
                + 0.20 * stability_score
                - risk_penalty
            )

        return candidates

这一步就是把“申请人排序”做成真正的推荐逻辑，而不是按时间顺序看申请表。

七、修改 RecommendationService

在你上一轮的 RecommendationService 基础上，加一个新方法。

app/service/recommendation_service.py
from app.recommendation.sources.pet_application_source import PetApplicationSource
from app.recommendation.hydrators.applicant_context_hydrator import ApplicantContextHydrator
from app.recommendation.filters.applicant_constraint_filter import ApplicantConstraintFilter
from app.recommendation.scorers.applicant_match_scorer import ApplicantMatchScorer

然后新增：

    async def rank_applicants_for_pet(self, pet_id: int):
        query = RecommendationQuery(user_id=0, scene="applicant_for_pet", pet_id=pet_id)

        pipeline = RecommendationPipeline(
            query_hydrators=[],
            sources=[
                PetApplicationSource(self.application_service),
            ],
            hydrators=[
                ApplicantContextHydrator(
                    self.profile_service,
                    self.pet_service,
                    self.pet_feature_service,
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

        return await pipeline.execute(query)

注意这里 RecommendationService.__init__ 里要补一个 application_service 参数。

例如：

class RecommendationService:
    def __init__(self, profile_service, pet_service, pet_feature_service, application_service):
        self.profile_service = profile_service
        self.pet_service = pet_service
        self.pet_feature_service = pet_feature_service
        self.application_service = application_service
八、修改 recommendation 路由
app/router/recommendation.py

新增一个接口：

from app.service.application_service import ApplicationService

然后补：

@router.get("/pets/{pet_id}/applicants")
async def rank_applicants(pet_id: int, db: Session = Depends(get_db)):
    profile_service = ProfileService(db)
    pet_service = PetService(db)
    pet_feature_service = PetFeatureService(db)
    application_service = ApplicationService(db)

    service = RecommendationService(
        profile_service=profile_service,
        pet_service=pet_service,
        pet_feature_service=pet_feature_service,
        application_service=application_service,
    )

    results = await service.rank_applicants_for_pet(pet_id)

    return [
        {
            "user_id": item.candidate_id,
            "score": round(item.final_score, 2),
            "reasons": item.reasons,
            "risk_flags": item.risk_flags,
            "sub_scores": item.scores,
        }
        for item in results
    ]
九、你这一步做完后的效果

现在你就会有两个核心接口：

1. 给领养用户推荐宠物

GET /recommendation/pets/{user_id}

2. 给发布者排序申请人

GET /recommendation/pets/{pet_id}/applicants

第二个接口才是你答辩时最能打的点，因为它直接体现：

推荐算法不是摆设
推荐结果进入审核环节
系统能辅助发布者做筛选
十、返回结果示例
[
  {
    "user_id": 7,
    "score": 82.5,
    "reasons": [
      "申请人具备较稳定照护时间",
      "申请人具备养宠经验",
      "申请人偏好与宠物类型一致",
      "申请人居住条件相对稳定"
    ],
    "risk_flags": [],
    "sub_scores": {
      "condition_score": 35.0,
      "care_score": 35.0,
      "preference_score": 15.0,
      "stability_score": 20.0,
      "risk_penalty": 0.0
    }
  },
  {
    "user_id": 12,
    "score": 58.0,
    "reasons": [
      "宠物适合新手照护"
    ],
    "risk_flags": [
      "高活动量宠物与申请人时间投入不匹配"
    ],
    "sub_scores": {
      "condition_score": 20.0,
      "care_score": 10.0,
      "preference_score": 15.0,
      "stability_score": 10.0,
      "risk_penalty": 10.0
    }
  }
]

这个结果已经非常像“审核辅助排序”了。
六、Scorer：对申请人做匹配排序
app/recommendation/scorers/applicant_match_scorer.py
class ApplicantMatchScorer:
    async def score(self, query, candidates):
        for candidate in candidates:
            profile = candidate.features["applicant_profile"]
            pref = candidate.features["applicant_preference"]
            app = candidate.features["application"]
            pet = candidate.features["pet"]
            req = candidate.features["requirement"]

            condition_score = 0.0
            care_score = 0.0
            preference_score = 0.0
            stability_score = 0.0
            risk_penalty = 0.0

            # 1. 条件匹配分
            if req["require_experience"] == bool(profile.get("pet_experience", False)):
                condition_score += 20
            if req["require_return_visit"] == bool(app.get("accept_return_visit", False)):
                condition_score += 15

            # 2. 照护能力分
            if profile.get("available_time") in ["medium", "high"]:
                care_score += 15
                candidate.reasons.append("申请人具备较稳定照护时间")
            if profile.get("pet_experience", False):
                care_score += 20
                candidate.reasons.append("申请人具备养宠经验")
            elif pet.get("beginner_friendly", True):
                care_score += 10
                candidate.reasons.append("宠物适合新手照护")

            # 3. 偏好一致性
            if pref.get("preferred_pet_type") == pet.get("pet_type"):
                preference_score += 15
                candidate.reasons.append("申请人偏好与宠物类型一致")

            # 4. 稳定性参考
            if profile.get("family_support", False):
                stability_score += 10
                candidate.reasons.append("申请人家庭支持养宠")
            if profile.get("rental_status") in ["own", "family"]:
                stability_score += 10
                candidate.reasons.append("申请人居住条件相对稳定")

            # 5. 风险扣分
            if pet.get("energy_level") == "high" and profile.get("available_time") == "low":
                risk_penalty += 10
                candidate.risk_flags.append("高活动量宠物与申请人时间投入不匹配")

            if pet.get("special_care_flag", False) and not profile.get("pet_experience", False):
                risk_penalty += 15
                candidate.risk_flags.append("特殊护理需求与申请人经验不匹配")

            candidate.scores = {
                "condition_score": condition_score,
                "care_score": care_score,
                "preference_score": preference_score,
                "stability_score": stability_score,
                "risk_penalty": risk_penalty,
            }

            candidate.final_score = (
                0.35 * condition_score
                + 0.30 * care_score
                + 0.15 * preference_score
                + 0.20 * stability_score
                - risk_penalty
            )

        return candidates

这一步就是把“申请人排序”做成真正的推荐逻辑，而不是按时间顺序看申请表。

七、修改 RecommendationService

在你上一轮的 RecommendationService 基础上，加一个新方法。

app/service/recommendation_service.py
from app.recommendation.sources.pet_application_source import PetApplicationSource
from app.recommendation.hydrators.applicant_context_hydrator import ApplicantContextHydrator
from app.recommendation.filters.applicant_constraint_filter import ApplicantConstraintFilter
from app.recommendation.scorers.applicant_match_scorer import ApplicantMatchScorer

然后新增：

    async def rank_applicants_for_pet(self, pet_id: int):
        query = RecommendationQuery(user_id=0, scene="applicant_for_pet", pet_id=pet_id)

        pipeline = RecommendationPipeline(
            query_hydrators=[],
            sources=[
                PetApplicationSource(self.application_service),
            ],
            hydrators=[
                ApplicantContextHydrator(
                    self.profile_service,
                    self.pet_service,
                    self.pet_feature_service,
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

        return await pipeline.execute(query)

注意这里 RecommendationService.__init__ 里要补一个 application_service 参数。

例如：

class RecommendationService:
    def __init__(self, profile_service, pet_service, pet_feature_service, application_service):
        self.profile_service = profile_service
        self.pet_service = pet_service
        self.pet_feature_service = pet_feature_service
        self.application_service = application_service
八、修改 recommendation 路由
app/router/recommendation.py

新增一个接口：

from app.service.application_service import ApplicationService

然后补：

@router.get("/pets/{pet_id}/applicants")
async def rank_applicants(pet_id: int, db: Session = Depends(get_db)):
    profile_service = ProfileService(db)
    pet_service = PetService(db)
    pet_feature_service = PetFeatureService(db)
    application_service = ApplicationService(db)

    service = RecommendationService(
        profile_service=profile_service,
        pet_service=pet_service,
        pet_feature_service=pet_feature_service,
        application_service=application_service,
    )

    results = await service.rank_applicants_for_pet(pet_id)

    return [
        {
            "user_id": item.candidate_id,
            "score": round(item.final_score, 2),
            "reasons": item.reasons,
            "risk_flags": item.risk_flags,
            "sub_scores": item.scores,
        }
        for item in results
    ]
九、你这一步做完后的效果

现在你就会有两个核心接口：

1. 给领养用户推荐宠物

GET /recommendation/pets/{user_id}

2. 给发布者排序申请人

GET /recommendation/pets/{pet_id}/applicants

第二个接口才是你答辩时最能打的点，因为它直接体现：

推荐算法不是摆设
推荐结果进入审核环节
系统能辅助发布者做筛选
十、返回结果示例
[
  {
    "user_id": 7,
    "score": 82.5,
    "reasons": [
      "申请人具备较稳定照护时间",
      "申请人具备养宠经验",
      "申请人偏好与宠物类型一致",
      "申请人居住条件相对稳定"
    ],
    "risk_flags": [],
    "sub_scores": {
      "condition_score": 35.0,
      "care_score": 35.0,
      "preference_score": 15.0,
      "stability_score": 20.0,
      "risk_penalty": 0.0
    }
  },
  {
    "user_id": 12,
    "score": 58.0,
    "reasons": [
      "宠物适合新手照护"
    ],
    "risk_flags": [
      "高活动量宠物与申请人时间投入不匹配"
    ],
    "sub_scores": {
      "condition_score": 20.0,
      "care_score": 10.0,
      "preference_score": 15.0,
      "stability_score": 10.0,
      "risk_penalty": 10.0
    }
  }
]


这个结果已经非常像“审核辅助排序”了。