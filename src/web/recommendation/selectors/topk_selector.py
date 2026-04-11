class TopKSelector:
    """
    结果选择器 - 根据分数排序并截取 Top-K 结果
    """
    def __init__(self, k=5):
        self.k = k

    def select(self, candidates):
        # 按 final_score 降序排列
        ranked = sorted(candidates, key=lambda x: x.final_score, reverse=True)
        # 返回前 K 个
        return ranked[: self.k]
