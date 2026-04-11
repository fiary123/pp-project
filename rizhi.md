可以，下一步就正式进入 X 核心流程的轻量化重构。

这一步只做一件事：

先跑通“给用户推荐宠物”这条链

也就是把这条流程先搭起来：

Query → Source → Hydrator → Filter → Scorer → Selector

你先别做“给发布者排序申请人”，那是下一轮。

这一步要新增的文件
app/recommendation/query.py
app/recommendation/candidate.py
app/recommendation/pipeline.py

app/recommendation/sources/available_pet_source.py
app/recommendation/hydrators/user_query_hydrator.py
app/recommendation/hydrators/pet_feature_hydrator.py
app/recommendation/filters/hard_constraint_filter.py
app/recommendation/scorers/multi_feature_scorer.py
app/recommendation/selectors/topk_selector.py

app/service/recommendation_service.py
app/router/recommendation.py
第一步代码：定义 Query 和 Candidate
app/recommendation/query.py
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RecommendationQuery:
    user_id: int
    scene: str = "pet_for_user"
    pet_id: Optional[int] = None
    user_profile: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
app/recommendation/candidate.py
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RecommendationCandidate:
    candidate_id: int
    candidate_type: str  # pet / applicant
    raw_data: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
第二步代码：搭 Pipeline 骨架
app/recommendation/pipeline.py
from typing import List


class RecommendationPipeline:
    def __init__(self, query_hydrators, sources, hydrators, filters, scorers, selector):
        self.query_hydrators = query_hydrators
        self.sources = sources
        self.hydrators = hydrators
        self.filters = filters
        self.scorers = scorers
        self.selector = selector

    async def execute(self, query):
        for hydrator in self.query_hydrators:
            query = await hydrator.hydrate(query)

        candidates: List = []
        for source in self.sources:
            source_candidates = await source.get_candidates(query)
            candidates.extend(source_candidates)

        for hydrator in self.hydrators:
            candidates = await hydrator.hydrate(query, candidates)

        for flt in self.filters:
            candidates = await flt.filter(query, candidates)

        for scorer in self.scorers:
            candidates = await scorer.score(query, candidates)

        return self.selector.select(candidates)

这一步就是把 X 的 candidate pipeline 思路先落地。

第三步代码：实现 Query Hydrator
app/recommendation/hydrators/user_query_hydrator.py
class UserQueryHydrator:
    def __init__(self, profile_service):
        self.profile_service = profile_service

    async def hydrate(self, query):
        profile = self.profile_service.get_profile_by_user_id(query.user_id)
        preference = self.profile_service.get_preference_by_user_id(query.user_id)

        query.user_profile = {
            "housing_type": getattr(profile, "housing_type", None),
            "housing_size": getattr(profile, "housing_size", None),
            "rental_status": getattr(profile, "rental_status", None),
            "pet_experience": getattr(profile, "pet_experience", False),
            "available_time": getattr(profile, "available_time", None),
            "family_support": getattr(profile, "family_support", False),
            "budget_level": getattr(profile, "budget_level", None),
        }

        query.user_preferences = {
            "preferred_pet_type": getattr(preference, "preferred_pet_type", None),
            "preferred_age_range": getattr(preference, "preferred_age_range", None),
            "preferred_size": getattr(preference, "preferred_size", None),
            "accept_special_care": getattr(preference, "accept_special_care", False),
            "accept_high_energy": getattr(preference, "accept_high_energy", False),
        }
        return query

注意这里依赖你上一轮已经建好的 ProfileService。

第四步代码：实现 Source
app/recommendation/sources/available_pet_source.py
from app.recommendation.candidate import RecommendationCandidate


class AvailablePetSource:
    def __init__(self, pet_service):
        self.pet_service = pet_service

    async def get_candidates(self, query):
        pets = self.pet_service.list_available_pets()

        return [
            RecommendationCandidate(
                candidate_id=pet.id,
                candidate_type="pet",
                raw_data={"pet": pet},
            )
            for pet in pets
        ]

这一步只取“当前可领养宠物”，先别搞复杂来源。

