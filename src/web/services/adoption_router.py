from __future__ import annotations

from typing import Any, Dict


def uncertainty_router(consensus_result: Dict[str, Any], publisher_preferences: Dict[str, Any] | None = None) -> Dict[str, Any]:
    prefs = publisher_preferences or {}
    
    # ── [对齐字段契约] ──────────────────────────────────────────────────
    # 将委员会返回的 readiness_score 映射为路由器的 overall_score
    overall_score = float(consensus_result.get("readiness_score", 0))
    
    # 从 phase2_vote 嵌套结构中提取共识与分歧指标
    vote_data = consensus_result.get("phase2_vote") or {}
    consensus_score = float(vote_data.get("avg_confidence", 0))
    disagreement_score = float(vote_data.get("disagreement", 0))
    
    missing_fields = consensus_result.get("missing_fields") or []
    followup_questions = consensus_result.get("followup_questions") or []
    risk_factors = consensus_result.get("risk_factors") or []
    # ──────────────────────────────────────────────────────────────────

    missing_count = len(missing_fields)
    risk_level = str(consensus_result.get("risk_level") or "Medium")
    conservative = prefs.get("risk_tolerance") == "conservative"
    relaxed = prefs.get("risk_tolerance") == "relaxed"

    reasons = []

    # 1. 拦截逻辑：低分自动驳回
    if overall_score < 45:
        reasons.append("综合准备度评分低于准入红线(45分)")
        return {"next_action": "reject_candidate", "requires_followup": False, "requires_manual_review": False, "route_reason": reasons}

    # 2. [主动追问核心]：决策影响力评估 (Decision-Impact Ranking)
    # ─────────────────────────────────────────────────────────────
    # 如果判定需要追问，我们需要对问题进行重排，将“最能消除分歧或降低风险”的问题置顶。
    
    if missing_count >= 2 or disagreement_score >= 0.28:
        reasons.append("关键信息不完整或专家分歧显著，触发主动追问")
        
        # 提取当前所有风险标签的维度
        risk_dims = [str(r.get("dimension", "")).lower() for r in risk_factors if isinstance(r, dict)]
        
        def calculate_impact(q_text: str) -> float:
            score = 1.0
            q_lower = q_text.lower()
            # 如果问题涉及当前已识别的风险维度，影响力倍增
            if any(dim in q_lower for dim in risk_dims): score += 2.0
            # 涉及物理硬约束 (空间、预算、时间) 的优先级最高
            if any(k in q_lower for k in ["预算", "budget", "空间", "housing", "时间", "time"]): score += 1.5
            return score

        # 对问题进行重排 (降序)
        ranked_questions = sorted(followup_questions, key=calculate_impact, reverse=True)
        
        return {
            "next_action": "followup",
            "requires_followup": True,
            "requires_manual_review": False,
            "route_reason": reasons,
            "prioritized_questions": ranked_questions[:3] # 仅抛出最有价值的前3个问题
        }
    # ─────────────────────────────────────────────────────────────

    # 3. 正常流转逻辑 (略，保持不变)
    if risk_level == "High" and (consensus_score < 0.62 or disagreement_score >= 0.35):
        reasons.append("高风险且共识不足")
        return {"next_action": "manual_review", "requires_followup": False, "requires_manual_review": True, "route_reason": reasons}

    if conservative and risk_level != "Low":
        reasons.append("发布者风险偏好更保守")
        return {"next_action": "manual_review", "requires_followup": False, "requires_manual_review": True, "route_reason": reasons}

    if relaxed and overall_score >= 72 and consensus_score >= 0.68:
        reasons.append("风险偏好较宽松且结果稳定")
        return {"next_action": "publisher_review", "requires_followup": False, "requires_manual_review": False, "route_reason": reasons}

    reasons.append("结果已达到发布者决策条件")
    return {"next_action": "publisher_review", "requires_followup": False, "requires_manual_review": False, "route_reason": reasons}
