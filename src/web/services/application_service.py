from typing import List, Dict, Any
from src.web.services.db_service import get_db

class ApplicationService:
    """
    领养申请基础服务 - 处理申请记录的增删改查
    """
    @staticmethod
    def list_by_pet_id(pet_id: int) -> List[Dict[str, Any]]:
        """获取指定宠物的所有申请记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applications WHERE pet_id = ?",
                (pet_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(application_id: int) -> Dict[str, Any]:
        """获取单条申请记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applications WHERE id = ?",
                (application_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
            
    @staticmethod
    def update_status(application_id: int, status: str):
        """更新申请状态"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE applications SET status = ? WHERE id = ?",
                (status, application_id)
            )
            conn.commit()
            return True
