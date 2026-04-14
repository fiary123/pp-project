from typing import List, Dict, Any
from src.web.services.db_service import get_db
from src.web.recommendation.candidate import RecommendationCandidate

class AvailablePetSource:
    """
    推荐系统召回层 - 结构化多策略召回
    基于用户的基本偏好（品种、体型等）从全库筛选出初步候选集。
    """
    def __init__(self, db_conn=None):
        self.db_conn = db_conn

    async def get_candidates(self, query) -> List[RecommendationCandidate]:
        candidates = []
        user_id = query.user_id
        pref = query.user_preferences or {}
        
        # 获取用户偏好品种
        preferred_type = pref.get("preferred_pet_type")
        
        def process_rows(rows):
            for row in rows:
                pet_data = dict(row)
                candidate = RecommendationCandidate(
                    candidate_id=pet_data['id'],
                    candidate_type="pet",
                    raw_data={"pet": pet_data}
                )
                
                # 标记召回策略
                if preferred_type and pet_data.get('type') == preferred_type:
                    candidate.reasons.append(f"命中品种偏好 ({preferred_type})")
                else:
                    candidate.reasons.append("全库活跃召回")
                
                candidates.append(candidate)

        sql = "SELECT * FROM pets WHERE status = '待领养'"
        params = []
        
        # 策略1: 如果用户有极强的品种偏好，可以缩小召回范围 (此处采用宽松策略，优先展示匹配品种，但保留其他)
        # 如果需要硬过滤，可以在此处修改 SQL
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            process_rows(cursor.fetchall())
                
        return candidates
