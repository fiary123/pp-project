import asyncio
import json
import time
import uuid
from typing import Any, Dict, List

from src.agents.agents import run_adoption_assessment
from src.web.services.db_service import get_db


class AdoptionAssessmentService:
    """
    领养评估生命周期 Flow。
    目标：
    1. 规则预筛与多智能体推理解耦
    2. Knowledge / Memory 明确分层
    3. 通过 Hook 风格阶段日志实现可审计与可降级
    """

    def __init__(self):
        self.rules = {
            "min_monthly_budget": 200,
            "min_companion_hours": 2,
            "blacklist_check": True,
        }

    async def run_full_assessment(self, user_id: int, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        started_at = time.time()
        lifecycle: List[str] = []
        try:
            await self._before_stage(trace_id, "collect_application", applicant_data)
            lifecycle.append("collect_application")

            await self._before_stage(trace_id, "rule_prescreen", applicant_data)
            rule_result = self._check_hard_rules(applicant_data)
            await self._after_stage(trace_id, "rule_prescreen", rule_result)
            lifecycle.append("rule_prescreen")

            if not rule_result["passed"]:
                result = self._blocked_response(rule_result, trace_id, started_at, lifecycle)
                self._log_audit(user_id, trace_id, applicant_data, result)
                return result

            await self._before_stage(trace_id, "knowledge_memory_prepare", applicant_data)
            knowledge_context = self._build_knowledge_context(applicant_data)
            memory_context = self._build_memory_context(user_id, applicant_data)
            await self._after_stage(
                trace_id,
                "knowledge_memory_prepare",
                {"knowledge_context": knowledge_context, "memory_context": memory_context},
            )
            lifecycle.append("knowledge_memory_prepare")

            await self._before_stage(trace_id, "hierarchical_crew_reasoning", applicant_data)
            ai_result = await asyncio.to_thread(
                run_adoption_assessment,
                applicant_data.get("applicant_info", ""),
                applicant_data.get("target_species", "cat"),
                applicant_data.get("target_pet_name", "未指定"),
                float(applicant_data.get("monthly_budget", 0) or 0),
                float(applicant_data.get("daily_companion_hours", 0) or 0),
                bool(applicant_data.get("has_pet_experience", False)),
                applicant_data.get("housing_type", "apartment"),
                applicant_data.get("application_reason", ""),
                applicant_data.get("existing_pets", ""),
                applicant_data.get("publisher_preferences"),
                knowledge_context,
                memory_context,
            )
            await self._after_stage(trace_id, "hierarchical_crew_reasoning", ai_result)
            lifecycle.append("hierarchical_crew_reasoning")

            await self._before_stage(trace_id, "conflict_review", ai_result)
            final_result = self._merge_results(rule_result, ai_result, applicant_data)
            await self._after_stage(trace_id, "conflict_review", final_result)
            lifecycle.append("conflict_review")

            final_result["trace_id"] = trace_id
            final_result["flow_path"] = lifecycle
            final_result["engine"] = "AdoptionLifecycleFlow"
            final_result["latency_ms"] = int((time.time() - started_at) * 1000)

            self._log_audit(user_id, trace_id, applicant_data, final_result)
            return final_result
        except Exception as exc:
            fallback = self._fallback_response(trace_id, started_at, lifecycle, str(exc))
            self._log_audit(user_id, trace_id, applicant_data, fallback)
            return fallback

    def _check_hard_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        flags = []
        passed = True

        if float(data.get("monthly_budget", 0) or 0) < self.rules["min_monthly_budget"]:
            flags.append("经济能力可能无法覆盖基础养护支出")
            passed = False

        if float(data.get("daily_companion_hours", 0) or 0) < self.rules["min_companion_hours"]:
            flags.append("每日陪伴时间严重不足")
            passed = False

        return {
            "passed": passed,
            "rule_flags": flags,
            "base_score": 100 if passed else 40,
            "prescreen_summary": "通过基础规则预筛" if passed else "命中硬性约束，需先补齐基础条件",
        }

    def _build_knowledge_context(self, data: Dict[str, Any]) -> str:
        target_species = data.get("target_species", "cat")
        target_pet_name = data.get("target_pet_name", "未命名宠物")
        publisher_preferences = data.get("publisher_preferences") or {}
        return (
            "【Knowledge】\n"
            f"- 平台当前评估对象：{target_pet_name} / {target_species}\n"
            "- 平台规则关注时间、预算、住房稳定性、责任意识与家庭共识\n"
            f"- 发布者偏好模板：{json.dumps(publisher_preferences, ensure_ascii=False)}\n"
            "- 养宠知识应优先考虑长期陪伴、疾病照护与行为适配"
        )

    def _build_memory_context(self, user_id: int, data: Dict[str, Any]) -> str:
        target_pet_name = data.get("target_pet_name", "")
        target_species = data.get("target_species", "")
        memory = {
            "historical_applications": [],
            "post_adoption_feedback": [],
            "owner_decision_patterns": [],
        }
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT a.pet_id, a.status, a.ai_decision, a.ai_readiness_score, a.create_time, p.name AS pet_name
                    FROM applications a
                    LEFT JOIN pets p ON p.id = a.pet_id
                    WHERE a.user_id=?
                    ORDER BY a.create_time DESC
                    LIMIT 5
                    """,
                    (user_id,),
                )
                memory["historical_applications"] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                memory["historical_applications"] = []

            try:
                cursor.execute(
                    """
                    SELECT pet_name, overall_satisfaction, bond_level, would_recommend, create_time
                    FROM adoption_feedbacks
                    WHERE user_id=?
                    ORDER BY create_time DESC
                    LIMIT 5
                    """,
                    (user_id,),
                )
                memory["post_adoption_feedback"] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                memory["post_adoption_feedback"] = []

            try:
                cursor.execute(
                    """
                    SELECT a.status, a.owner_followed_ai, a.ai_decision, a.decision_time
                    FROM applications a
                    LEFT JOIN pets p ON p.id = a.pet_id
                    WHERE p.name=? OR p.species=?
                    ORDER BY a.decision_time DESC
                    LIMIT 5
                    """,
                    (target_pet_name, target_species),
                )
                memory["owner_decision_patterns"] = [dict(row) for row in cursor.fetchall()]
            except Exception:
                memory["owner_decision_patterns"] = []

        return "【Memory】\n" + json.dumps(memory, ensure_ascii=False)

    def _merge_results(self, rule_result: Dict[str, Any], ai_result: Dict[str, Any], applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        readiness_score = int(ai_result.get("readiness_score", rule_result["base_score"]))
        decision = ai_result.get("decision", "review_required")
        risk_level = ai_result.get("risk_level", "Medium")
        confidence_level = float(ai_result.get("confidence_level", 0.75))
        need_followup = bool(ai_result.get("need_followup", False))
        followup_questions = ai_result.get("followup_questions") or []
        conflict_notes = ai_result.get("conflict_notes") or []
        recommendations = ai_result.get("recommendations") or []

        if conflict_notes and not followup_questions:
            followup_questions = self._derive_followup_questions(applicant_data, conflict_notes)
            need_followup = True

        if risk_level == "High" and decision != "reject":
            decision = "review_required"

        return {
            "status": "success",
            "readiness_score": readiness_score,
            "success_probability": ai_result.get("success_probability", round(readiness_score / 100, 2)),
            "confidence_level": confidence_level,
            "risk_level": risk_level,
            "decision": decision,
            "need_manual_review": decision == "review_required",
            "need_followup": need_followup,
            "followup_questions": followup_questions[:3],
            "conflict_notes": conflict_notes[:3],
            "risk_factors": ai_result.get("risk_factors", []),
            "recommendations": recommendations[:5],
            "review_note": "高风险或冲突样本应交由送养方/管理员进一步确认" if decision == "review_required" else "",
            "baseline_report": ai_result.get("baseline_report", ""),
            "profile_report": ai_result.get("profile_report", ""),
            "cohabitation_report": ai_result.get("cohabitation_report", ""),
            "final_summary": ai_result.get("final_summary", ""),
        }

    def _derive_followup_questions(self, applicant_data: Dict[str, Any], conflict_notes: List[str]) -> List[str]:
        note_text = " ".join(conflict_notes)
        questions: List[str] = []
        if "陪伴" in note_text or "独处" in note_text:
            questions.append("如果宠物刚到家有些焦虑，您工作日每天能稳定陪伴多久？")
        if "预算" in note_text or "医疗" in note_text:
            questions.append("如果宠物突然生病需要持续治疗，您是否有长期医疗预算准备？")
        if "住房" in note_text or "租房" in note_text or "稳定" in note_text:
            questions.append("您当前的住房安排能否在未来一年内保持稳定？同住人是否都同意养宠？")
        if not questions:
            questions.append("您是否愿意再补充一下自己的作息、预算和长期照顾计划？")
        return questions[:3]

    async def _before_stage(self, trace_id: str, stage: str, payload: Dict[str, Any]):
        self._log_stage(trace_id, f"{stage}:before", payload)

    async def _after_stage(self, trace_id: str, stage: str, payload: Dict[str, Any]):
        self._log_stage(trace_id, f"{stage}:after", payload)

    def _log_stage(self, trace_id: str, stage: str, payload: Dict[str, Any]):
        summary = json.dumps(payload, ensure_ascii=False)[:1200]
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO agent_trace_logs
                (trace_id, endpoint, agent_name, tool_name, latency_ms, fallback_used, input_msg, output_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    "adoption_flow",
                    "AdoptionDecisionFlow",
                    stage,
                    0,
                    0,
                    stage,
                    summary,
                ),
            )
            conn.commit()

    def _log_audit(self, user_id: int, trace_id: str, input_data: Dict[str, Any], result: Dict[str, Any]):
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO agent_trace_logs
                (trace_id, endpoint, agent_name, tool_name, latency_ms, fallback_used, input_msg, output_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    "adoption_assessment",
                    "AdoptionDecisionManager",
                    "final_audit",
                    0,
                    0,
                    json.dumps({"user_id": user_id, "input": input_data}, ensure_ascii=False),
                    json.dumps(result, ensure_ascii=False)[:4000],
                ),
            )
            conn.commit()

    def _blocked_response(self, rule_result: Dict[str, Any], trace_id: str, started_at: float, lifecycle: List[str]) -> Dict[str, Any]:
        return {
            "status": "success",
            "readiness_score": 40,
            "success_probability": 0.2,
            "confidence_level": 0.95,
            "risk_level": "High",
            "decision": "reject",
            "need_manual_review": False,
            "need_followup": False,
            "followup_questions": [],
            "conflict_notes": [],
            "risk_factors": [
                {"dimension": "规则引擎", "description": flag, "severity": "high"}
                for flag in rule_result.get("rule_flags", [])
            ],
            "recommendations": ["请先补足基础预算或陪伴条件后再重新申请。"],
            "review_note": "",
            "baseline_report": "",
            "profile_report": "",
            "cohabitation_report": "",
            "final_summary": f"## 评估拦截\n\n{rule_result.get('prescreen_summary', '')}",
            "trace_id": trace_id,
            "flow_path": lifecycle,
            "engine": "AdoptionLifecycleFlow",
            "latency_ms": int((time.time() - started_at) * 1000),
        }

    def _fallback_response(self, trace_id: str, started_at: float, lifecycle: List[str], error_text: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "readiness_score": 68,
            "success_probability": 0.68,
            "confidence_level": 0.55,
            "risk_level": "Medium",
            "decision": "review_required",
            "need_manual_review": True,
            "need_followup": True,
            "followup_questions": [
                "您未来半年内的居住环境是否稳定？",
                "如果宠物生病，您是否有持续医疗预算准备？",
                "工作日下班后，您通常能陪伴宠物多久？",
            ],
            "conflict_notes": ["智能评估链路出现波动，已切换为规则兜底评估。"],
            "risk_factors": [],
            "recommendations": ["建议补充长期照顾计划，并由送养方进一步确认。"],
            "review_note": error_text[:200],
            "baseline_report": "",
            "profile_report": "",
            "cohabitation_report": "",
            "final_summary": "系统已根据基础条件完成兜底评估，当前建议补充更多照顾计划后再由送养方进一步确认。",
            "trace_id": trace_id,
            "flow_path": lifecycle + ["fallback_response"],
            "engine": "AdoptionLifecycleFlow",
            "latency_ms": int((time.time() - started_at) * 1000),
        }
