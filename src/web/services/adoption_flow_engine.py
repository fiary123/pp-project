from __future__ import annotations

import json
from typing import Any, Dict, List, Set


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
    def resolve_result_flow_status(self, result: dict) -> str:
        route = result.get("route_decision") or {}
        next_action = route.get("next_action")
        if next_action == "followup":
            return "need_more_info"
        if next_action == "manual_review":
            return "manual_review"
        if next_action == "reject_candidate":
            return "rejected"
        return "waiting_publisher"

    def resolve_review_flow_status(self, status: str) -> str:
        return {
            "approved": "approved",
            "rejected": "rejected",
            "probing": "need_more_info",
            "human_review": "manual_review",
        }.get(status, "waiting_publisher")

    def resolve_terminal_flow_status(self, status: str) -> str:
        if status == "approved":
            return "adopted"
        return self.resolve_review_flow_status(status)

    def resolve_feedback_flow_status(self, current_status: str | None = None) -> str:
        if current_status == "adopted":
            return "followup_completed"
        if current_status == "approved":
            return "followup_completed"
        return "followup_completed"

    def can_transition(self, current_status: str | None, next_status: str) -> bool:
        if not current_status or current_status not in FLOW_TRANSITIONS:
            return True
        return next_status in FLOW_TRANSITIONS[current_status]

    def append_event(
        self,
        conn,
        *,
        application_id: int,
        event_type: str,
        from_status: str | None,
        to_status: str | None,
        actor_role: str = "",
        actor_id: int | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> None:
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
                to_status or "",
                actor_role,
                actor_id,
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )

    def get_timeline(self, conn, application_id: int, limit: int = 20) -> List[Dict[str, Any]]:
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
            raw_payload = item.get("payload_json")
            try:
                item["payload"] = json.loads(raw_payload) if raw_payload else {}
            except Exception:
                item["payload"] = {}
        return rows

    def rebuild_flow_status(self, conn, application_id: int, fallback_status: str = "submitted") -> str:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT to_status
            FROM adoption_flow_events
            WHERE application_id=? AND to_status IS NOT NULL AND TRIM(to_status) != ''
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (application_id,),
        )
        row = cursor.fetchone()
        return row["to_status"] if row and row["to_status"] else fallback_status


flow_engine = AdoptionFlowEngine()
