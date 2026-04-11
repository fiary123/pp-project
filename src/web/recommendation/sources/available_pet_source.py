from typing import List, Dict, Any
from src.web.services.db_service import get_db
from src.web.recommendation.candidate import RecommendationCandidate

class AvailablePetSource:
    """
    推荐系统数据源 - 获取所有处于 '待领养' 状态的宠物作为初始候选集
    """
    def __init__(self, db_conn=None):
        # 允许外部传入连接（用于事务或测试）
        self.db_conn = db_conn

    async def get_candidates(self, query) -> List[RecommendationCandidate]:
        candidates = []
        
        # 内部获取连接或使用外部传入
        conn = self.db_conn if self.db_conn else None
        
        def process_rows(rows):
            for row in rows:
                pet_data = dict(row)
                candidates.append(RecommendationCandidate(
                    candidate_id=pet_data['id'],
                    candidate_type="pet",
                    raw_data={"pet": pet_data}
                ))

        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pets WHERE status = '待领养'")
            process_rows(cursor.fetchall())
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM pets WHERE status = '待领养'")
                process_rows(cursor.fetchall())
                
        return candidates
