from __future__ import annotations

from typing import Any, Dict


def uncertainty_router(consensus_result: Dict[str, Any], publisher_preferences: Dict[str, Any] | None = None) -> Dict[str, Any]:
    prefs = publisher_preferences or {}
    missing_count = len(consensus_result.get("missing_fields") or [])
    consensus_score = float(consensus_result.get("consensus_score") or 0)
    disagreement_score = float(consensus_result.get("disagreement_score") or 0)
    overall_score = float(consensus_result.get("overall_score") or 0)
    risk_level = str(consensus_result.get("risk_level") or "Medium")
    conservative = prefs.get("risk_tolerance") == "conservative"
    relaxed = prefs.get("risk_tolerance") == "relaxed"

    reasons = []

    if overall_score < 45:
        reasons.append("综合准备度过低")
        return {
            "next_action": "reject_candidate",
            "requires_followup": False,
            "requires_manual_review": False,
            "route_reason": reasons,
        }

    if risk_level == "High" and (consensus_score < 0.62 or disagreement_score >= 0.35):
        reasons.append("高风险且共识不足")
        return {
            "next_action": "manual_review",
            "requires_followup": False,
            "requires_manual_review": True,
            "route_reason": reasons,
        }

    if missing_count >= 2 or disagreement_score >= 0.28:
        reasons.append("关键信息仍不完整或专家存在分歧")
        return {
            "next_action": "followup",
            "requires_followup": True,
            "requires_manual_review": False,
            "route_reason": reasons,
        }

    if conservative and risk_level != "Low":
        reasons.append("发布者风险偏好更保守")
        return {
            "next_action": "manual_review",
            "requires_followup": False,
            "requires_manual_review": True,
            "route_reason": reasons,
        }

    if relaxed and overall_score >= 72 and consensus_score >= 0.68:
        reasons.append("风险偏好较宽松且结果稳定")
        return {
            "next_action": "publisher_review",
            "requires_followup": False,
            "requires_manual_review": False,
            "route_reason": reasons,
        }

    reasons.append("结果已达到发布者决策条件")
    return {
        "next_action": "publisher_review",
        "requires_followup": False,
        "requires_manual_review": False,
        "route_reason": reasons,
    }
