import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.web.services.db_service import get_db
from src.web.services.adoption_flow_engine import flow_engine

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

    @staticmethod
    def create_application(user_id: int, pet_id: int, applicant_data: Dict[str, Any]) -> int:
        """
        创建正式领养申请
        1. 验证宠物存在并获取送养人ID
        2. 序列化评估输入为 assessment_payload
        3. 插入 applications 表
        4. 记录初始流程事件
        """
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 获取宠物信息
            cursor.execute("SELECT owner_id FROM pets WHERE id = ?", (pet_id,))
            pet_row = cursor.fetchone()
            if not pet_row:
                raise ValueError(f"宠物 ID {pet_id} 不存在")
            
            pet_owner_id = pet_row[0]
            
            # 准备数据
            apply_reason = applicant_data.get("application_reason", "")
            assessment_payload = json.dumps(applicant_data, ensure_ascii=False)
            
            # 插入申请
            # 插入申请 (状态统一初始化为 evaluating)
            cursor.execute(
                """
                INSERT INTO applications 
                (user_id, pet_id, pet_owner_id, apply_reason, assessment_payload, status, flow_status)
                VALUES (?, ?, ?, ?, ?, 'evaluating', 'evaluating')
                """,
                (user_id, pet_id, pet_owner_id, apply_reason, assessment_payload)
            )
            application_id = cursor.lastrowid

            # 记录流程事件: submitted
            flow_engine.append_event(
                conn,
                application_id=application_id,
                event_type="SUBMIT_APPLICATION",
                from_status=None,
                to_status="evaluating",
                actor_role="applicant",
                actor_id=user_id,
                payload=applicant_data
            )

            conn.commit()
            return application_id

