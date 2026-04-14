from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class RecommendationCandidate:
    candidate_id: int
    candidate_type: str  # pet / applicant
    raw_data: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    stage_trace: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"<RecommendationCandidate(id={self.candidate_id}, type={self.candidate_type}, score={self.final_score})>"
