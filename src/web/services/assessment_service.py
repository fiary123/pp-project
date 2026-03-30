import asyncio
import json
import time
import uuid
from typing import Any, Dict, List

from src.agents.agents import run_adoption_assessment
from src.web.services.db_service import get_db
from src.web.services.adoption_consensus import fuse_consensus
from src.web.services.adoption_contract import CONTRACT_VERSION, validate_contract_list
from src.web.services.adoption_memory import (
    collect_posterior_signal_weights,
    retrieve_similar_case_memories,
    summarize_case_feedback_signal,
)
from src.web.services.adoption_router import uncertainty_router


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
        self.dimension_labels = {
            "economic": "经济承受能力",
            "time": "时间陪伴能力",
            "housing": "居住环境适配度",
            "family": "家庭支持度",
            "experience": "养宠经验",
            "motivation": "领养动机稳定性",
            "compatibility": "与当前宠物的适配度",
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
                result = self._blocked_response(rule_result, applicant_data, trace_id, started_at, lifecycle)
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
            fallback = self._fallback_response(applicant_data, trace_id, started_at, lifecycle, str(exc))
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
            f"- 发布者硬性条件：{json.dumps(publisher_preferences.get('hard_preferences', []), ensure_ascii=False)}\n"
            f"- 发布者软性偏好：{json.dumps(publisher_preferences.get('soft_preferences', []), ensure_ascii=False)}\n"
            f"- 发布者风险容忍度：{publisher_preferences.get('risk_tolerance', 'medium')}\n"
            "- 养宠知识应优先考虑长期陪伴、疾病照护与行为适配"
        )

    def _build_memory_context(self, user_id: int, data: Dict[str, Any]) -> str:
        target_pet_name = data.get("target_pet_name", "")
        target_species = data.get("target_species", "")
        memory = {
            "historical_applications": [],
            "post_adoption_feedback": [],
            "owner_decision_patterns": [],
            "case_memory": [],
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

            try:
                memory["case_memory"] = retrieve_similar_case_memories(data, limit=5)
            except Exception:
                memory["case_memory"] = []

        return "【Memory】\n" + json.dumps(memory, ensure_ascii=False)

    def _unique_list(self, values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            text = (value or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    def _clamp_score(self, score: float) -> int:
        return int(max(0, min(100, round(score))))

    def _risk_from_score(self, score: int) -> str:
        if score >= 75:
            return "Low"
        if score >= 55:
            return "Medium"
        return "High"

    def _text_contains(self, text: str, keywords: List[str]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _dimension_result(
        self,
        key: str,
        score: float,
        evidence: List[str],
        missing_info: List[str],
        suggestion: str,
    ) -> Dict[str, Any]:
        final_score = self._clamp_score(score)
        return {
            "key": key,
            "label": self.dimension_labels[key],
            "score": final_score,
            "risk_level": self._risk_from_score(final_score),
            "evidence": self._unique_list(evidence),
            "missing_info": self._unique_list(missing_info),
            "suggestion": suggestion,
        }

    def _evaluate_dimensions(self, data: Dict[str, Any], ai_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        prefs = data.get("publisher_preferences") or {}
        applicant_text = f"{data.get('applicant_info', '')}\n{data.get('application_reason', '')}".lower()
        budget = float(data.get("monthly_budget", 0) or 0)
        companion_hours = float(data.get("daily_companion_hours", 0) or 0)
        has_experience = bool(data.get("has_pet_experience", False))
        housing_type = data.get("housing_type", "apartment")
        existing_pets = (data.get("existing_pets") or "").strip()
        ai_conflicts = " ".join(ai_result.get("conflict_notes") or [])

        dimensions: List[Dict[str, Any]] = []

        economic_score = 45
        economic_evidence: List[str] = []
        economic_missing: List[str] = []
        if budget <= 0:
            economic_missing.append("尚未明确月均养宠预算")
            economic_evidence.append("当前没有提交明确的预算信息")
        elif budget >= 1200:
            economic_score = 95
            economic_evidence.append(f"已填写月预算约 {int(budget)} 元，经济准备较充分")
        elif budget >= 800:
            economic_score = 85
            economic_evidence.append(f"已填写月预算约 {int(budget)} 元，能覆盖大部分日常支出")
        elif budget >= 500:
            economic_score = 72
            economic_evidence.append(f"已填写月预算约 {int(budget)} 元，基础支出能力基本可接受")
        elif budget >= 300:
            economic_score = 60
            economic_evidence.append(f"月预算约 {int(budget)} 元，处于偏紧状态")
        else:
            economic_score = 45
            economic_evidence.append(f"月预算约 {int(budget)} 元，难以覆盖医疗和长期波动开销")
        if prefs.get("require_financial_capacity") and budget < 500:
            economic_score -= 12
            economic_evidence.append("送养方将经济能力视为关键条件，当前预算支撑偏弱")
        if self._text_contains(applicant_text, ["稳定收入", "固定收入", "应急预算", "储蓄"]):
            economic_score += 6
            economic_evidence.append("申请描述中体现出稳定收入或应急预算意识")
        dimensions.append(self._dimension_result("economic", economic_score, economic_evidence, economic_missing, "建议补充基础开销、医疗储备和应急预算安排。"))

        time_score = 45
        time_evidence: List[str] = []
        time_missing: List[str] = []
        if companion_hours <= 0:
            time_missing.append("尚未明确工作日可陪伴宠物的时间")
            time_evidence.append("当前没有提交明确的陪伴时长")
        elif companion_hours >= 8:
            time_score = 95
            time_evidence.append(f"工作日预计可陪伴 {companion_hours:g} 小时，时间投入充分")
        elif companion_hours >= 4:
            time_score = 82
            time_evidence.append(f"工作日预计可陪伴 {companion_hours:g} 小时，陪伴能力较强")
        elif companion_hours >= 2:
            time_score = 68
            time_evidence.append(f"工作日预计可陪伴 {companion_hours:g} 小时，达到基础陪伴门槛")
        else:
            time_score = 46
            time_evidence.append(f"工作日预计可陪伴 {companion_hours:g} 小时，陪伴能力偏弱")
        if prefs.get("focus_companionship") and companion_hours < 4:
            time_score -= 10
            time_evidence.append("送养方更关注长期陪伴，当前时间投入与偏好存在落差")
        if self._text_contains(applicant_text, ["加班", "经常出差", "工作很忙", "不固定", "轮班"]):
            time_score -= 8
            time_evidence.append("申请描述中提及加班或作息不稳定，可能影响陪伴兑现")
        dimensions.append(self._dimension_result("time", time_score, time_evidence, time_missing, "建议补充工作日作息、独处时长和照护兜底安排。"))

        housing_score = {"house": 85, "apartment": 72, "other": 60}.get(housing_type, 60)
        housing_evidence = [f"当前填写住房类型为：{'独立住宅' if housing_type == 'house' else '公寓' if housing_type == 'apartment' else '其他'}"]
        housing_missing: List[str] = []
        if prefs.get("require_stable_housing"):
            housing_evidence.append("送养方将稳定居住环境视为重点")
        if not prefs.get("accept_renting", True) and self._text_contains(applicant_text, ["租房", "合租"]):
            housing_score -= 18
            housing_evidence.append("送养方对租房申请较谨慎，当前描述存在租住信号")
        if self._text_contains(applicant_text, ["搬家", "短租", "暂住", "不稳定"]):
            housing_score -= 14
            housing_evidence.append("申请描述中存在居住不稳定信号")
        if prefs.get("require_stable_housing") and not self._text_contains(applicant_text, ["稳定", "长期居住", "固定住所", "自住房", "封窗"]):
            housing_missing.append("建议补充居住稳定性、封窗/活动空间等环境信息")
        dimensions.append(self._dimension_result("housing", housing_score, housing_evidence, housing_missing, "建议说明居住周期、封窗情况和宠物活动空间。"))

        family_score = 60
        family_evidence: List[str] = []
        family_missing: List[str] = []
        if self._text_contains(applicant_text, ["家人支持", "家里人都同意", "家人同意", "伴侣支持", "父母同意"]):
            family_score = 88
            family_evidence.append("申请描述中明确提到家庭成员支持领养")
        elif self._text_contains(applicant_text, ["家人反对", "家里不同意", "室友不同意", "伴侣不同意"]):
            family_score = 25
            family_evidence.append("申请描述中出现家庭或同住人反对信号")
        else:
            family_evidence.append("家庭支持度信息较少，目前只能做中性判断")
        if prefs.get("require_family_agreement") and family_score < 80:
            family_score -= 12
            family_evidence.append("送养方要求家庭成员明确同意，当前证据不足")
            family_missing.append("建议补充家庭成员或同住人是否知情并一致同意")
        dimensions.append(self._dimension_result("family", family_score, family_evidence, family_missing, "建议明确说明家庭态度、同住人支持度和照护分工。"))

        experience_score = 82 if has_experience else 52
        experience_evidence = ["已勾选具备养宠经验" if has_experience else "当前填写为无明确养宠经验"]
        experience_missing: List[str] = []
        if self._text_contains(applicant_text, ["养过", "救助过", "照顾过", "曾经养", "寄养"]):
            experience_score = max(experience_score, 84)
            experience_evidence.append("申请描述中提及既往养宠或照护经历")
        if prefs.get("focus_experience") and not has_experience:
            experience_score -= 12
            experience_evidence.append("送养方更看重经验，当前经验支撑偏弱")
        if not prefs.get("allow_novice", True) and not has_experience:
            experience_score -= 15
            experience_evidence.append("送养方不倾向新手申请，当前与偏好存在冲突")
            experience_missing.append("建议补充过往照护经历、疾病处理或训练经验")
        dimensions.append(self._dimension_result("experience", experience_score, experience_evidence, experience_missing, "建议补充过往养宠经历和突发情况处理经验。"))

        motivation_score = 62
        motivation_evidence: List[str] = []
        motivation_missing: List[str] = []
        reason_text = (data.get("application_reason") or "").strip()
        if len(reason_text) >= 20:
            motivation_score += 12
            motivation_evidence.append("申请理由较完整，动机表达相对充分")
        else:
            motivation_missing.append("申请理由偏简略，建议补充长期照护动机")
            motivation_evidence.append("当前申请理由较短，难以完整判断动机稳定性")
        if self._text_contains(applicant_text, ["长期陪伴", "负责到底", "终身", "稳定照顾", "做好准备"]):
            motivation_score += 12
            motivation_evidence.append("申请文本体现出长期责任意识")
        if self._text_contains(applicant_text, ["冲动", "试试看", "好玩", "随便", "孩子喜欢"]):
            motivation_score -= 20
            motivation_evidence.append("申请文本中出现短期或冲动型动机信号")
        dimensions.append(self._dimension_result("motivation", motivation_score, motivation_evidence, motivation_missing, "建议补充领养原因、长期承诺和困难场景应对计划。"))

        compatibility_score = 70
        compatibility_evidence: List[str] = ["默认从宠物特性、家庭氛围和原住宠物情况做综合判断"]
        compatibility_missing: List[str] = []
        if existing_pets:
            compatibility_evidence.append(f"已填写原住宠物情况：{existing_pets}")
            compatibility_score += 6
        if prefs.get("prefer_multi_pet_experience") and existing_pets and not has_experience:
            compatibility_score -= 10
            compatibility_evidence.append("存在原住宠物，但多宠磨合经验仍需进一步确认")
        if prefs.get("prefer_quiet_household"):
            if self._text_contains(applicant_text, ["安静", "规律", "独居", "作息稳定"]):
                compatibility_score += 10
                compatibility_evidence.append("申请描述与送养方偏好的安静家庭氛围较契合")
            else:
                compatibility_score -= 8
                compatibility_evidence.append("送养方偏好安静家庭，当前文本支持度不足")
                compatibility_missing.append("建议补充家庭氛围、噪音和日常节奏信息")
        if self._text_contains(ai_conflicts, ["原住宠物", "磨合", "环境"]):
            compatibility_score -= 8
            compatibility_evidence.append("AI 冲突检测提示环境或共处磨合仍存在不确定性")
        dimensions.append(self._dimension_result("compatibility", compatibility_score, compatibility_evidence, compatibility_missing, "建议补充原住宠物磨合预案、安置空间和适应计划。"))

        return dimensions

    def _build_dimension_summary(self, dimensions: List[Dict[str, Any]]) -> str:
        ordered = sorted(dimensions, key=lambda item: item["score"])
        weakest = "；".join(f"{item['label']} {item['score']}分" for item in ordered[:3])
        strongest = "；".join(f"{item['label']} {item['score']}分" for item in sorted(dimensions, key=lambda item: item["score"], reverse=True)[:2])
        return f"维度速览：薄弱项为 {weakest}。相对优势项为 {strongest}。"

    def _merge_results(self, rule_result: Dict[str, Any], ai_result: Dict[str, Any], applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        similar_cases = retrieve_similar_case_memories(applicant_data, limit=3)
        case_signal = summarize_case_feedback_signal(similar_cases)
        dimension_scores = self._evaluate_dimensions(applicant_data, ai_result)
        average_dimension_score = round(
            sum(item["score"] for item in dimension_scores) / max(1, len(dimension_scores))
        )
        ai_score = int(ai_result.get("readiness_score", rule_result["base_score"]))
        readiness_score = self._clamp_score(ai_score * 0.6 + average_dimension_score * 0.4)
        decision = ai_result.get("decision", "review_required")
        confidence_level = float(ai_result.get("confidence_level", 0.75))
        followup_questions = list(ai_result.get("followup_questions") or [])
        conflict_notes = list(ai_result.get("conflict_notes") or [])
        recommendations = list(ai_result.get("recommendations") or [])
        missing_fields = self._unique_list(
            [item for dimension in dimension_scores for item in dimension.get("missing_info", [])]
        )

        for dimension in dimension_scores:
            if dimension["risk_level"] == "High":
                conflict_notes.append(f"{dimension['label']}存在明显短板，需要重点核验")
            if dimension["score"] < 70 or dimension.get("missing_info"):
                recommendations.append(dimension["suggestion"])
            if dimension.get("missing_info"):
                question = f"请补充说明：{dimension['missing_info'][0]}"
                followup_questions.append(question)

        if conflict_notes and not followup_questions:
            followup_questions = self._derive_followup_questions(applicant_data, conflict_notes)
        else:
            followup_questions = self._unique_list(followup_questions)

        if case_signal["case_bias"] <= -1:
            readiness_score = self._clamp_score(readiness_score - 6)
            conflict_notes.append("相似历史案例的后验反馈偏谨慎，建议加强人工确认")
            recommendations.append("历史相似案例中出现低满意度或不推荐反馈，建议重点核验长期照护兑现能力。")
        elif case_signal["case_bias"] >= 1:
            readiness_score = self._clamp_score(readiness_score + 3)
            recommendations.append("相似历史案例反馈整体较正向，可作为辅助参考，但仍需结合当前个体条件判断。")

        high_risk_dimensions = sum(1 for item in dimension_scores if item["risk_level"] == "High")
        medium_risk_dimensions = sum(1 for item in dimension_scores if item["risk_level"] == "Medium")
        if high_risk_dimensions >= 2 or readiness_score < 55:
            risk_level = "High"
        elif high_risk_dimensions >= 1 or medium_risk_dimensions >= 3 or readiness_score < 75:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        risk_factors = list(ai_result.get("risk_factors", []))
        for dimension in dimension_scores:
            if dimension["risk_level"] in ("Medium", "High"):
                risk_factors.append(
                    {
                        "dimension": dimension["label"],
                        "description": dimension["evidence"][0] if dimension["evidence"] else f"{dimension['label']}需要进一步确认",
                        "severity": "high" if dimension["risk_level"] == "High" else "medium",
                    }
                )

        summary_bits = self._build_dimension_summary(dimension_scores)
        final_summary = ai_result.get("final_summary", "").strip()
        if final_summary:
            final_summary = f"{final_summary}\n\n{summary_bits}"
        else:
            final_summary = summary_bits
        agent_outputs = validate_contract_list([
            {
                "agent_name": "RulePrescreenAgent",
                "dimension_scores": {},
                "risk_tags": rule_result.get("rule_flags", []),
                "missing_fields": [],
                "confidence": 0.98,
                "recommendation": "pass" if rule_result.get("passed") else "reject_candidate",
                "evidence": [rule_result.get("prescreen_summary", "")],
                "score": rule_result.get("base_score", 60),
            },
            *list(ai_result.get("structured_agent_contracts") or ai_result.get("agent_outputs") or []),
            {
                "agent_name": "DimensionScoringLayer",
                "dimension_scores": {item["key"]: item["score"] for item in dimension_scores},
                "risk_tags": [item["label"] for item in dimension_scores if item["risk_level"] in ("Medium", "High")],
                "missing_fields": missing_fields[:6],
                "confidence": round(max(0.45, min(0.95, average_dimension_score / 100)), 2),
                "recommendation": decision,
                "evidence": [self._build_dimension_summary(dimension_scores)],
                "score": average_dimension_score,
            },
        ], fallback_name_prefix="AssessmentLayer")

        consensus_result = fuse_consensus(
            rule_result=rule_result,
            ai_result=ai_result,
            dimension_scores=dimension_scores,
            missing_fields=missing_fields,
            conflict_notes=conflict_notes,
            risk_level=risk_level,
        )
        route_decision = uncertainty_router(consensus_result, applicant_data.get("publisher_preferences") or {})
        posterior_signal_weights = collect_posterior_signal_weights(
            route_decision=route_decision.get("next_action", ""),
            risk_tags=consensus_result.get("risk_tags") or [],
            followup_questions=followup_questions,
        )
        if posterior_signal_weights["average_risk_weight"] <= -0.35:
            readiness_score = self._clamp_score(readiness_score - 4)
            conflict_notes.append("历史后验表明当前风险标签对应的不良结果偏多")
            recommendations.append("历史反馈显示当前风险标签的负向结果较多，建议提高人工核验强度。")
        elif posterior_signal_weights["average_risk_weight"] >= 0.35:
            readiness_score = self._clamp_score(readiness_score + 2)
            recommendations.append("历史反馈显示当前风险标签对应的实际结果相对稳定，可作为辅助参考。")

        if posterior_signal_weights["route_weight"] <= -0.45 and route_decision.get("next_action") == "publisher_review":
            route_decision = {
                **route_decision,
                "next_action": "manual_review",
                "requires_followup": False,
                "requires_manual_review": True,
                "route_reason": list(route_decision.get("route_reason") or []) + ["历史后验表明直接交由发布者决策的效果偏弱，已上调为人工复核"],
            }
        elif posterior_signal_weights["average_followup_weight"] >= 0.4 and route_decision.get("next_action") == "publisher_review" and followup_questions:
            route_decision = {
                **route_decision,
                "next_action": "followup",
                "requires_followup": True,
                "requires_manual_review": False,
                "route_reason": list(route_decision.get("route_reason") or []) + ["历史后验表明当前追问项对结果区分度较高，优先触发补充追问"],
            }
        consensus_result["next_action"] = route_decision.get("next_action", "publisher_review")

        readiness_score = int(consensus_result.get("overall_score", readiness_score))
        risk_level = consensus_result.get("risk_level", risk_level)
        need_followup = bool(route_decision.get("requires_followup"))
        need_manual_review = bool(route_decision.get("requires_manual_review"))

        if route_decision["next_action"] == "reject_candidate":
            decision = "reject"
        elif route_decision["next_action"] == "manual_review":
            decision = "review_required"
        elif route_decision["next_action"] == "followup":
            decision = "conditional_pass"
        elif readiness_score >= 78:
            decision = "pass"
        else:
            decision = "conditional_pass"

        return {
            "status": "success",
            "readiness_score": readiness_score,
            "success_probability": round(ai_result.get("success_probability", readiness_score / 100), 2),
            "confidence_level": confidence_level,
            "risk_level": risk_level,
            "decision": decision,
            "need_manual_review": need_manual_review,
            "need_followup": need_followup,
            "dimension_scores": dimension_scores,
            "missing_fields": missing_fields[:6],
            "followup_questions": self._unique_list(followup_questions)[:4],
            "conflict_notes": self._unique_list(conflict_notes)[:4],
            "risk_factors": risk_factors[:8],
            "recommendations": self._unique_list(recommendations)[:6],
            "review_note": "高风险或冲突样本应交由送养方/管理员进一步确认" if decision == "review_required" else "",
            "baseline_report": ai_result.get("baseline_report", ""),
            "profile_report": ai_result.get("profile_report", ""),
            "cohabitation_report": ai_result.get("cohabitation_report", ""),
            "final_summary": final_summary,
            "agent_outputs": agent_outputs,
            "structured_contract_version": CONTRACT_VERSION,
            "similar_cases": similar_cases,
            "case_feedback_signal": case_signal,
            "posterior_signal_weights": posterior_signal_weights,
            "consensus_result": consensus_result,
            "route_decision": route_decision,
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

    def _blocked_response(self, rule_result: Dict[str, Any], applicant_data: Dict[str, Any], trace_id: str, started_at: float, lifecycle: List[str]) -> Dict[str, Any]:
        dimension_scores = self._evaluate_dimensions(applicant_data, {})
        consensus_result = {
            "overall_score": 40,
            "consensus_score": 0.92,
            "disagreement_score": 0.0,
            "risk_level": "High",
            "risk_tags": ["hard_rule_block"],
            "missing_fields": self._unique_list([item for d in dimension_scores for item in d.get("missing_info", [])])[:6],
            "next_action": "reject_candidate",
        }
        return {
            "status": "success",
            "readiness_score": 40,
            "success_probability": 0.2,
            "confidence_level": 0.95,
            "risk_level": "High",
            "decision": "reject",
            "need_manual_review": False,
            "need_followup": False,
            "dimension_scores": dimension_scores,
            "missing_fields": self._unique_list([item for d in dimension_scores for item in d.get("missing_info", [])])[:6],
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
            "final_summary": f"## 评估拦截\n\n{rule_result.get('prescreen_summary', '')}\n\n{self._build_dimension_summary(dimension_scores)}",
            "agent_outputs": validate_contract_list([{
                "agent_name": "RulePrescreenAgent",
                "dimension_scores": {},
                "risk_tags": rule_result.get("rule_flags", []),
                "missing_fields": [],
                "confidence": 0.99,
                "recommendation": "reject_candidate",
                "evidence": [rule_result.get("prescreen_summary", "")],
                "score": 40,
            }], fallback_name_prefix="AssessmentLayer"),
            "structured_contract_version": CONTRACT_VERSION,
            "similar_cases": retrieve_similar_case_memories(applicant_data, limit=3),
            "case_feedback_signal": summarize_case_feedback_signal(retrieve_similar_case_memories(applicant_data, limit=3)),
            "posterior_signal_weights": collect_posterior_signal_weights(route_decision="reject_candidate", risk_tags=["hard_rule_block"], followup_questions=[]),
            "consensus_result": consensus_result,
            "route_decision": {
                "next_action": "reject_candidate",
                "requires_followup": False,
                "requires_manual_review": False,
                "route_reason": ["命中硬性规则拦截"],
            },
            "trace_id": trace_id,
            "flow_path": lifecycle,
            "engine": "AdoptionLifecycleFlow",
            "latency_ms": int((time.time() - started_at) * 1000),
        }

    def _fallback_response(self, applicant_data: Dict[str, Any], trace_id: str, started_at: float, lifecycle: List[str], error_text: str) -> Dict[str, Any]:
        dimension_scores = self._evaluate_dimensions(applicant_data, {})
        consensus_result = {
            "overall_score": 68,
            "consensus_score": 0.55,
            "disagreement_score": 0.32,
            "risk_level": "Medium",
            "risk_tags": ["fallback_response", "information_gap"],
            "missing_fields": self._unique_list([item for d in dimension_scores for item in d.get("missing_info", [])])[:6],
            "next_action": "manual_review",
        }
        return {
            "status": "success",
            "readiness_score": 68,
            "success_probability": 0.68,
            "confidence_level": 0.55,
            "risk_level": "Medium",
            "decision": "review_required",
            "need_manual_review": True,
            "need_followup": True,
            "dimension_scores": dimension_scores,
            "missing_fields": self._unique_list([item for d in dimension_scores for item in d.get("missing_info", [])])[:6],
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
            "final_summary": f"系统已根据基础条件完成兜底评估，当前建议补充更多照顾计划后再由送养方进一步确认。\n\n{self._build_dimension_summary(dimension_scores)}",
            "agent_outputs": validate_contract_list([{
                "agent_name": "FallbackRuleEngine",
                "dimension_scores": {},
                "risk_tags": ["fallback_response"],
                "missing_fields": self._unique_list([item for d in dimension_scores for item in d.get("missing_info", [])])[:6],
                "confidence": 0.55,
                "recommendation": "manual_review",
                "evidence": ["智能评估链路波动，已切换为规则兜底评估"],
                "score": 68,
            }], fallback_name_prefix="AssessmentLayer"),
            "structured_contract_version": CONTRACT_VERSION,
            "similar_cases": retrieve_similar_case_memories(applicant_data, limit=3),
            "case_feedback_signal": summarize_case_feedback_signal(retrieve_similar_case_memories(applicant_data, limit=3)),
            "posterior_signal_weights": collect_posterior_signal_weights(route_decision="manual_review", risk_tags=["fallback_response", "information_gap"], followup_questions=[]),
            "consensus_result": consensus_result,
            "route_decision": {
                "next_action": "manual_review",
                "requires_followup": True,
                "requires_manual_review": True,
                "route_reason": ["智能评估链路波动，已切换为规则兜底"],
            },
            "trace_id": trace_id,
            "flow_path": lifecycle + ["fallback_response"],
            "engine": "AdoptionLifecycleFlow",
            "latency_ms": int((time.time() - started_at) * 1000),
        }
