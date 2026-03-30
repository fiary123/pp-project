from __future__ import annotations

from typing import Any, Dict, List


def clamp_score(score: float) -> int:
    return int(max(0, min(100, round(score))))


def unique_list(values: List[str]) -> List[str]:
    result: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def fuse_consensus(
    *,
    rule_result: Dict[str, Any],
    ai_result: Dict[str, Any],
    dimension_scores: List[Dict[str, Any]],
    missing_fields: List[str],
    conflict_notes: List[str],
    risk_level: str,
) -> Dict[str, Any]:
    average_dimension_score = clamp_score(
        sum(item.get("score", 0) for item in dimension_scores) / max(1, len(dimension_scores))
    )
    base_score = clamp_score(rule_result.get("base_score", 60))
    ai_score = clamp_score(ai_result.get("readiness_score", average_dimension_score))
    overall_score = clamp_score(base_score * 0.15 + ai_score * 0.45 + average_dimension_score * 0.40)

    signal_scores = [base_score, ai_score, average_dimension_score]
    disagreement_score = round((max(signal_scores) - min(signal_scores)) / 100, 2)
    raw_confidence = ai_result.get("confidence_level", 0.75)
    raw_confidence = float(raw_confidence if raw_confidence is not None else 0.75)
    confidence = raw_confidence if raw_confidence <= 1 else raw_confidence / 100
    consensus_score = round(max(0.0, min(1.0, (1 - disagreement_score) * 0.6 + confidence * 0.4)), 2)

    risk_tags: List[str] = []
    for factor in ai_result.get("risk_factors", []) or []:
        if isinstance(factor, dict):
            label = factor.get("dimension") or factor.get("description") or ""
            if label:
                risk_tags.append(str(label))

    for dimension in dimension_scores:
        if dimension.get("risk_level") in ("Medium", "High"):
            risk_tags.append(str(dimension.get("key") or dimension.get("label") or ""))

    if missing_fields:
        risk_tags.append("information_gap")
    if conflict_notes:
        risk_tags.append("expert_conflict")

    return {
        "overall_score": overall_score,
        "consensus_score": consensus_score,
        "disagreement_score": disagreement_score,
        "risk_level": risk_level,
        "risk_tags": unique_list(risk_tags)[:8],
        "missing_fields": unique_list(missing_fields)[:6],
        "signal_scores": {
            "rule_score": base_score,
            "ai_score": ai_score,
            "dimension_score": average_dimension_score,
        },
    }
