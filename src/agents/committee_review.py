"""
独立评审-委员会表决-分歧仲裁  多智能体评估架构
(Thesis Core: Independent Review - Committee Voting - Conflict Mediation)

设计原则：
  1. 每个评审专家在独立 Crew 中单独运行，互不干扰，避免锚定效应
  2. 所有专家输出统一为 AgentContract 格式，便于表决
  3. 分歧度超过阈值时，触发仲裁智能体分析根因并裁决
  4. 最终结果由委员会表决算法（非简单平均）产出
"""

import json
import time
import logging
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from crewai import Agent, Task, Crew

logger = logging.getLogger(__name__)


# ============================================================
# 1. 独立评审 Crew（每个专家单独跑一个 Crew）
# ============================================================

def _run_single_crew(agent: Agent, task_description: str, expected_output: str) -> str:
    """执行单个 Agent 的独立评审，返回原始输出"""
    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
    )
    try:
        return str(Crew(agents=[agent], tasks=[task]).kickoff())
    except Exception as e:
        logger.error(f"独立评审失败 [{agent.role}]: {e}")
        return ""


def _parse_contract_from_raw(raw: str, agent_name: str, fallback_score: int = 65) -> Dict[str, Any]:
    """从 Agent 原始输出中解析标准化 contract"""
    import re
    contract = {
        "agent_name": agent_name,
        "score": fallback_score,
        "recommendation": "publisher_review",
        "risk_tags": [],
        "evidence": [],
        "missing_fields": [],
        "confidence": 0.72,
        "dimension_scores": {},
    }
    if not raw:
        contract["evidence"] = ["评审未返回有效输出"]
        contract["confidence"] = 0.3
        return contract

    # 尝试解析 JSON
    cleaned = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.S)
    if fenced:
        cleaned = fenced.group(1)
    else:
        brace = re.search(r"(\{.*\})", cleaned, re.S)
        if brace:
            cleaned = brace.group(1)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            contract["score"] = int(float(data.get("readiness_score", data.get("score", fallback_score))))
            contract["score"] = max(0, min(100, contract["score"]))
            contract["confidence"] = float(data.get("confidence", data.get("confidence_level", 0.72)))
            if contract["confidence"] > 1:
                contract["confidence"] = contract["confidence"] / 100
            contract["risk_tags"] = data.get("risk_tags", data.get("risk_factors", []))
            if isinstance(contract["risk_tags"], list):
                contract["risk_tags"] = [str(t.get("dimension", t) if isinstance(t, dict) else t) for t in contract["risk_tags"]]
            contract["evidence"] = data.get("evidence", data.get("recommendations", []))
            if isinstance(contract["evidence"], str):
                contract["evidence"] = [contract["evidence"]]
            contract["missing_fields"] = data.get("missing_fields", data.get("followup_questions", []))

            decision = str(data.get("decision", data.get("recommendation", ""))).lower()
            if "reject" in decision:
                contract["recommendation"] = "reject_candidate"
            elif "review" in decision or "人工" in decision:
                contract["recommendation"] = "manual_review"
            elif "followup" in decision or "追问" in decision:
                contract["recommendation"] = "followup"
            else:
                contract["recommendation"] = "publisher_review"

            contract["dimension_scores"] = data.get("dimension_scores", {})
    except (json.JSONDecodeError, ValueError):
        # JSON 解析失败，从文本中提取分数
        score_match = re.search(r'(?:score|评分|分数)[：:\s]*(\d+)', raw, re.I)
        if score_match:
            contract["score"] = max(0, min(100, int(score_match.group(1))))
        contract["evidence"] = [raw[:200]]

    return contract


