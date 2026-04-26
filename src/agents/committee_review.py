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


from src.agents.agents import safe_parse_json

def _parse_contract_from_raw(raw: str, agent_name: str, fallback_score: int = 65) -> Dict[str, Any]:
    """
    [重构增强] 从 Agent 原始输出中解析标准化 contract。
    集成自愈能力，优先处理 JSON 结构，正则作为后备提取手段。
    """
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
        "case_reference": "未明确引用判例", # 新增判例溯源
    }
    
    if not raw:
        contract["evidence"] = ["评审未返回有效输出"]
        contract["confidence"] = 0.3
        return contract

    # 1. 使用工业级解析器进行提取
    data = safe_parse_json(raw)
    
    if not data:
        # 如果解析全量 JSON 失败，尝试正则提取分数作为最后兜底
        score_match = re.search(r'(?:score|评分|分数)[：:\s]*(\d+)', raw, re.I)
        if score_match:
            contract["score"] = max(0, min(100, int(score_match.group(1))))
        contract["evidence"] = ["由于输出格式非标准，系统仅提取了基础分值结论"]
        return contract

    # 2. 字段映射与双重校验 (Double Validation)
    try:
        # 分数归一化
        contract["score"] = int(float(data.get("readiness_score", data.get("score", fallback_score))))
        contract["score"] = max(0, min(100, contract["score"]))
        
        # 置信度校准
        contract["confidence"] = float(data.get("confidence", data.get("confidence_level", 0.72)))
        if contract["confidence"] > 1:
            contract["confidence"] = contract["confidence"] / 100
        
        # 风险标签清洗
        raw_tags = data.get("risk_tags", data.get("risk_factors", []))
        if isinstance(raw_tags, list):
            contract["risk_tags"] = [str(t.get("dimension", t) if isinstance(t, dict) else t) for t in raw_tags]
        
        # 依据与建议
        contract["evidence"] = data.get("evidence", data.get("recommendations", []))
        if isinstance(contract["evidence"], str):
            contract["evidence"] = [contract["evidence"]]
        
        # 问题追问
        contract["missing_fields"] = data.get("missing_fields", data.get("followup_questions", []))

        # 决策映射
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
        contract["case_reference"] = data.get("case_reference", "已参考历史案例但未给出具体差异点")
        
    except Exception as e:
        logger.warning(f"Contract normalization failed for {agent_name}: {e}")
        
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
    并行运行 3 个独立评审 Crew，每个专家均被注入【判例锚点】。
    """
    from .adoption_profiler import (
        get_encyclopedia_agent,
        get_adoption_profiler_agent,
        get_cohabitation_risk_agent,
    )

    prefs_str = json.dumps(publisher_preferences or {}, ensure_ascii=False)

    # 统一判例锚定指令
    anchoring_instruction = (
        f"--- 【关键参考资料 (Anchors)】 ---\n"
        f"1. 专业知识库: {knowledge_context}\n"
        f"2. 历史判例锚点: {memory_context}\n\n"
        "--- 【评审纪律】 ---\n"
        "你必须对比当前申请与【历史判例】的异同。在评分前请自问：\n"
        "- 相似的成功案例具备哪些此申请人也具备的特质？\n"
        "- 此申请人是否避开了相似失败案例中的关键红线？\n"
        "不得仅凭主观印象给分，必须有迹可循。\n"
    )

    review_configs = {
        "BreedBaselineReview": {
            "agent_factory": lambda: get_encyclopedia_agent(llm),
            "description": (
                f"你正在进行【品种适配性独立评审】。\n"
                f"目标宠物: {target_pet_name} ({target_species})\n"
                f"申请人背景: {applicant_info}\n"
                f"{anchoring_instruction}\n"
                "请输出严格 JSON: {readiness_score, confidence, evidence, case_reference, decision}"
            ),
            "expected_output": "包含 case_reference 的严格 JSON 对象",
        },
        "ProfileMatchReview": {
            "agent_factory": lambda: get_adoption_profiler_agent(llm),
            "description": (
                f"你正在进行【申请人画像匹配独立评审】。\n"
                f"申请理由: {application_reason}\n"
                f"送养人偏好: {prefs_str}\n"
                f"{anchoring_instruction}\n"
                "请输出严格 JSON: {readiness_score, confidence, evidence, case_reference, decision}"
            ),
            "expected_output": "包含 case_reference 的严格 JSON 对象",
        },
        "CohabitationRiskReview": {
            "agent_factory": lambda: get_cohabitation_risk_agent(llm),
            "description": (
                f"你正在进行【多宠共处与环境风险独立评审】。\n"
                f"住房类型: {housing_type} | 原住宠物: {existing_pets}\n"
                f"{anchoring_instruction}\n"
                "请输出严格 JSON: {readiness_score, confidence, evidence, case_reference, decision}"
            ),
            "expected_output": "包含 case_reference 的严格 JSON 对象",
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


def run_agent_reflection(
    llm,
    agent_name: str,
    original_contract: Dict[str, Any],
    opponent_contract: Dict[str, Any],
    context: str
) -> Dict[str, Any]:
    """
    [创新机制] 智能体自我反思：根据立场（高分/低分）进行对立辩论，修正原始评估。
    """
    from .adoption_profiler import (
        get_encyclopedia_agent,
        get_adoption_profiler_agent,
        get_cohabitation_risk_agent,
    )
    
    factory_map = {
        "BreedBaselineReview": get_encyclopedia_agent,
        "ProfileMatchReview": get_adoption_profiler_agent,
        "CohabitationRiskReview": get_cohabitation_risk_agent,
    }
    
    agent_factory = factory_map.get(agent_name)
    if not agent_factory:
        return original_contract
        
    agent = agent_factory(llm)
    
    # 动态构建辩论立场
    is_optimist = original_contract['score'] >= opponent_contract['score']
    
    if is_optimist:
        debate_role_instruction = (
            f"作为【匹配辩护方】，你给出了高分 ({original_contract['score']})，"
            f"而对手专家 ({opponent_contract['agent_name']}) 却给出了低分 ({opponent_contract['score']}) 并提出风险点：{opponent_contract.get('risk_tags', [])}。\n"
            "你的任务：\n"
            "1. 评估对手的质疑是否属于『过度警觉』或对该品种特性的误解。\n"
            "2. 说明为什么申请人的优势（如预算或经验）足以覆盖这些风险。\n"
        )
    else:
        debate_role_instruction = (
            f"作为【风险质疑方】，你表现得非常审慎 ({original_contract['score']})，"
            f"但对手专家 ({opponent_contract['agent_name']}) 却给出了高分 ({opponent_contract['score']}) 并认为：{opponent_contract.get('evidence', [])[:2]}。\n"
            "你的任务：\n"
            "1. 揭示对手是否被申请人的『理想化描述』所误导。\n"
            "2. 针对目标宠物的具体习性，指出如果由于这些细节疏忽，可能导致的弃养后果。\n"
        )

    debate_prompt = (
        f"--- 辩论上下文 ---\n"
        f"{context}\n\n"
        f"--- 对手意见摘要 ---\n"
        f"对方评分: {opponent_contract['score']} | 核心理由: {opponent_contract.get('evidence', ['未提供'])[-1]}\n\n"
        f"--- 你的辩论任务 ---\n"
        f"{debate_role_instruction}\n"
        "请进行深度反思，并输出最终 JSON: {readiness_score, reflection_notes, counter_arguments, revised_decision}"
    )
    
    raw = _run_single_crew(agent, debate_prompt, "严格 JSON 对象")
    reflected_data = safe_parse_json(raw)
    
    if reflected_data:
        new_contract = original_contract.copy()
        new_contract["score"] = int(reflected_data.get("readiness_score", original_contract["score"]))
        new_contract["evidence"].append(f"【辩论记录】: {reflected_data.get('reflection_notes', '无')}")
        new_contract["is_reflected"] = True
        new_contract["debate_logic"] = reflected_data.get("counter_arguments", "")
        return new_contract
    
    return original_contract

def run_debate_round(
    llm,
    contracts: Dict[str, Dict[str, Any]],
    context: str
) -> Dict[str, Dict[str, Any]]:
    """
    [多智能体辩论] 挑选分歧最大的两方进行交叉质询。
    """
    sorted_agents = sorted(contracts.items(), key=lambda x: x[1]["score"])
    low_agent_name, low_contract = sorted_agents[0]
    high_agent_name, high_contract = sorted_agents[-1]
    
    logger.info(f"触发辩论：{low_agent_name} (低分) vs {high_agent_name} (高分)")
    
    # 并行让两方反思
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_agent_reflection, llm, low_agent_name, low_contract, high_contract, context)
        f2 = executor.submit(run_agent_reflection, llm, high_agent_name, high_contract, low_contract, context)
        
        contracts[low_agent_name] = f1.result()
        contracts[high_agent_name] = f2.result()
        
    return contracts


# ============================================================
# 3. 分歧仲裁智能体（仅在 needs_mediation 时触发）
# ============================================================

def run_conflict_mediation(
    llm,
    contracts: Dict[str, Dict[str, Any]],
    vote_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    分歧仲裁：分析各专家意见及辩论反思过程，给出最终裁决。
    """
    mediator = Agent(
        role="领养评估分歧仲裁官",
        goal="分析专家间的辩论博弈轨迹，识别谁的逻辑在反思中表现出更高的理性度与一致性，产出最终决策。",
        backstory=(
            "你是一名具备高级逻辑分析能力的动物保护法学专家。你的独特之处在于你不看分数，而是看『论证质量』。"
            "如果一名专家在辩论后修正了分数，说明其具有自省能力，你要赋予其更高的权重。"
            "如果双方僵持不下，你要判断风险质疑方的『红旗指标』是否属于不可撤销的一票否决项。"
        ),
        llm=llm,
        verbose=True,
        max_iter=3,
        allow_delegation=False,
    )

    # 构造各专家的意见摘要（包含反思状态）
    expert_opinions = []
    for name, contract in contracts.items():
        ref_status = " [已完成反思与修正]" if contract.get("is_reflected") else ""
        expert_opinions.append(
            f"【{name}{ref_status}】\n"
            f"- 最终分值: {contract['score']}\n"
            f"- 核心逻辑: {contract.get('debate_logic', '无')}\n"
            f"- 反思结论: {contract.get('evidence', [])[-1:]}\n"
        )

    opinions_text = "\n".join(expert_opinions)
    score_spread = vote_result["disagreement"]

    task_desc = (
        f"以下是三位评审专家在经历【对抗性辩论与反思】后的最终评估结果：\n\n"
        f"{opinions_text}\n\n"
        f"初始最大分歧度: {score_spread:.1%}\n"
        f"委员会初步投票意向: {vote_result['vote_decision']}\n\n"
        "请作为最高仲裁官，根据辩论后的逻辑链输出严格 JSON：\n"
        "{mediation_score(0-100), final_decision(pass/reject/review/followup), "
        "conflict_reason(字符串-为什么产生分歧), key_insight_from_debate(辩论中最关键的发现), "
        "additional_questions(需补充的问题数组)}"
    )

    raw = _run_single_crew(mediator, task_desc, "严格 JSON 对象")
    mediation = _parse_contract_from_raw(raw, "ConflictMediationAgent", fallback_score=vote_result["weighted_score"])

    # 解析仲裁特有字段
    data = safe_parse_json(raw)
    if data:
        mediation["conflict_reason"] = data.get("conflict_reason", "分歧原因未明确")
        mediation["key_insight"] = data.get("key_insight_from_debate", "")
        mediation["additional_questions"] = data.get("additional_questions", [])
        if data.get("mediation_score"):
            mediation["score"] = max(0, min(100, int(float(data["mediation_score"]))))
        
        # 决策映射
        decision = str(data.get("final_decision", "")).lower()
        if "reject" in decision:
            mediation["recommendation"] = "reject_candidate"
        elif "review" in decision:
            mediation["recommendation"] = "manual_review"
        elif "followup" in decision:
            mediation["recommendation"] = "followup"
        else:
            mediation["recommendation"] = "publisher_review"
            
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
    完整的委员会评估流程（辩论反思增强版）：
      Phase 1 — 独立评审（3 个 Agent 并行）
      Phase 2 — 分歧检测与多轮辩论反思
      Phase 3 — 委员会表决与终极仲裁
    """
    start_time = time.time()
    
    context_summary = (
        f"目标宠物: {target_pet_name}({target_species}), "
        f"申请人: {applicant_info}, 预算:{monthly_budget}, "
        f"经验:{'有' if has_pet_experience else '无'}, 住房:{housing_type}"
    )

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

    # Phase 2: 分歧初步检测
    vote_result = committee_vote(contracts)

    # [核心机制] 触发辩论与反思 (Conflict-Driven Reflection)
    if vote_result["needs_mediation"]:
        logger.info(f"分歧度 {vote_result['disagreement']:.1%} 较高，启动【多智能体辩论与反思】机制")
        contracts = run_debate_round(llm, contracts, context_summary)
        # 辩论后重新计算投票结果
        vote_result = committee_vote(contracts)

    # Phase 3: 最终仲裁（如果辩论后依然需要仲裁，或者为了产出最终一致性报告）
    mediation_result = None
    if vote_result["needs_mediation"]:
        logger.info("进入仲裁裁决环节...")
        mediation_result = run_conflict_mediation(llm, contracts, vote_result)
        final_score = mediation_result["score"]
        final_decision = mediation_result.get("recommendation", vote_result["vote_decision"])
    else:
        final_score = vote_result["weighted_score"]
        final_decision = vote_result["vote_decision"]

    latency = round(time.time() - start_time, 2)
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
        "architecture": "multi_agent_debate_reflection_v2",
        "phase1_contracts": contracts,
        "phase2_vote": vote_result,
        "phase3_mediation": mediation_result,
        "latency_seconds": latency,
        "final_summary": (
            f"## 评审委员会报告 (MADR 辩论增强版)\n"
            f"**最终裁决: {final_decision} (综合得分: {final_score}/100)**\n"
            f"**分歧度: {vote_result['disagreement']:.1%}**\n"
            f"**机制状态: {'已执行对抗性辩论' if vote_result.get('needs_mediation') or mediation_result else '共识达成，无需辩论'}**\n\n"
            f"### 各专家评分及反思快照\n"
            + "\n".join(
                f"- {name}: {c['score']}分 (建议: {c.get('recommendation')}) {'[已执行反思修正]' if c.get('is_reflected') else ''}"
                for name, c in contracts.items()
            )
            + (
                f"\n\n### 仲裁核心见解\n{mediation_result.get('key_insight', mediation_result.get('conflict_reason', ''))}"
                if mediation_result
                else ""
            )
        ),
    }

