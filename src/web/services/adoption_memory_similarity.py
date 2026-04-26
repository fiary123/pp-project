    def _calculate_hybrid_similarity(self, current: Dict[str, Any], case: Dict[str, Any]) -> float:
        """
        [创新点：混合相似度算法]：
        计算 (结构化特征分 * 0.4) + (风险标签分 * 0.3) + (语义关键词分 * 0.3)
        """
        # 1. 结构化特征分 (0.4)
        struct_score = 0.0
        try:
            hist_feats = json.loads(case.get("feature_snapshot_json") or "{}")
            if hist_feats:
                # 预算相似度 (归一化距离)
                curr_b = float(current.get("monthly_budget", 500))
                hist_b = float(hist_feats.get("monthly_budget", 500))
                budget_sim = 1.0 - min(1.0, abs(curr_b - hist_b) / max(curr_b, hist_b, 1))
                
                # 经验相似度 (布尔匹配)
                curr_e = bool(current.get("has_pet_experience", False))
                hist_e = bool(hist_feats.get("has_pet_experience", False))
                exp_sim = 1.0 if curr_e == hist_e else 0.5
                
                # 陪伴时间相似度
                curr_t = float(current.get("daily_companion_hours", 2))
                hist_t = float(hist_feats.get("daily_companion_hours", 2))
                time_sim = 1.0 - min(1.0, abs(curr_t - hist_t) / max(curr_t, hist_t, 1))
                
                struct_score = (budget_sim + exp_sim + time_sim) / 3.0
            else:
                struct_score = 0.5
        except: 
            struct_score = 0.5

        # 2. 风险标签分 (0.3) - Jaccard Similarity
        tag_score = 0.0
        try:
            # 尝试从当前数据中获取初步识别的风险 (如果有)
            curr_tags = set(current.get("risk_tags", []))
            hist_tags = set(json.loads(case.get("risk_tags_json") or "[]"))
            if not curr_tags and not hist_tags:
                tag_score = 1.0
            elif not curr_tags or not hist_tags:
                tag_score = 0.4
            else:
                intersection = curr_tags.intersection(hist_tags)
                union = curr_tags.union(hist_tags)
                tag_score = len(intersection) / len(union)
        except: 
            tag_score = 0.0

        # 3. 语义关键词分 (0.3)
        text_score = 0.0
        try:
            text_current = str(current.get("application_reason", "")).lower()
            text_case = str(case.get("case_summary", "")).lower()
            
            # 简单关键词提取模拟 (过滤短词)
            kw_curr = set([w for w in text_current.replace("，", " ").split() if len(w) > 1])
            kw_case = set([w for w in text_case.replace("，", " ").split() if len(w) > 1])
            
            if kw_curr and kw_case:
                text_score = len(kw_curr.intersection(kw_case)) / len(kw_curr.union(kw_case))
            else:
                # 降级到字符级匹配
                c_curr, c_case = set(text_current), set(text_case)
                if c_curr and c_case:
                    text_score = len(c_curr.intersection(c_case)) / len(c_curr.union(c_case))
        except: 
            text_score = 0.0

        # 4. 决策价值加权
        val_weight = 1.2 if case.get("owner_followed_ai") == 1 else 1.0

        final_score = (0.4 * struct_score + 0.3 * tag_score + 0.3 * text_score) * val_weight
        return round(min(1.0, final_score), 4)
