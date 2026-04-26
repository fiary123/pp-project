from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

# --- 论文核心逻辑：有限状态自动机 (FSM) 定义 ---
# 严格限制领养评估生命周期的流转路径
FLOW_TRANSITIONS: Dict[str, Set[str]] = {
    "submitted": {"evaluating", "need_more_info", "manual_review", "waiting_publisher"},
    "evaluating": {"need_more_info", "manual_review", "waiting_publisher", "approved", "rejected"},
    "need_more_info": {"evaluating", "manual_review", "waiting_publisher", "rejected"},
    "waiting_publisher": {"approved", "rejected", "need_more_info", "manual_review"},
    "manual_review": {"approved", "rejected", "need_more_info", "waiting_publisher"},
    "approved": {"adopted", "followup_completed"},
    "adopted": {"followup_completed"},
    "rejected": set(),
    "followup_completed": set(),
}

class AdoptionFlowEngine:
    """
    领养评估流程控制引擎 (Thesis Core: Lifecycle Controller)
    实现强约束的状态迁移管理与审计追踪。
    """
    
    def can_transition(self, current_status: str | None, next_status: str) -> bool:
        """校验状态迁移合法性"""
        if not current_status:
            return True # 初始状态允许
        if current_status not in FLOW_TRANSITIONS:
            return False
        return next_status in FLOW_TRANSITIONS[current_status]

    def append_event(
        self,
        conn,
        *,
        application_id: int,
        event_type: str,
        from_status: str | None,
        to_status: str,
        actor_role: str = "",
        actor_id: int | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> None:
        """
        追加流程事件 [强约束版]
        在写入事件库前强制执行 FSM 状态机校验。
        """
        # 1. 执行强约束校验
        if not self.can_transition(from_status, to_status):
            error_msg = f"非法流程拦截：禁止从 {from_status} 直接跳转至 {to_status} (Application: {application_id})"
            logger.error(error_msg)
            
            # 记录违规尝试以便审计 (Layer 5: Audit Feedback)
            conn.execute(
                """
                INSERT INTO adoption_flow_events
                (application_id, event_type, from_status, to_status, actor_role, actor_id, payload_json)
                VALUES (?, 'ILLEGAL_TRANSITION_ATTEMPT', ?, ?, ?, ?, ?)
                """,
                (application_id, from_status or "", to_status, actor_role, actor_id, 
                 json.dumps({"error": error_msg}, ensure_ascii=False))
            )
            raise RuntimeError(error_msg)

        # 2. 校验通过，写入正式流程日志
        conn.execute(
            """
            INSERT INTO adoption_flow_events
            (application_id, event_type, from_status, to_status, actor_role, actor_id, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                event_type,
                from_status or "",
                to_status,
                actor_role,
                actor_id,
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )

    def resolve_review_flow_status(self, review_decision: str) -> str:
        """[测试对齐] 根据送养人/管理员的人工审核决策解析下一个流程节点"""
        return {
            "approved": "approved",
            "rejected": "rejected",
            "probing": "need_more_info",
            "human_review": "manual_review",
        }.get(review_decision, "waiting_publisher")

    def resolve_feedback_flow_status(self, feedback_status: str) -> str:
        """[测试对齐] 根据领养反馈状态解析下一个流程节点"""
        return "followup_completed"

    def resolve_result_flow_status(self, result: dict) -> str:
        """根据 AI Agent 评估结论解析下一个流程节点"""
        route = result.get("route_decision") or {}
        next_action = route.get("next_action")
        mapping = {
            "followup": "need_more_info",
            "manual_review": "manual_review",
            "reject_candidate": "rejected"
        }
        return mapping.get(next_action, "waiting_publisher")

    def resolve_terminal_flow_status(self, status: str) -> str:
        """解析最终归档状态"""
        if status == "approved":
            return "adopted"
        return {
            "rejected": "rejected",
            "probing": "need_more_info",
            "human_review": "manual_review",
        }.get(status, "waiting_publisher")

    def get_timeline(self, conn, application_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """获取可视化时间轴数据"""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, application_id, event_type, from_status, to_status, actor_role, actor_id, payload_json, created_at
            FROM adoption_flow_events
            WHERE application_id=?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (application_id, limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        for item in rows:
            try:
                item["payload"] = json.loads(item.get("payload_json") or "{}")
            except:
                item["payload"] = {}
        return rows

    def rebuild_flow_status(self, conn, application_id: int, fallback_status: str = "submitted") -> str:
        """基于事件回溯机制重建当前状态 (用于系统自愈)"""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT to_status FROM adoption_flow_events WHERE application_id=? AND event_type != 'ILLEGAL_TRANSITION_ATTEMPT' ORDER BY id DESC LIMIT 1",
            (application_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else fallback_status

flow_engine = AdoptionFlowEngine()