def run_independent_reviews(
    llm,
    *,
    applicant_info: str,
    target_species: str,
    target_pet_name: str,
    monthly_budget: float,
    daily_companion_hours: float,
    has_pet_experience: bool,
    housing_type: str,
    application_reason: str,
    existing_pets: str,
    publisher_preferences: Optional[dict],
    knowledge_context: str,
    memory_context: str,
) -> Dict[str, Dict[str, Any]]:
    """
    并行运行 3 个独立评审 Crew，返回各自的标准化 contract。
    每个评审专家互不可见彼此的输出。
    """
    from .adoption_profiler import (
        get_encyclopedia_agent,
        get_adoption_profiler_agent,
        get_cohabitation_risk_agent,
    )

    prefs_str = json.dumps(publisher_preferences or {}, ensure_ascii=False)

    # 定义三个独立评审任务
    review_configs = {
        "BreedBaselineReview": {
            "agent_factory": lambda: get_encyclopedia_agent(llm),
            "description": (
                f"你正在独立评审一份领养申请，请从品种养护基准角度出发。\n"
                f"目标宠物: {target_pet_name} ({target_species})\n"
                f"申请人信息: {applicant_info}\n"
                f"月预算: {monthly_budget}元, 日陪伴: {daily_companion_hours}h\n"
                f"养宠经验: {'有' if has_pet_experience else '无'}, 住房: {housing_type}\n"
                f"知识参考: {knowledge_context}\n\n"
                "请输出严格 JSON: {readiness_score(0-100), confidence(0-1), "
                "risk_tags(数组), evidence(数组), missing_fields(数组), decision(pass/reject/review)}"
            ),
            "expected_output": "严格 JSON 对象",
        },
        "ProfileMatchReview": {
            "agent_factory": lambda: get_adoption_profiler_agent(llm),
            "description": (
                f"你正在独立评审一份领养申请，请从申请人画像与送养人偏好匹配角度出发。\n"
                f"目标宠物: {target_pet_name} ({target_species})\n"
                f"申请理由: {application_reason}\n"
                f"申请人信息: {applicant_info}\n"
                f"月预算: {monthly_budget}元, 日陪伴: {daily_companion_hours}h\n"
                f"养宠经验: {'有' if has_pet_experience else '无'}, 住房: {housing_type}\n"
                f"原住宠物: {existing_pets}\n"
                f"送养人偏好: {prefs_str}\n"
                f"历史记忆: {memory_context}\n\n"
                "请输出严格 JSON: {readiness_score(0-100), confidence(0-1), "
                "risk_tags(数组), evidence(数组), missing_fields(数组), decision(pass/reject/review)}"
            ),
            "expected_output": "严格 JSON 对象",
        },
        "CohabitationRiskReview": {
            "agent_factory": lambda: get_cohabitation_risk_agent(llm),
            "description": (
                f"你正在独立评审一份领养申请，请从居住环境与共处风险角度出发。\n"
                f"目标宠物: {target_pet_name} ({target_species})\n"
                f"申请人信息: {applicant_info}\n"
                f"住房类型: {housing_type}\n"
                f"原住宠物: {existing_pets}\n"
                f"养宠经验: {'有' if has_pet_experience else '无'}\n"
                f"知识参考: {knowledge_context}\n\n"
                "请输出严格 JSON: {readiness_score(0-100), confidence(0-1), "
                "risk_tags(数组), evidence(数组), missing_fields(数组), decision(pass/reject/review)}"
            ),
            "expected_output": "严格 JSON 对象",
        },
    }

    # 并行执行三个独立评审
    contracts: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for name, config in review_configs.items():
            agent = config["agent_factory"]()
            future = executor.submit(
                _run_single_crew,
                agent,
                config["description"],
                config["expected_output"],
            )
            futures[future] = name

        for future in as_completed(futures):
            name = futures[future]
            try:
                raw_output = future.result(timeout=120)
                contracts[name] = _parse_contract_from_raw(raw_output, name)
            except Exception as e:
                logger.error(f"评审超时或异常 [{name}]: {e}")
                contracts[name] = _parse_contract_from_raw("", name, fallback_score=60)

    return contracts


# ============================================================
# 2. 委员会表决（非简单平均，带分歧检测）
# ============================================================

