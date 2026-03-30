from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


CONTRACT_VERSION = "adoption-agent-contract-v1"


def _unique_strings(values: List[Any], limit: int = 8) -> List[str]:
    result: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def clamp_score(value: Any, default: int = 0) -> int:
    try:
        score = int(float(value))
    except Exception:
        score = default
    return max(0, min(100, score))


def normalize_confidence(value: Any, default: float = 0.72) -> float:
    try:
        confidence = float(value)
    except Exception:
        confidence = default
    if confidence > 1:
        confidence = confidence / 100
    return round(max(0.0, min(1.0, confidence)), 2)


class AgentContract(BaseModel):
    agent_name: str
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    risk_tags: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    confidence: float = 0.72
    recommendation: str = "publisher_review"
    evidence: List[str] = Field(default_factory=list)
    score: int = 0


def normalize_agent_contract(raw: Any, fallback_name: str = "UnknownAgent") -> Dict[str, Any]:
    payload = raw if isinstance(raw, dict) else {}
    raw_dimensions = payload.get("dimension_scores") or {}
    dimension_scores: Dict[str, float] = {}
    if isinstance(raw_dimensions, dict):
        for key, value in raw_dimensions.items():
            try:
                dimension_scores[str(key)] = float(value)
            except Exception:
                continue

    contract = AgentContract(
        agent_name=str(payload.get("agent_name") or fallback_name),
        dimension_scores=dimension_scores,
        risk_tags=_unique_strings(list(payload.get("risk_tags") or [])),
        missing_fields=_unique_strings(list(payload.get("missing_fields") or []), limit=6),
        confidence=normalize_confidence(payload.get("confidence"), 0.72),
        recommendation=str(payload.get("recommendation") or "publisher_review"),
        evidence=_unique_strings(list(payload.get("evidence") or []), limit=6),
        score=clamp_score(payload.get("score"), 0),
    )
    return contract.model_dump()


def validate_contract_list(items: Any, fallback_name_prefix: str = "ValidatedAgent") -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    validated: List[Dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        validated.append(normalize_agent_contract(item, f"{fallback_name_prefix}{index}"))
    return validated
