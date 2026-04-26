import json
import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.web.services.db_service import get_db

logger = logging.getLogger(__name__)

# ==========================================
# 1. 模块级工具函数 (提前定义以防循环引用导入失败)
# ==========================================

def build_case_summary(application_row: Dict[str, Any], assessment_result: Dict[str, Any]) -> str:
    """
    兼容旧流程的案例摘要构造函数。
    """
    pet_name = application_row.get("pet_name") or application_row.get("target_pet_name") or "未命名宠物"
    decision = assessment_result.get("decision") or assessment_result.get("final_decision") or application_row.get("status") or "unknown"
    score = assessment_result.get("readiness_score") or assessment_result.get("score") or application_row.get("ai_readiness_score") or 0
    risk_level = assessment_result.get("risk_level") or application_row.get("risk_level") or "Unknown"
    apply_reason = application_row.get("apply_reason") or application_row.get("application_reason") or ""
    summary_bits = [
        f"宠物：{pet_name}",
        f"结论：{decision}",
        f"综合分：{score}",
        f"风险等级：{risk_level}",
    ]
    if apply_reason:
        summary_bits.append(f"申请理由：{str(apply_reason)[:60]}")
    return " | ".join(summary_bits)


def collect_posterior_signal_weights(
    route_decision: str,
    risk_tags: List[str],
    followup_questions: List[str],
) -> Dict[str, Any]:
    """
    [后验驱动评估]：从数据库加载经过真实反馈修正后的动态权重。
    """
    # 基础硬编码兜底
    base_penalties = {
        "hard_rule_block": -0.8, "budget_risk": -0.45, "time_risk": -0.45,
        "housing_risk": -0.35, "medical_risk": -0.3, "information_gap": -0.15,
    }
    base_routes = {
        "reject_candidate": -0.8, "manual_review": -0.4, "followup": 0.25, "publisher_review": 0.1,
    }

    dynamic_weights: Dict[str, Dict[str, float]] = {
        "risk_tag": {}, "route_decision": {}, "followup_question": {}
    }

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # 加载所有已学习的修正信号 (Layer 4: Self-correction)
            cursor.execute("SELECT signal_type, signal_key, positive_count, negative_count FROM adoption_signal_weights")
            for row in cursor.fetchall():
                stype, skey, pos, neg = row
                if stype in dynamic_weights:
                    # 计算偏移量：每个负面反馈降低权重，每个正面反馈提升权重
                    # 加大负面惩罚力度 (0.2) 以确保闭环纠偏灵敏度
                    offset = (pos * 0.05) - (neg * 0.2)
                    dynamic_weights[stype][skey] = offset

            # 1. 计算决策路径得分
            route_val = base_routes.get(route_decision, 0.0)
            route_val += dynamic_weights["route_decision"].get(route_decision, 0.0)

            # 2. 计算风险标签总分 (平均值)
            risk_vals = []
            for tag in (risk_tags or []):
                val = base_penalties.get(tag, 0.0)
                val += dynamic_weights["risk_tag"].get(tag, 0.0)
                risk_vals.append(val)
            
            # 3. 计算追问项权重
            follow_vals = {}
            for q in (followup_questions or []):
                val = 0.15 # 基础贡献度
                val += dynamic_weights["followup_question"].get(q, 0.0)
                follow_vals[q] = round(val, 3)

            return {
                "route_weight": round(route_val, 3),
                "average_risk_weight": round(sum(risk_vals)/len(risk_vals), 3) if risk_vals else 0.0,
                "risk_tag_weights": {t: (base_penalties.get(t,0.0) + dynamic_weights["risk_tag"].get(t,0.0)) for t in (risk_tags or [])},
                "followup_weights": follow_vals
            }
    except Exception as exc:
        logger.error(f"collect_posterior_signal_weights failed: {exc}")
        return {"route_weight": 0.0, "average_risk_weight": 0.0, "risk_tag_weights": {}, "followup_weights": {}}