第五步代码：补全宠物特征
app/recommendation/hydrators/pet_feature_hydrator.py
class PetFeatureHydrator:
    def __init__(self, pet_feature_service):
        self.pet_feature_service = pet_feature_service

    async def hydrate(self, query, candidates):
        for candidate in candidates:
            pet = candidate.raw_data["pet"]
            feature = self.pet_feature_service.get_feature_by_pet_id(pet.id)
            requirement = self.pet_feature_service.get_requirement_by_pet_id(pet.id)

            candidate.features["pet"] = {
                "pet_type": getattr(pet, "pet_type", None),
                "age": getattr(pet, "age", None),
                "energy_level": getattr(feature, "energy_level", None),
                "care_level": getattr(feature, "care_level", None),
                "beginner_friendly": getattr(feature, "beginner_friendly", True),
                "social_level": getattr(feature, "social_level", None),
                "special_care_flag": getattr(feature, "special_care_flag", False),
            }

            candidate.features["requirement"] = {
                "require_experience": getattr(requirement, "require_experience", False),
                "require_stable_housing": getattr(requirement, "require_stable_housing", False),
                "require_return_visit": getattr(requirement, "require_return_visit", False),
                "region_limit": getattr(requirement, "region_limit", None),
            }

        return candidates
第六步代码：先做硬性过滤
app/recommendation/filters/hard_constraint_filter.py
class HardConstraintFilter:
    async def filter(self, query, candidates):
        result = []

        for candidate in candidates:
            pet = candidate.features["pet"]
            req = candidate.features["requirement"]
            profile = query.user_profile
            pref = query.user_preferences

            # 需要经验，但用户无经验
            if req["require_experience"] and not profile.get("pet_experience", False):
                continue

            # 特殊护理宠物，但用户不接受
            if pet["special_care_flag"] and not pref.get("accept_special_care", False):
                continue

            # 高精力宠物，但用户可投入时间较少
            if pet["energy_level"] == "high" and profile.get("available_time") == "low":
                continue

            result.append(candidate)

        return result

这一层就是你项目里非常重要的“规则前置”。

第七步代码：做轻量化评分器
app/recommendation/scorers/multi_feature_scorer.py
class MultiFeatureScorer:
    async def score(self, query, candidates):
        for candidate in candidates:
            pet = candidate.features["pet"]
            req = candidate.features["requirement"]
            profile = query.user_profile
            pref = query.user_preferences

            condition_score = 0.0
            preference_score = 0.0
            experience_score = 0.0
            stability_score = 0.0
            risk_penalty = 0.0

            # 条件匹配
            if req["require_experience"] == bool(profile.get("pet_experience", False)):
                condition_score += 20
            if not req["require_stable_housing"] or profile.get("rental_status") in ["own", "family"]:
                condition_score += 15

            # 偏好匹配
            if pref.get("preferred_pet_type") == pet.get("pet_type"):
                preference_score += 20
                candidate.reasons.append("宠物类型与用户偏好一致")

            # 经验适配
            if profile.get("pet_experience", False):
                experience_score += 20
                candidate.reasons.append("用户具备养宠经验")
            elif pet.get("beginner_friendly", True):
                experience_score += 10
                candidate.reasons.append("宠物适合新手饲养")

            # 稳定性参考
            if profile.get("family_support", False):
                stability_score += 10
                candidate.reasons.append("家庭支持养宠")
            if profile.get("available_time") in ["medium", "high"]:
                stability_score += 10
                candidate.reasons.append("用户可投入较稳定照护时间")

            # 风险扣分
            if pet.get("special_care_flag", False) and not profile.get("pet_experience", False):
                risk_penalty += 15
                candidate.risk_flags.append("特殊护理需求与用户经验不匹配")

            candidate.scores = {
                "condition_score": condition_score,
                "preference_score": preference_score,
                "experience_score": experience_score,
                "stability_score": stability_score,
                "risk_penalty": risk_penalty,
            }

            candidate.final_score = (
                0.35 * condition_score
                + 0.25 * preference_score
                + 0.20 * experience_score
                + 0.20 * stability_score
                - risk_penalty
            )

        return candidates