def committee_vote(contracts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    委员会表决算法：
    1. 收集所有 contract 的 score
    2. 计算加权平均（按 confidence 加权）
    3. 计算分歧度（最大分差 / 100）
    4. 合并 risk_tags, evidence, missing_fields
    5. 决定是否需要触发仲裁
    """
    scores = []
    confidences = []
    all_risk_tags = []
    all_evidence = []
    all_missing = []
    recommendations = []

    for name, contract in contracts.items():
        scores.append(contract["score"])
        confidences.append(contract["confidence"])
        all_risk_tags.extend(contract.get("risk_tags", []))
        all_evidence.extend(contract.get("evidence", []))
        all_missing.extend(contract.get("missing_fields", []))
        recommendations.append(contract.get("recommendation", "publisher_review"))

    # 加权平均（按 confidence 加权）
    total_weight = sum(confidences) or 1.0
    weighted_score = sum(s * c for s, c in zip(scores, confidences)) / total_weight
    weighted_score = int(max(0, min(100, round(weighted_score))))

    # 分歧度
    disagreement = (max(scores) - min(scores)) / 100 if scores else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

    # 去重
    unique_tags = list(dict.fromkeys(str(t) for t in all_risk_tags if t))[:8]
    unique_evidence = list(dict.fromkeys(str(e) for e in all_evidence if e))[:8]
    unique_missing = list(dict.fromkeys(str(m) for m in all_missing if m))[:6]

    # 投票裁决
    reject_count = recommendations.count("reject_candidate")
    review_count = recommendations.count("manual_review")
    if reject_count >= 2:
        vote_decision = "reject"
    elif reject_count >= 1 and weighted_score < 55:
        vote_decision = "reject"
    elif review_count >= 2 or disagreement >= 0.30:
        vote_decision = "review_required"
    elif weighted_score >= 75:
        vote_decision = "pass"
    elif weighted_score >= 55:
        vote_decision = "conditional_pass"
    else:
        vote_decision = "review_required"

    # 是否需要仲裁
    needs_mediation = disagreement >= 0.25

    return {
        "weighted_score": weighted_score,
        "disagreement": round(disagreement, 3),
        "avg_confidence": round(avg_confidence, 3),
        "vote_decision": vote_decision,
        "needs_mediation": needs_mediation,
        "risk_tags": unique_tags,
        "evidence": unique_evidence,
        "missing_fields": unique_missing,
        "individual_scores": {name: c["score"] for name, c in contracts.items()},
        "individual_recommendations": {name: c.get("recommendation") for name, c in contracts.items()},
    }


# ============================================================
# 3. 分歧仲裁智能体（仅在 needs_mediation 时触发）
# ============================================================

def run_conflict_mediation(
    llm,
    contracts: Dict[str, Dict[str, Any]],
    vote_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    分歧仲裁：分析各专家意见不一致的根因，给出最终裁决。
    只在分歧度超过阈值时被调用。
    """
    mediator = Agent(
        role="领养评估分歧仲裁官",
        goal="分析多位评审专家的意见分歧，找出根因，给出公正的最终裁决。",
        backstory=(
            "你是一名资深的动物福利仲裁专家。当多位评审专家意见不一致时，"
            "你的职责是：\n"
            "1. 识别分歧的具体维度（经济？经验？环境？）\n"
            "2. 分析分歧根因（信息解读不同？权重偏好不同？证据缺失？）\n"
            "3. 给出仲裁裁决：最终应采纳谁的意见，以及理由\n"
            "4. 如果分歧源于信息不足，指出需要补充什么"
        ),
        llm=llm,
        verbose=True,
        max_iter=3,
        allow_delegation=False,
    )

    # 构造各专家的意见摘要
    expert_opinions = []
    for name, contract in contracts.items():
        expert_opinions.append(
            f"【{name}】评分: {contract['score']}/100, "
            f"建议: {contract.get('recommendation')}, "
            f"置信度: {contract.get('confidence')}, "
            f"风险标签: {contract.get('risk_tags', [])}, "
            f"证据: {contract.get('evidence', [])[:3]}"
        )

    opinions_text = "\n".join(expert_opinions)
    score_spread = vote_result["disagreement"]

    task_desc = (
        f"以下是三位独立评审专家对同一份领养申请的评估结果：\n\n"
        f"{opinions_text}\n\n"
        f"分歧度: {score_spread:.1%} (阈值: 25%)\n"
        f"委员会初步投票: {vote_result['vote_decision']}\n\n"
        "请分析分歧原因并输出严格 JSON：\n"
        "{mediation_score(0-100), final_decision(pass/reject/review/followup), "
        "conflict_reason(字符串-分歧根因), adopted_opinion(采纳哪位专家), "
        "rejected_opinions(被否决的专家及理由), additional_questions(需补充的问题数组)}"
    )

    raw = _run_single_crew(mediator, task_desc, "严格 JSON 对象")
    mediation = _parse_contract_from_raw(raw, "ConflictMediationAgent", fallback_score=vote_result["weighted_score"])

    # 额外解析仲裁特有字段
    import re
    try:
        cleaned = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.S)
        if fenced:
            cleaned = fenced.group(1)
        else:
            brace = re.search(r"(\{.*\})", cleaned, re.S)
            if brace:
                cleaned = brace.group(1)
        data = json.loads(cleaned)
        mediation["conflict_reason"] = data.get("conflict_reason", "分歧原因未明确")
        mediation["adopted_opinion"] = data.get("adopted_opinion", "")
        mediation["additional_questions"] = data.get("additional_questions", [])
        if data.get("mediation_score"):
            mediation["score"] = max(0, min(100, int(float(data["mediation_score"]))))
        if data.get("final_decision"):
            decision = str(data["final_decision"]).lower()
            if "reject" in decision:
                mediation["recommendation"] = "reject_candidate"
            elif "review" in decision:
                mediation["recommendation"] = "manual_review"
            elif "followup" in decision:
                mediation["recommendation"] = "followup"
            else:
                mediation["recommendation"] = "publisher_review"
    except Exception:
        mediation["conflict_reason"] = "仲裁解析异常，以委员会投票为准"
        mediation["adopted_opinion"] = ""
        mediation["additional_questions"] = []

    return mediation