def build_closed_loop_stats() -> Dict[str, Any]:
    """
    构建闭环评估统计数据 (Thesis Core: Performance Monitoring)
    供管理后台仪表盘使用。
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # 1. 核心看板指标：总评估、平均分、人机一致率
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_reviews,
                    AVG(overall_score) as avg_score,
                    AVG(CASE WHEN owner_followed_ai = 1 THEN 1.0 ELSE 0.0 END) as consistency_rate
                FROM adoption_ai_reviews
            """)
            row = cursor.fetchone()
            
            # 2. 风险分布统计
            cursor.execute("SELECT risk_level, COUNT(*) as cnt FROM adoption_ai_reviews GROUP BY risk_level")
            risks = {r["risk_level"]: r["cnt"] for r in cursor.fetchall()}

            # 3. 后验学习信号热力：统计预测最“准”的风险标签 (正向/负向比)
            cursor.execute("""
                SELECT signal_key, positive_count, negative_count,
                       (CAST(positive_count AS FLOAT) / (positive_count + negative_count + 0.1)) as confidence
                FROM adoption_signal_weights
                WHERE signal_type = 'risk_tag'
                ORDER BY (positive_count + negative_count) DESC
                LIMIT 10
            """)
            signal_heatmap = [dict(r) for r in cursor.fetchall()]

            # 4. 最近审计轨迹性能
            cursor.execute("SELECT AVG(latency_ms) FROM agent_trace_logs WHERE endpoint='adoption_assessment'")
            avg_latency = cursor.fetchone()[0] or 0

            return {
                "total_ai_reviews": row["total_reviews"] if row else 0,
                "avg_ai_score": round(row["avg_score"] or 0, 2) if row else 0,
                "human_ai_consistency": round((row["consistency_rate"] or 0) * 100, 1) if row else 0,
                "risk_distribution": risks,
                "signal_heatmap": signal_heatmap,
                "avg_audit_latency": round(avg_latency, 0)
            }
    except Exception as exc:
        logger.error(f"build_closed_loop_stats failed: {exc}")
        return {}


# ==========================================
# 2. 核心服务类
# ==========================================

