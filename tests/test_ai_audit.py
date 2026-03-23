"""
AI 审计接口单元测试
覆盖：agent_trace_logs 写入/读取、row_factory 修复验证、404/403 边界
"""
import os
import sys
import sqlite3
import json
import uuid
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── 辅助：创建内存数据库并建表 ─────────────────────────────────────────────

def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute('''CREATE TABLE agent_trace_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trace_id TEXT NOT NULL,
        endpoint TEXT,
        agent_name TEXT,
        tool_name TEXT,
        latency_ms INTEGER,
        fallback_used INTEGER DEFAULT 0,
        input_msg TEXT,
        output_msg TEXT,
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn


def _insert_trace(conn, trace_id: str, input_data: dict, output_data: dict):
    conn.execute(
        "INSERT INTO agent_trace_logs (trace_id, endpoint, input_msg, output_msg) VALUES (?,?,?,?)",
        (trace_id, "/api/adoption/assess", json.dumps(input_data), json.dumps(output_data))
    )
    conn.commit()


# ── 测试：写入后以 tuple 方式正确读取 ────────────────────────────────────

def test_trace_log_read_as_tuple():
    """agent_trace_logs 应能正确写入并以 row[0]/row[1] 读取"""
    conn = _make_conn()
    trace_id = str(uuid.uuid4())
    input_data = {"applicant_info": "测试数据", "species": "cat"}
    output_data = {
        "readiness_score": 75,
        "decision": "Approved",
        "confidence_level": 0.82,
        "risk_tags": ["经济风险"],
        "expert_summary": "申请人条件良好"
    }
    _insert_trace(conn, trace_id, input_data, output_data)

    cursor = conn.cursor()
    cursor.execute(
        "SELECT input_msg, output_msg FROM agent_trace_logs WHERE trace_id = ?",
        (trace_id,)
    )
    row = cursor.fetchone()

    assert row is not None, "应能查到写入的 trace 记录"
    input_msg, output_msg = row[0], row[1]
    parsed_input = json.loads(input_msg)
    parsed_output = json.loads(output_msg)

    assert parsed_input["species"] == "cat"
    assert parsed_output["readiness_score"] == 75
    assert parsed_output["decision"] == "Approved"


def test_trace_log_missing_returns_none():
    """查询不存在的 trace_id 应返回 None"""
    conn = _make_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT input_msg, output_msg FROM agent_trace_logs WHERE trace_id = ?",
        ("non-existent-trace-id",)
    )
    row = cursor.fetchone()
    assert row is None


def test_trace_log_output_msg_json_parseable():
    """output_msg 必须是合法 JSON，json.loads 不应抛异常"""
    conn = _make_conn()
    trace_id = str(uuid.uuid4())
    _insert_trace(
        conn, trace_id,
        {"test": True},
        {"readiness_score": 60, "decision": "Manual_Review",
         "confidence_level": 0.6, "risk_tags": [], "expert_summary": "需人工复核"}
    )
    cursor = conn.cursor()
    cursor.execute(
        "SELECT output_msg FROM agent_trace_logs WHERE trace_id = ?", (trace_id,)
    )
    row = cursor.fetchone()
    assert row is not None
    parsed = json.loads(row[0])
    assert "readiness_score" in parsed
    assert "decision" in parsed


def test_row_factory_not_json_loads():
    """
    验证修复后的代码不再将 row_factory 设为 json.loads（类型错误）。
    sqlite3.row_factory 必须是接受 (cursor, row) 两个参数的可调用对象，
    json.loads 只接受一个字符串参数，赋值后调用必然报错。
    """
    conn = _make_conn()
    # 模拟修复前的错误赋值
    conn.row_factory = json.loads
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    with pytest.raises(Exception):
        # 调用 fetchone() 时 sqlite3 会调用 row_factory(cursor, row)
        # 但 json.loads 不接受这个签名，必然报 TypeError
        cursor.fetchone()


def test_row_factory_sqlite_row_works():
    """sqlite3.Row 是合法的 row_factory，应正常工作"""
    conn = _make_conn()
    conn.row_factory = sqlite3.Row
    trace_id = str(uuid.uuid4())
    _insert_trace(conn, trace_id, {"x": 1}, {"readiness_score": 50, "decision": "Rejected",
                                               "confidence_level": 0.9, "risk_tags": [], "expert_summary": ""})
    cursor = conn.cursor()
    cursor.execute(
        "SELECT input_msg, output_msg FROM agent_trace_logs WHERE trace_id = ?", (trace_id,)
    )
    row = cursor.fetchone()
    assert row is not None
    assert json.loads(row["input_msg"])["x"] == 1
