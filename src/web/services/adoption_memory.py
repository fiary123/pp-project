from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List

from src.web.services.db_service import get_db, ensure_tables


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def sync_publisher_preferences(publisher_id: int | None, pet_id: int | None, preferences: Dict[str, Any] | None):
    if not publisher_id or not pet_id or not preferences:
        return
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO publisher_preferences
            (publisher_id, pet_id, hard_constraints_json, soft_preferences_json, risk_tolerance, raw_preferences_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(publisher_id, pet_id) DO UPDATE SET
                hard_constraints_json=excluded.hard_constraints_json,
                soft_preferences_json=excluded.soft_preferences_json,
                risk_tolerance=excluded.risk_tolerance,
                raw_preferences_json=excluded.raw_preferences_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                publisher_id,
                pet_id,
                _json_text(preferences.get("hard_preferences", [])),
                _json_text(preferences.get("soft_preferences", [])),
                preferences.get("risk_tolerance", "medium"),
                _json_text(preferences),
            ),
        )
        conn.commit()


def persist_ai_review(application_id: int, result: Dict[str, Any]):
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO adoption_ai_reviews
            (application_id, trace_id, agent_outputs_json, consensus_result_json, route_decision, overall_score, consensus_score, disagreement_score, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                result.get("trace_id", ""),
                _json_text(result.get("agent_outputs", [])),
                _json_text(result.get("consensus_result", {})),
                (result.get("route_decision") or {}).get("next_action", ""),
                result.get("readiness_score"),
                (result.get("consensus_result") or {}).get("consensus_score"),
                (result.get("consensus_result") or {}).get("disagreement_score"),
                result.get("risk_level", "Medium"),
            ),
        )
        conn.commit()


def persist_followup_records(application_id: int, questions: Iterable[str], answer: str, source: str = "applicant"):
    rows = [q for q in questions if str(q or "").strip()]
    if not rows and answer.strip():
        rows = ["补充说明"]
    if not rows:
        return
    with get_db() as conn:
        ensure_tables(conn)
        conn.executemany(
            """
            INSERT INTO adoption_followups (application_id, question, answer, source, impact_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(application_id, question, answer.strip(), source, 0.5) for question in rows],
        )
        conn.commit()


def upsert_case_memory(
    *,
    application_id: int,
    case_summary: str,
    decision_result: str = "",
    owner_followed_ai: int | None = None,
    followup_outcome: str = "",
    risk_tags: list[str] | None = None,
    feedback_id: int | None = None,
    embedding_status: str = "pending",
):
    with get_db() as conn:
        ensure_tables(conn)
        conn.execute(
            """
            INSERT INTO adoption_case_memory
            (application_id, case_summary, decision_result, owner_followed_ai, followup_outcome, risk_tags_json, feedback_id, embedding_status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(application_id) DO UPDATE SET
                case_summary=excluded.case_summary,
                decision_result=excluded.decision_result,
                owner_followed_ai=excluded.owner_followed_ai,
                followup_outcome=excluded.followup_outcome,
                risk_tags_json=excluded.risk_tags_json,
                feedback_id=excluded.feedback_id,
                embedding_status=excluded.embedding_status,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                application_id,
                case_summary,
                decision_result,
                owner_followed_ai,
                followup_outcome,
                _json_text(risk_tags or []),
                feedback_id,
                embedding_status,
            ),
        )
        conn.commit()


def build_case_summary(application_row: Dict[str, Any], result: Dict[str, Any] | None = None, feedback_summary: str = "") -> str:
    risk_level = (result or {}).get("risk_level") or application_row.get("risk_level") or "Medium"
    readiness = (result or {}).get("readiness_score") or application_row.get("ai_readiness_score") or 0
    decision = (result or {}).get("decision") or application_row.get("status") or application_row.get("ai_decision") or "pending"
    pet_name = application_row.get("pet_name") or f"宠物{application_row.get('pet_id', '')}"
    applicant = application_row.get("apply_reason") or "申请人提交了领养申请"
    summary = (
        f"宠物：{pet_name}；综合评分：{readiness}；风险等级：{risk_level}；"
        f"当前决策：{decision}；申请概述：{str(applicant)[:160]}"
    )
    if feedback_summary:
        summary += f"；回访：{feedback_summary[:160]}"
    return summary