class AdoptionMemoryService:
    """
    语义案例记忆服务 (Thesis Core: Memory Augmentation)
    实现基于“结构化特征匹配 + 关键词权重”的混合案例检索。
    """

    def retrieve_similar_cases(self, current_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """
        [主线 2 增强]：执行混合相似度检索
        """
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                # 1. 获取候选集 (召回最近的活跃案例)
                # 统一字段名：增加 feature_snapshot_json 以支持结构化特征匹配
                cursor.execute("""
                    SELECT id, application_id, case_summary, decision_result, 
                           owner_followed_ai, risk_tags_json, feature_snapshot_json
                    FROM adoption_case_memory 
                    ORDER BY id DESC LIMIT 50
                """)
                candidates = [dict(row) for row in cursor.fetchall()]

            if not candidates:
                return []

            # 2. 多维相似度评分
            scored_cases = []
            for case in candidates:
                score = self._calculate_hybrid_similarity(current_data, case)
                case["similarity_score"] = score
                scored_cases.append(case)

            # 3. 排序并截断
            scored_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # 仅保留高价值记忆
            top_cases = [c for c in scored_cases if c["similarity_score"] > 0.3]
            return top_cases[:limit]
        except Exception as e:
            logger.warning(f"retrieve_similar_cases error: {e}")
            return []

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
        # 送养人采纳了 AI 建议的案例具备更高参考价值
        val_weight = 1.2 if case.get("owner_followed_ai") == 1 else 1.0

        final_score = (0.4 * struct_score + 0.3 * tag_score + 0.3 * text_score) * val_weight
        return round(min(1.0, final_score), 4)

    def upsert_case_memory(self, application_id: int, **kwargs):
        """存入评估快照与特征向量(模拟)"""
        with get_db() as conn:
            # 提取结构化特征以供后续精准匹配
            feature_snapshot = {
                "monthly_budget": kwargs.get("monthly_budget", 0),
                "housing_size": kwargs.get("housing_size", 0),
                "has_pet_experience": kwargs.get("has_pet_experience", False)
            }
            
            conn.execute("""
                INSERT INTO adoption_case_memory 
                (application_id, case_summary, decision_result, owner_followed_ai, 
                 feature_snapshot_json, risk_tags_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(application_id) DO UPDATE SET
                    case_summary=excluded.case_summary,
                    decision_result=excluded.decision_result,
                    owner_followed_ai=excluded.owner_followed_ai,
                    feature_snapshot_json=excluded.feature_snapshot_json,
                    risk_tags_json=excluded.risk_tags_json,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                application_id, kwargs.get("case_summary"),
                kwargs.get("decision_result"), kwargs.get("owner_followed_ai"),
                json.dumps(feature_snapshot, ensure_ascii=False),
                json.dumps(kwargs.get("risk_tags", []), ensure_ascii=False)
            ))
            conn.commit()

memory_service = AdoptionMemoryService()


# ==========================================
# 3. 外部导出入口
# ==========================================

def build_case_anchor_context(similar_cases: List[Dict[str, Any]], memory_signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    [核心增强] 构建判例锚点上下文。
    将相似案例转化为具有“判例效力”的文本，强制 AI 基于历史事实进行决策。
    """
    if not similar_cases:
        return {
            "case_anchor_text": "暂无相似历史判例参考，请基于专业知识进行独立评估。",
            "case_signal": {
                "positive_count": 0,
                "negative_count": 0,
                "average_similarity": 0,
                "signal_summary": "无锚点参考"
            }
        }

    # 计算平均相似度
    sim_scores = [float(c.get('similarity_score', 0)) for c in similar_cases]
    avg_sim = sum(sim_scores) / len(sim_scores) if sim_scores else 0
    
    pos_count = memory_signal.get("positive_count", 0)
    neg_count = memory_signal.get("negative_count", 0)
    
    header = (
        f"【历史判例锚点 (Case-based Anchoring)】\n"
        f"共检索到 {len(similar_cases)} 个历史相似案例，平均相似度 {avg_sim:.2f}。\n"
        f"其中正向结果 (Approved/Success) {pos_count} 个，负向结果 (Rejected/Failed) {neg_count} 个。\n\n"
    )
    
    case_details = []
    for i, case in enumerate(similar_cases, 1):
        outcome = case.get('decision_result', 'pending')
        sim = float(case.get('similarity_score', 0))
        summary = case.get('case_summary', '无摘要')[:100]
        case_details.append(
            f"案例 {i}：相似度 {sim:.2f}，结果 {outcome}\n"
            f"   摘要：{summary}..."
        )
    
    footer = (
        "\n请对比当前申请与上述案例的关键差异：\n"
        "1. 是否具备成功案例中的核心特质？\n"
        "2. 是否重蹈了失败案例中的覆辙？\n"
        "不得仅凭主观印象给分，必须基于上述锚点进行逻辑推演。"
    )
    
    anchor_text = header + "\n".join(case_details) + footer
    
    return {
        "case_anchor_text": anchor_text,
        "case_signal": {
            "positive_count": pos_count,
            "negative_count": neg_count,
            "average_similarity": round(avg_sim, 2),
            "signal_summary": memory_signal.get("signal_summary", "")
        }
    }


def retrieve_similar_case_memories(current_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """
    兼容 assessment_service 的模块级检索入口。
    """
    try:
        return memory_service.retrieve_similar_cases(current_data=current_data, limit=limit)
    except Exception as exc:
        logger.warning("retrieve_similar_case_memories failed: %s", exc)
        return []


def summarize_case_feedback_signal(similar_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    汇总相似案例的反馈信号，供评估流程做解释增强。
    """
    if not similar_cases:
        return {
            "case_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "followed_ai_count": 0,
            "average_similarity": 0.0,
            "signal_summary": "暂无可参考的历史相似案例",
        }

    positive_results = {"approved", "pass", "conditional_pass", "success"}
    negative_results = {"rejected", "reject", "reject_candidate", "failed"}

    positive_count = 0
    negative_count = 0
    followed_ai_count = 0
    similarity_scores: List[float] = []

    for case in similar_cases:
        decision = str(case.get("decision_result") or "").lower()
        if decision in positive_results:
            positive_count += 1
        elif decision in negative_results:
            negative_count += 1

        if case.get("owner_followed_ai") == 1:
            followed_ai_count += 1

        try:
            similarity_scores.append(float(case.get("similarity_score") or 0.0))
        except Exception:
            similarity_scores.append(0.0)

    average_similarity = round(sum(similarity_scores) / len(similarity_scores), 3) if similarity_scores else 0.0
    if positive_count > negative_count:
        signal_summary = "历史相似案例整体结果偏正向，可作为辅助参考"
    elif negative_count > positive_count:
        signal_summary = "历史相似案例中负向结果较多，建议提高人工核验强度"
    else:
        signal_summary = "历史相似案例结果分布接近，建议结合当前个体条件判断"

    return {
        "case_count": len(similar_cases),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "followed_ai_count": followed_ai_count,
        "average_similarity": average_similarity,
        "signal_summary": signal_summary,
    }


def upsert_case_memory(application_id: int, **kwargs):
    """
    兼容旧流程的模块级 upsert 入口。
    """
    try:
        return memory_service.upsert_case_memory(application_id=application_id, **kwargs)
    except Exception as exc:
        logger.warning("upsert_case_memory failed: %s", exc)
        return None


def persist_ai_review(
    application_id: int,
    trace_id: str = "",
    agent_outputs: Optional[List[Dict[str, Any]]] = None,
    consensus_result: Optional[Dict[str, Any]] = None,
    route_decision: str = "",
    overall_score: float = 0.0,
    consensus_score: float = 0.0,
    disagreement_score: float = 0.0,
    risk_level: str = "Medium",
):
    """
    持久化 AI 审核快照。
    """
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO adoption_ai_reviews
                (application_id, trace_id, agent_outputs_json, consensus_result_json, route_decision,
                 overall_score, consensus_score, disagreement_score, risk_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    application_id,
                    trace_id,
                    json.dumps(agent_outputs or [], ensure_ascii=False),
                    json.dumps(consensus_result or {}, ensure_ascii=False),
                    route_decision,
                    overall_score,
                    consensus_score,
                    disagreement_score,
                    risk_level,
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("persist_ai_review failed: %s", exc)


def persist_followup_records(application_id: int, followups: Optional[List[Dict[str, Any]]] = None):
    """
    批量写入追问记录。
    """
    if not followups:
        return
    try:
        with get_db() as conn:
            for item in followups:
                conn.execute(
                    """
                    INSERT INTO adoption_followups
                    (application_id, question, answer, source, impact_score, trace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        application_id,
                        item.get("question", ""),
                        item.get("answer", ""),
                        item.get("source", "applicant"),
                        float(item.get("impact_score", 0.0) or 0.0),
                        item.get("trace_id", ""),
                    ),
                )
            conn.commit()
    except Exception as exc:
        logger.warning("persist_followup_records failed: %s", exc)


def update_publisher_implicit_prefs(
    publisher_id: int,
    applicant_features: Dict[str, Any],
    decision: str  # 'approved' or 'rejected'
):
    """
    [创新点：隐性偏好学习] 从送养人的历史决策中学习其真实的“审美”偏好。
    """
    is_positive = decision == 'approved'
    delta = 0.1 if is_positive else -0.1
    
    # 提取核心信号
    signals = []
    if applicant_features.get("pet_experience") and applicant_features["pet_experience"] != "无":
        signals.append("has_pet_experience")
    if applicant_features.get("housing_type") == "自有住房":
        signals.append("housing_stability")
    if float(applicant_features.get("available_time", 0)) >= 4:
        signals.append("high_companionship")
    if applicant_features.get("budget_level") == "高":
        signals.append("financial_strength")

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            for signal in signals:
                # 记录信号频率并更新权重
                cursor.execute("""
                    INSERT INTO publisher_implicit_preferences (publisher_id, signal_key, positive_count, negative_count, current_weight)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(publisher_id, signal_key) DO UPDATE SET
                        positive_count = positive_count + ?,
                        negative_count = negative_count + ?,
                        current_weight = MAX(0.5, MIN(2.0, current_weight + ?)),
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    publisher_id, signal, 1 if is_positive else 0, 0 if is_positive else 1, 1.0 + delta,
                    1 if is_positive else 0, 0 if is_positive else 1, delta
                ))
            conn.commit()
            logger.info(f"Implicit preferences updated for Publisher:{publisher_id}")
    except Exception as e:
        logger.error(f"update_publisher_implicit_prefs failed: {e}")


def update_signal_weights_from_feedback(
    application_id: int,
    overall_satisfaction: int,
    route_decision: str = "",
    risk_tags: Optional[List[str]] = None,
    would_recommend: bool = True,
    followup_questions: Optional[List[str]] = None,
):
    """
    [后验学习核心] 根据真实回访结果，动态修正模型对风险信号的权重认知。
    - 满意度 >= 4 且 愿意推荐 视为显著正向案例。
    - 满意度 <= 2 视为显著负向案例。
    """
    is_positive = overall_satisfaction >= 4 and would_recommend
    is_negative = overall_satisfaction <= 2
    
    if not is_positive and not is_negative:
        return # 中性反馈不影响权重修正

    delta_pos = 1 if is_positive else 0
    delta_neg = 1 if is_negative else 0

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. 如果未传入 tags 或 decision，自动从 ai_review 快照中补齐
            if risk_tags is None or not route_decision:
                cursor.execute(
                    "SELECT agent_outputs_json FROM adoption_ai_reviews WHERE application_id = ? ORDER BY id DESC LIMIT 1",
                    (application_id,)
                )
                row = cursor.fetchone()
                if row:
                    try:
                        res = json.loads(row[0])
                        if risk_tags is None:
                            # 尝试从 risk_factors 中提取标签
                            factors = res.get("risk_factors", [])
                            risk_tags = [f.get("dimension") for f in factors if isinstance(f, dict)] if factors else []
                        if not route_decision:
                            route_decision = res.get("decision", "")
                    except: 
                        risk_tags = risk_tags or []

            # 2. 更新路径决策的后验表现 (例如：通过、人工复核等决策的可靠性)
            if route_decision:
                cursor.execute("""
                    INSERT INTO adoption_signal_weights (signal_type, signal_key, positive_count, negative_count, updated_at)
                    VALUES ('route_decision', ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(signal_type, signal_key) DO UPDATE SET
                        positive_count = positive_count + excluded.positive_count,
                        negative_count = negative_count + excluded.negative_count,
                        updated_at = CURRENT_TIMESTAMP
                """, (route_decision, delta_pos, delta_neg))

            # 3. 更新各个风险标签的真实风险抵扣度
            if risk_tags:
                for tag in risk_tags:
                    if not tag: continue
                    cursor.execute("""
                        INSERT INTO adoption_signal_weights (signal_type, signal_key, positive_count, negative_count, updated_at)
                        VALUES ('risk_tag', ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(signal_type, signal_key) DO UPDATE SET
                            positive_count = positive_count + excluded.positive_count,
                            negative_count = negative_count + excluded.negative_count,
                            updated_at = CURRENT_TIMESTAMP
                    """, (tag, delta_pos, delta_neg))

            # 4. 更新追问项的有效性 (如果有补充)
            if followup_questions:
                for q in followup_questions:
                    if not q: continue
                    cursor.execute("""
                        INSERT INTO adoption_signal_weights (signal_type, signal_key, positive_count, negative_count, updated_at)
                        VALUES ('followup_question', ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(signal_type, signal_key) DO UPDATE SET
                            positive_count = positive_count + excluded.positive_count,
                            negative_count = negative_count + excluded.negative_count,
                            updated_at = CURRENT_TIMESTAMP
                    """, (q, delta_pos, delta_neg))

            # 5. 同步更新案例记忆库结局
            cursor.execute("""
                UPDATE adoption_case_memory 
                SET decision_result = ?, 
                    owner_followed_ai = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE application_id = ?
            """, ("success" if is_positive else "failed", application_id))
            
            conn.commit()
            logger.info(f"Closed-loop feedback processed for App:{application_id}, Positive:{is_positive}")
    except Exception as exc:
        logger.error(f"update_signal_weights_from_feedback failed: {exc}")
