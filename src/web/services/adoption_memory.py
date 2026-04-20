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
) -> Dict[str, float]:
    """
    兼容 assessment_service 的后验信号权重入口。
    """
    risk_penalties = {
        "hard_rule_block": -0.8,
        "budget_risk": -0.45,
        "time_risk": -0.45,
        "housing_risk": -0.35,
        "medical_risk": -0.3,
        "fallback_response": -0.2,
        "information_gap": -0.15,
    }
    route_weights = {
        "reject_candidate": -0.8,
        "manual_review": -0.4,
        "followup": 0.25,
        "publisher_review": 0.1,
    }

    risk_values = [risk_penalties.get(str(tag), 0.0) for tag in (risk_tags or [])]
    average_risk_weight = round(sum(risk_values) / len(risk_values), 3) if risk_values else 0.0

    followup_count = len(followup_questions or [])
    average_followup_weight = round(min(0.6, followup_count * 0.15), 3) if followup_count else 0.0

    return {
        "average_risk_weight": average_risk_weight,
        "average_followup_weight": average_followup_weight,
        "route_weight": round(route_weights.get(route_decision or "", 0.0), 3),
    }


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
                # 修复：移除不存在的 user_id 和 feature_snapshot_json 字段
                cursor.execute("""
                    SELECT id, application_id, case_summary, decision_result, 
                           owner_followed_ai, risk_tags_json
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
        """混合相似度算法：0.6 * 结构化分 + 0.4 * 文本语义分"""
        
        # A. 结构化特征分 (Numerical Similarity)
        # 暂时由于 feature_snapshot_json 字段缺失，我们主要依赖文本相似度和风险标签重合度
        risk_tags = json.loads(case.get("risk_tags_json") or "[]")
        
        # 基础分
        struct_score = 0.5
        
        # B. 文本语义分 (Keyword Overlap)
        text_current = set(str(current.get("application_reason", "") + current.get("applicant_info", "")))
        text_case = set(case.get("case_summary", ""))
        
        if not text_current or not text_case:
            text_score = 0.0
        else:
            intersection = text_current.intersection(text_case)
            union = text_current.union(text_case)
            text_score = len(intersection) / len(union)

        # C. 决策价值加权
        val_weight = 1.2 if case.get("owner_followed_ai") == 1 else 1.0

        return (0.6 * struct_score + 0.4 * text_score) * val_weight

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


def update_signal_weights_from_feedback(
    application_id: int,
    overall_satisfaction: int,
    route_decision: str = "",
    risk_tags: Optional[List[str]] = None,
):
    """
    [后验学习核心] 根据真实回访结果，动态修正模型对风险信号的权重认知。
    满意度 >= 4 视为正向案例，<= 2 视为负向案例。
    """
    is_positive = overall_satisfaction >= 4
    is_negative = overall_satisfaction <= 2
    
    if not is_positive and not is_negative:
        return # 中性反馈不影响权重修正

    delta_pos = 1 if is_positive else 0
    delta_neg = 1 if is_negative else 0

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. 如果未传入 tags，自动从 ai_review 快照中补齐
            if risk_tags is None:
                cursor.execute(
                    "SELECT consensus_result_json FROM adoption_ai_reviews WHERE application_id = ? ORDER BY id DESC LIMIT 1",
                    (application_id,)
                )
                row = cursor.fetchone()
                if row:
                    try:
                        res = json.loads(row[0])
                        risk_tags = res.get("risk_tags", [])
                        if not route_decision:
                            route_decision = res.get("next_action", "")
                    except: risk_tags = []

            # 2. 更新路径决策的后验表现
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
                    cursor.execute("""
                        INSERT INTO adoption_signal_weights (signal_type, signal_key, positive_count, negative_count, updated_at)
                        VALUES ('risk_tag', ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(signal_type, signal_key) DO UPDATE SET
                            positive_count = positive_count + excluded.positive_count,
                            negative_count = negative_count + excluded.negative_count,
                            updated_at = CURRENT_TIMESTAMP
                    """, (tag, delta_pos, delta_neg))

            # 4. 同步更新案例记忆库结局
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
