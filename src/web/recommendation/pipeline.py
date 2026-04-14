from typing import List, Dict, Any

class RecommendationPipeline:
    """
    增强型推荐流水线 - 支持执行追踪 (Execution Trace)
    记录每阶段的候选数量变化与详细统计，专为演示视角设计。
    """
    def __init__(self, query_hydrators, sources, hydrators, filters, scorers, selector):
        self.query_hydrators = query_hydrators
        self.sources = sources
        self.hydrators = hydrators
        self.filters = filters
        self.scorers = scorers
        self.selector = selector
        self.trace = {
            "phases": [],
            "query_context": {}
        }

    def _add_trace(self, phase_name: str, before_count: int, after_count: int, details: Any = None):
        self.trace["phases"].append({
            "phase": phase_name,
            "before": before_count,
            "after": after_count,
            "details": details
        })

    async def execute(self, query) -> List[Any]:
        # 重置追踪信息
        self.trace = {"phases": [], "query_context": {}}
        
        # 1. 查询补全 (Query Hydration Phase)
        for hydrator in self.query_hydrators:
            await hydrator.hydrate(query)
        self.trace["query_context"] = {
            "user_id": query.user_id,
            "scene": query.scene,
            "profile": query.user_profile,
            "preferences": query.user_preferences
        }

        # 2. 候选生成 (Recall Phase)
        candidates = []
        for source in self.sources:
            candidates.extend(await source.get_candidates(query))
        
        recall_count = len(candidates)
        self._add_trace("候选生成 (Recall)", 0, recall_count, {"sources": [type(s).__name__ for s in self.sources]})

        # 3. 特征补全 (Feature Hydration Phase)
        for hydrator in self.hydrators:
            candidates = await hydrator.hydrate(query, candidates)
        self._add_trace("特征补全 (Hydration)", recall_count, len(candidates))

        # 4. 约束过滤 (Constraint Filtering Phase)
        all_intercepted = []
        before_filter = len(candidates)
        
        for filter_obj in self.filters:
            # 尝试调用增强版过滤接口以获取拦截详情
            if hasattr(filter_obj, 'filter_with_details'):
                candidates, intercepted = await filter_obj.filter_with_details(query, candidates)
                all_intercepted.extend(intercepted)
            else:
                candidates = await filter_obj.filter(query, candidates)
        
        after_filter = len(candidates)
        self._add_trace("约束过滤 (Filtering)", before_filter, after_filter, {
            "intercepted_count": len(all_intercepted),
            "intercepted_samples": all_intercepted[:10] 
        })

        # 5. 多维评分 (精排) (Scoring Phase)
        for scorer in self.scorers:
            candidates = await scorer.score(query, candidates)
        self._add_trace("多维评分 (Scoring)", after_filter, len(candidates))

        # 6. 最终排序与选择 (Selection Phase)
        selected = self.selector.select(candidates)
        self._add_trace("排序选择 (Selection)", len(candidates), len(selected))
        
        # 将本次执行的完整链路数据挂载到 query 对象，方便上层 Service 提取展示
        query.last_execution_trace = self.trace
        
        return selected