# ============================================================
# 4. 完整的评审委员会流程入口
# ============================================================

def run_committee_assessment(
    llm,
    *,
    applicant_info: str,
    target_species: str,
    target_pet_name: str,
    monthly_budget: float = 0,
    daily_companion_hours: float = 0,
    has_pet_experience: bool = False,
    housing_type: str = "apartment",
    application_reason: str = "",
    existing_pets: str = "",
    publisher_preferences: Optional[dict] = None,
    knowledge_context: str = "",
    memory_context: str = "",
) -> Dict[str, Any]:
    """
    完整的委员会评估流程：
      Phase 1 — 独立评审（3 个 Agent 并行）
      Phase 2 — 委员会表决
      Phase 3 — 分歧仲裁（仅在需要时触发）
    """
    start_time = time.time()

    # Phase 1: 独立评审
    contracts = run_independent_reviews(
        llm,
        applicant_info=applicant_info,
        target_species=target_species,
        target_pet_name=target_pet_name,
        monthly_budget=monthly_budget,
        daily_companion_hours=daily_companion_hours,
        has_pet_experience=has_pet_experience,
        housing_type=housing_type,
        application_reason=application_reason,
        existing_pets=existing_pets,
        publisher_preferences=publisher_preferences,
        knowledge_context=knowledge_context,
        memory_context=memory_context,
    )

    # Phase 2: 委员会表决
    vote_result = committee_vote(contracts)

    # Phase 3: 分歧仲裁（条件触发）
    mediation_result = None
    if vote_result["needs_mediation"]:
        logger.info(
            f"分歧度 {vote_result['disagreement']:.1%} 超过阈值，触发仲裁智能体"
        )
        mediation_result = run_conflict_mediation(llm, contracts, vote_result)
        # 仲裁结果覆盖委员会投票
        final_score = mediation_result["score"]
        final_decision = mediation_result.get("recommendation", vote_result["vote_decision"])
    else:
        final_score = vote_result["weighted_score"]
        final_decision = vote_result["vote_decision"]

    latency = round(time.time() - start_time, 2)

    # 组装最终结果
    risk_level = "Low" if final_score >= 75 else ("High" if final_score < 50 else "Medium")

    return {
        "readiness_score": final_score,
        "success_probability": round(final_score / 100 * 0.95, 2),
        "decision": final_decision,
        "risk_level": risk_level,
        "confidence_level": vote_result["avg_confidence"],
        "risk_factors": [
            {"dimension": tag, "description": tag, "severity": "medium"}
            for tag in vote_result["risk_tags"][:5]
        ],
        "recommendations": vote_result["evidence"][:4],
        "followup_questions": (
            mediation_result.get("additional_questions", [])
            if mediation_result
            else vote_result["missing_fields"][:3]
        ),
        "conflict_notes": (
            [mediation_result["conflict_reason"]]
            if mediation_result and mediation_result.get("conflict_reason")
            else []
        ),
        # 架构元数据
        "architecture": "independent_review_committee_voting",
        "phase1_contracts": contracts,
        "phase2_vote": vote_result,
        "phase3_mediation": mediation_result,
        "latency_seconds": latency,
        "final_summary": (
            f"## 评审委员会报告\n"
            f"**裁决: {final_decision} (综合评分: {final_score}/100)**\n"
            f"**分歧度: {vote_result['disagreement']:.1%}**\n"
            f"**仲裁: {'已触发' if mediation_result else '未触发'}**\n\n"
            f"### 各专家独立评分\n"
            + "\n".join(
                f"- {name}: {c['score']}分 (建议: {c.get('recommendation')})"
                for name, c in contracts.items()
            )
            + (
                f"\n\n### 仲裁结论\n{mediation_result.get('conflict_reason', '')}"
                if mediation_result
                else ""
            )
        ),
    }
