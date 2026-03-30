import os
import sys
import sqlite3
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.services.adoption_consensus import fuse_consensus
from src.web.services.adoption_contract import CONTRACT_VERSION, normalize_agent_contract, validate_contract_list
from src.web.services.adoption_router import uncertainty_router
from src.web.services.adoption_flow_engine import flow_engine
from src.web.services.db_service import ensure_tables
from src.web.services import adoption_memory


def test_consensus_fusion_returns_framework_fields():
    result = fuse_consensus(
        rule_result={"base_score": 100, "rule_flags": []},
        ai_result={"readiness_score": 78, "confidence_level": 0.82, "risk_factors": [{"dimension": "时间", "description": "陪伴时间略少"}]},
        dimension_scores=[
            {"key": "economic", "label": "经济承受能力", "score": 80, "risk_level": "Low"},
            {"key": "time", "label": "时间陪伴能力", "score": 60, "risk_level": "Medium"},
        ],
        missing_fields=["房东是否允许养宠"],
        conflict_notes=["时间维度存在分歧"],
        risk_level="Medium",
    )

    assert result["overall_score"] >= 0
    assert 0 <= result["consensus_score"] <= 1
    assert 0 <= result["disagreement_score"] <= 1
    assert result["risk_level"] == "Medium"
    assert "information_gap" in result["risk_tags"]


def test_agent_contract_normalization_clamps_and_cleans_values():
    normalized = normalize_agent_contract(
        {
            "agent_name": "RiskAgent",
            "dimension_scores": {"economic": "82", "time": "bad"},
            "risk_tags": ["budget", "budget", ""],
            "missing_fields": ["房东许可", None],
            "confidence": 88,
            "recommendation": "manual_review",
            "evidence": ["预算一般", "预算一般"],
            "score": 108,
        }
    )

    assert normalized["agent_name"] == "RiskAgent"
    assert normalized["dimension_scores"] == {"economic": 82.0}
    assert normalized["risk_tags"] == ["budget"]
    assert normalized["missing_fields"] == ["房东许可"]
    assert normalized["confidence"] == 0.88
    assert normalized["score"] == 100


def test_validate_contract_list_returns_uniform_contracts():
    contracts = validate_contract_list(
        [
            {"agent_name": "A1", "confidence": 0.7, "score": 60},
            {"risk_tags": ["x"], "score": -2},
        ],
        fallback_name_prefix="Contract",
    )

    assert len(contracts) == 2
    assert contracts[0]["agent_name"] == "A1"
    assert contracts[1]["agent_name"] == "Contract2"
    assert contracts[1]["score"] == 0
    assert CONTRACT_VERSION == "adoption-agent-contract-v1"


def test_uncertainty_router_prefers_followup_when_information_is_missing():
    route = uncertainty_router(
        {
            "overall_score": 76,
            "consensus_score": 0.73,
            "disagreement_score": 0.12,
            "risk_level": "Medium",
            "missing_fields": ["家庭成员是否同意", "房东是否允许养宠"],
        },
        {"risk_tolerance": "medium"},
    )

    assert route["next_action"] == "followup"
    assert route["requires_followup"] is True


def test_flow_engine_maps_review_statuses():
    assert flow_engine.resolve_review_flow_status("approved") == "approved"
    assert flow_engine.resolve_review_flow_status("probing") == "need_more_info"
    assert flow_engine.resolve_terminal_flow_status("approved") == "adopted"
    assert flow_engine.resolve_feedback_flow_status("adopted") == "followup_completed"
    assert flow_engine.can_transition("waiting_publisher", "approved") is True
    assert flow_engine.can_transition("rejected", "approved") is False


def test_ensure_tables_creates_framework_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)

    cursor = conn.cursor()
    for table in (
        "publisher_preferences",
        "adoption_ai_reviews",
        "adoption_followups",
        "adoption_case_memory",
        "adoption_flow_events",
    ):
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        assert cursor.fetchone() is not None, f"{table} should exist"


def test_retrieve_similar_case_memories_prefers_matching_pet_context(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username, email, password) VALUES ('u1', 'u1@example.com', 'pwd')")
    cursor.execute("INSERT INTO users (username, email, password) VALUES ('owner', 'owner@example.com', 'pwd')")
    user_id = 1
    owner_id = 2
    cursor.execute("INSERT INTO pets (owner_id, name, species, status) VALUES (?, '奶糖', 'cat', '待领养')", (owner_id,))
    pet_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO applications (user_id, pet_id, apply_reason, pet_owner_id, status, risk_level, flow_status)
        VALUES (?, ?, ?, ?, 'approved', 'Medium', 'followup_completed')
        """,
        (user_id, pet_id, '我有稳定预算，也愿意长期照顾猫咪', owner_id),
    )
    app_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO adoption_case_memory (application_id, case_summary, decision_result, followup_outcome, risk_tags_json)
        VALUES (?, ?, 'approved', '回访良好', '["time"]')
        """,
        (app_id, '宠物：奶糖；综合评分：82；风险等级：Medium；当前决策：approved；申请概述：稳定预算和长期照顾计划',),
    )
    conn.commit()

    @contextmanager
    def fake_get_db():
        yield conn

    monkeypatch.setattr(adoption_memory, "get_db", fake_get_db)
    similar_cases = adoption_memory.retrieve_similar_case_memories(
        {
            "target_pet_name": "奶糖",
            "target_species": "cat",
            "application_reason": "我愿意长期照顾，也准备了稳定预算",
            "applicant_info": "家里环境稳定，能长期照顾猫咪",
        },
        limit=3,
    )

    assert similar_cases
    assert similar_cases[0]["application_id"] == app_id
    assert similar_cases[0]["similarity_score"] > 0


def test_flow_engine_appends_events_and_rebuilds_status():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)

    flow_engine.append_event(
        conn,
        application_id=12,
        event_type="application_submitted",
        from_status="submitted",
        to_status="waiting_publisher",
        actor_role="applicant",
        actor_id=3,
        payload={"pet_id": 9},
    )
    flow_engine.append_event(
        conn,
        application_id=12,
        event_type="review_completed",
        from_status="waiting_publisher",
        to_status="adopted",
        actor_role="publisher",
        actor_id=5,
        payload={"requested_status": "approved"},
    )
    conn.commit()

    timeline = flow_engine.get_timeline(conn, 12, limit=10)
    rebuilt = flow_engine.rebuild_flow_status(conn, 12, fallback_status="submitted")

    assert len(timeline) == 2
    assert timeline[0]["event_type"] == "review_completed"
    assert timeline[0]["payload"]["requested_status"] == "approved"
    assert rebuilt == "adopted"


def test_signal_weights_are_updated_and_collectable(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_tables(conn)

    @contextmanager
    def fake_get_db():
        yield conn

    monkeypatch.setattr(adoption_memory, "get_db", fake_get_db)
    adoption_memory.update_signal_weights_from_feedback(
        route_decision="publisher_review",
        risk_tags=["information_gap", "time"],
        followup_questions=["请补充房东许可"],
        overall_satisfaction=1,
        would_recommend=False,
    )
    weights = adoption_memory.collect_posterior_signal_weights(
        route_decision="publisher_review",
        risk_tags=["information_gap", "time"],
        followup_questions=["请补充房东许可"],
    )

    assert weights["route_weight"] < 0
    assert weights["risk_tag_weights"]["information_gap"] < 0
    assert weights["followup_weights"]["请补充房东许可"] < 0
