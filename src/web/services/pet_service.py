from typing import Dict, Any
from src.web.services.db_service import get_db

class PetService:
    """
    宠物信息基础服务
    """
    @staticmethod
    def get_by_id(pet_id: int) -> Dict[str, Any]:
        """通过 ID 获取宠物基础信息"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pets WHERE id = ?", (pet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
