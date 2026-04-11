from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class RecommendationQuery:
    user_id: int
    scene: str = "pet_for_user"
    pet_id: Optional[int] = None
    user_profile: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