def _keyword_tokens(*parts: str) -> List[str]:
    tokens: List[str] = []
    for part in parts:
        for piece in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", str(part or "")):
            text = piece.lower().strip()
            if text and text not in tokens:
                tokens.append(text)
    return tokens


def retrieve_similar_case_memories(applicant_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    target_pet_name = str(applicant_data.get("target_pet_name") or "")
    target_species = str(applicant_data.get("target_species") or "")
    reason = str(applicant_data.get("application_reason") or "")
    profile = str(applicant_data.get("applicant_info") or "")
    keywords = _keyword_tokens(target_pet_name, target_species, reason, profile)

    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT cm.application_id, cm.case_summary, cm.decision_result, cm.followup_outcome,
                   cm.risk_tags_json, cm.updated_at, a.apply_reason, a.risk_level, p.name AS pet_name, p.species AS pet_species
            FROM adoption_case_memory cm
            LEFT JOIN applications a ON a.id = cm.application_id
            LEFT JOIN pets p ON p.id = a.pet_id
            ORDER BY cm.updated_at DESC, cm.id DESC
            LIMIT 40
            """
        )
        rows = [dict(row) for row in cursor.fetchall()]

    scored: List[Dict[str, Any]] = []
    for row in rows:
        haystack = " ".join(
            [
                str(row.get("case_summary") or ""),
                str(row.get("followup_outcome") or ""),
                str(row.get("apply_reason") or ""),
                str(row.get("pet_name") or ""),
                str(row.get("pet_species") or ""),
                str(row.get("risk_tags_json") or ""),
            ]
        ).lower()
        score = 0
        if target_species and str(row.get("pet_species") or "").lower() == target_species.lower():
            score += 3
        if target_pet_name and target_pet_name.lower() in str(row.get("pet_name") or "").lower():
            score += 4
        score += sum(1 for token in keywords if token in haystack)
        if score <= 0:
            continue
        row["risk_tags"] = json.loads(row.get("risk_tags_json") or "[]")
        row["similarity_score"] = score
        scored.append(row)

    scored.sort(key=lambda item: (-item["similarity_score"], item.get("updated_at") or ""), reverse=False)
    return scored[:limit]


def build_closed_loop_stats() -> Dict[str, Any]:
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM applications WHERE flow_status='adopted'")
        adopted = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM applications WHERE flow_status='followup_completed'")
        followup_completed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM applications WHERE owner_followed_ai = 1")
        owner_followed_ai = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adoption_case_memory WHERE feedback_id IS NOT NULL")
        case_memory_with_feedback = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adoption_followups WHERE answer IS NOT NULL AND TRIM(answer) != ''")
        answered_followups = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adoption_ai_reviews")
        ai_reviews = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM adoption_signal_weights")
        total_signal_weights = cursor.fetchone()[0]

    feedback_completion_rate = round((followup_completed / adopted) * 100, 1) if adopted else 0.0
    ai_follow_rate = round((owner_followed_ai / ai_reviews) * 100, 1) if ai_reviews else 0.0
    return {
        "adopted": adopted,
        "followup_completed": followup_completed,
        "feedback_completion_rate": feedback_completion_rate,
        "case_memory_with_feedback": case_memory_with_feedback,
        "answered_followups": answered_followups,
        "ai_follow_rate": ai_follow_rate,
        "total_signal_weights": total_signal_weights,
    }


def summarize_case_feedback_signal(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    positive = 0
    negative = 0
    highlighted: List[str] = []
    for case in cases:
        outcome = str(case.get("followup_outcome") or "").lower()
        score_match = re.search(r"满意度\s*(\d)\s*/\s*5", outcome)
        score = int(score_match.group(1)) if score_match else None
        if score is not None:
            if score >= 4:
                positive += 1
            elif score <= 2:
                negative += 1
        if "否" in outcome or "不推荐" in outcome:
            negative += 1
        if "是" in outcome and "推荐" in outcome:
            positive += 1
        summary = str(case.get("case_summary") or "").strip()
        if summary and summary not in highlighted:
            highlighted.append(summary[:120])

    return {
        "positive_cases": positive,
        "negative_cases": negative,
        "case_bias": positive - negative,
        "highlights": highlighted[:2],
    }


def _upsert_signal_weight(conn, signal_type: str, signal_key: str, positive_delta: int = 0, negative_delta: int = 0) -> None:
    if not signal_key:
        return
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT positive_count, negative_count
        FROM adoption_signal_weights
        WHERE signal_type=? AND signal_key=?
        """,
        (signal_type, signal_key),
    )
    row = cursor.fetchone()
    positive_count = (row["positive_count"] if row else 0) + positive_delta
    negative_count = (row["negative_count"] if row else 0) + negative_delta
    total = max(1, positive_count + negative_count)
    weight = round((positive_count - negative_count) / total, 2)
    conn.execute(
        """
        INSERT INTO adoption_signal_weights
        (signal_type, signal_key, positive_count, negative_count, weight, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(signal_type, signal_key) DO UPDATE SET
            positive_count=excluded.positive_count,
            negative_count=excluded.negative_count,
            weight=excluded.weight,
            updated_at=CURRENT_TIMESTAMP
        """,
        (signal_type, signal_key, positive_count, negative_count, weight),
    )


