from typing import List

class RecommendationPipeline:
    """
    通用推荐流水线 - 协调各种组件完成推荐流程
    """
    def __init__(self, query_hydrators, sources, hydrators, filters, scorers, selector):
        self.query_hydrators = query_hydrators
        self.sources = sources
        self.hydrators = hydrators
        self.filters = filters
        self.scorers = scorers
        self.selector = selector

    async def execute(self, query):
        # 1. 补全请求上下文 (Query Hydration)
        for hydrator in self.query_hydrators:
            query = await hydrator.hydrate(query)

        # 2. 召回候选集 (Recall Phase)
        candidates: List = []
        for source in self.sources:
            source_candidates = await source.get_candidates(query)
            candidates.extend(source_candidates)

        # 3. 补全候选特征 (Candidate Hydration)
        for hydrator in self.hydrators:
            candidates = await hydrator.hydrate(query, candidates)

        # 4. 过滤不合规候选 (Filtering Phase)
        for flt in self.filters:
            candidates = await flt.filter(query, candidates)

        # 5. 计算分数 (Scoring Phase)
        for scorer in self.scorers:
            candidates = await scorer.score(query, candidates)

        # 6. 最终排序与选择 (Selection Phase)
        return self.selector.select(candidates)