第八步代码：选择 Top-K
app/recommendation/selectors/topk_selector.py
class TopKSelector:
    def __init__(self, k=5):
        self.k = k

    def select(self, candidates):
        ranked = sorted(candidates, key=lambda x: x.final_score, reverse=True)
        return ranked[: self.k]
第九步代码：Service 组装整条链
app/service/recommendation_service.py
from app.recommendation.query import RecommendationQuery
from app.recommendation.pipeline import RecommendationPipeline
from app.recommendation.sources.available_pet_source import AvailablePetSource
from app.recommendation.hydrators.user_query_hydrator import UserQueryHydrator
from app.recommendation.hydrators.pet_feature_hydrator import PetFeatureHydrator
from app.recommendation.filters.hard_constraint_filter import HardConstraintFilter
from app.recommendation.scorers.multi_feature_scorer import MultiFeatureScorer
from app.recommendation.selectors.topk_selector import TopKSelector


class RecommendationService:
    def __init__(self, profile_service, pet_service, pet_feature_service):
        self.profile_service = profile_service
        self.pet_service = pet_service
        self.pet_feature_service = pet_feature_service

    async def recommend_pets_for_user(self, user_id: int):
        query = RecommendationQuery(user_id=user_id, scene="pet_for_user")

        pipeline = RecommendationPipeline(
            query_hydrators=[
                UserQueryHydrator(self.profile_service),
            ],
            sources=[
                AvailablePetSource(self.pet_service),
            ],
            hydrators=[
                PetFeatureHydrator(self.pet_feature_service),
            ],
            filters=[
                HardConstraintFilter(),
            ],
            scorers=[
                MultiFeatureScorer(),
            ],
            selector=TopKSelector(k=5),
        )

        return await pipeline.execute(query)
第十步代码：提供 API 接口
app/router/recommendation.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.service.profile_service import ProfileService
from app.service.pet_service import PetService
from app.service.pet_feature_service import PetFeatureService
from app.service.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("/pets/{user_id}")
async def recommend_pets(user_id: int, db: Session = Depends(get_db)):
    profile_service = ProfileService(db)
    pet_service = PetService(db)
    pet_feature_service = PetFeatureService(db)

    service = RecommendationService(
        profile_service=profile_service,
        pet_service=pet_service,
        pet_feature_service=pet_feature_service,
    )

    results = await service.recommend_pets_for_user(user_id)

    return [
        {
            "pet_id": item.candidate_id,
            "score": round(item.final_score, 2),
            "reasons": item.reasons,
            "risk_flags": item.risk_flags,
            "sub_scores": item.scores,
        }
        for item in results
    ]
主程序别忘了注册
from app.router import recommendation

app.include_router(recommendation.router)
这一步改完后，你能得到什么

你马上就会有一个可以演示的接口：

GET /recommendation/pets/{user_id}

返回结果会像这样：

[
  {
    "pet_id": 12,
    "score": 76.5,
    "reasons": [
      "宠物类型与用户偏好一致",
      "用户具备养宠经验",
      "家庭支持养宠"
    ],
    "risk_flags": [],
    "sub_scores": {
      "condition_score": 35.0,
      "preference_score": 20.0,
      "experience_score": 20.0,
      "stability_score": 10.0,
      "risk_penalty": 0.0
    }
  }
]

这就已经能体现：

候选获取
规则前置
多维评分
Top-K 选择
推荐解释

也就是你想借鉴的 X 核心流程。

你这一轮改完后，不要马上做什么

先不要立刻去做：

申请人排序
前端复杂推荐页
推荐记录表
回访反馈闭环

先把这条接口跑通再说。

你现在的执行顺序

按最稳的顺序来：

新建 recommendation/ 目录
写 query.py、candidate.py、pipeline.py
写 AvailablePetSource
写两个 hydrator
写 HardConstraintFilter
写 MultiFeatureScorer
写 TopKSelector
写 recommendation_service.py
暴露 /recommendation/pets/{user_id} 接口
用已有测试数据跑一遍
这一轮完成后，真正的下一步

下一轮才是：

把同样的流水线改成“给发布者排序申请人”

那时你只需要换掉：

Source
Hydrator
Filter
Scorer

Pipeline 主体可以复用。

这才是你这次重构最漂亮的地方。