def update_signal_weights_from_feedback(
    *,
    route_decision: str = "",
    risk_tags: List[str] | None = None,
    followup_questions: List[str] | None = None,
    overall_satisfaction: int,
    would_recommend: bool,
) -> None:
    positive = overall_satisfaction >= 4 and bool(would_recommend)
    negative = overall_satisfaction <= 2 or not bool(would_recommend)
    positive_delta = 1 if positive else 0
    negative_delta = 1 if negative else 0
    if positive_delta == 0 and negative_delta == 0:
        return

    with get_db() as conn:
        ensure_tables(conn)
        if route_decision:
            _upsert_signal_weight(conn, "route_decision", route_decision, positive_delta, negative_delta)
        for tag in list(risk_tags or []):
            _upsert_signal_weight(conn, "risk_tag", str(tag), positive_delta, negative_delta)
        for question in list(followup_questions or []):
            _upsert_signal_weight(conn, "followup_question", str(question)[:160], positive_delta, negative_delta)
        conn.commit()


def get_signal_weight(signal_type: str, signal_key: str) -> float:
    with get_db() as conn:
        ensure_tables(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT weight
            FROM adoption_signal_weights
            WHERE signal_type=? AND signal_key=?
            """,
            (signal_type, signal_key),
        )
        row = cursor.fetchone()
    return float(row["weight"]) if row else 0.0


def collect_posterior_signal_weights(
    *,
    route_decision: str = "",
    risk_tags: List[str] | None = None,
    followup_questions: List[str] | None = None,
) -> Dict[str, Any]:
    risk_weight_map = {
        str(tag): get_signal_weight("risk_tag", str(tag))
        for tag in list(risk_tags or [])
        if str(tag or "").strip()
    }
    followup_weight_map = {
        str(question): get_signal_weight("followup_question", str(question)[:160])
        for question in list(followup_questions or [])
        if str(question or "").strip()
    }
    route_weight = get_signal_weight("route_decision", route_decision) if route_decision else 0.0
    return {
        "route_weight": round(route_weight, 2),
        "risk_tag_weights": risk_weight_map,
        "followup_weights": followup_weight_map,
        "average_risk_weight": round(sum(risk_weight_map.values()) / max(1, len(risk_weight_map)), 2) if risk_weight_map else 0.0,
        "average_followup_weight": round(sum(followup_weight_map.values()) / max(1, len(followup_weight_map)), 2) if followup_weight_map else 0.0,
    }
