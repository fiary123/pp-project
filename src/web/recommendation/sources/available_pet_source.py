from typing import List, Dict, Any
from src.web.services.db_service import get_db
from src.web.recommendation.query import PetCandidate

class AvailablePetSource:
    """
    推荐系统数据源 - 获取所有处于 '待领养' 状态的宠物作为初始候选集
    """
    @staticmethod
    def get_candidates() -> List[PetCandidate]:
        candidates = []
        with get_db() as conn:
            cursor = conn.cursor()
            # 只获取待领养的宠物
            cursor.execute("SELECT * FROM pets WHERE status = '待领养'")
            rows = cursor.fetchall()
            
            for row in rows:
                base_info = dict(row)
                candidates.append(PetCandidate(pet_id=base_info['id'], base_info=base_info))
                
        return candidates
