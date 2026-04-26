import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def route_adoption_tier(
    applicant_data: Dict[str, Any], 
    memory_signal: Dict[str, Any], 
    publisher_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    [T1 动态分诊路由]
    职责：根据申请数据、历史判例锚点和发布者偏好，动态选择评估路径。
    
    返回结构：
    {
        "tier": "HARD_REJECT" | "FAST_TRACK" | "DEEP_REVIEW",
        "risk_score": float,
        "requires_committee": bool,
        "route_reason": List[str],
    }
    """
    # 提取核心指标
    budget = float(applicant_data.get("monthly_budget", 0) or 0)
    companion = float(applicant_data.get("daily_companion_hours", 0) or 0)
    info_text = str(applicant_data.get("applicant_info", "")).lower()
    has_experience = applicant_data.get("has_pet_experience", False)
    existing_pets = applicant_data.get("existing_pets", "")
    
    # 记忆信号解析 (RAG & Memory anchors)
    pos_cases = memory_signal.get("positive_count", 0)
    neg_cases = memory_signal.get("negative_count", 0)
    
    reasons = []
    
    # --- T0: HARD_REJECT (硬约束拦截) ---
    # 1. 经济红线
    if budget < 100:
        reasons.append("月预算 (¥{:.0f}) 低于宠物生存红线 (¥100)".format(budget))
        return _build_result("HARD_REJECT", 1.0, reasons)
    
    # 2. 政策/环境冲突关键词
    reject_keywords = ["禁止养宠", "房东拒绝", "不允许养", "宿舍", "偷偷养"]
    matched_keywords = [k for k in reject_keywords if k in info_text]
    if matched_keywords:
        reasons.append(f"环境合规性拦截：发现冲突词汇 {matched_keywords}")
        return _build_result("HARD_REJECT", 0.9, reasons)

    # --- T1: FAST_TRACK (快速通过路径) ---
    # 条件：高预算、充足陪伴、有经验、无原住宠冲突、历史判例正向、发布者非保守派
    is_conservative = (publisher_preferences or {}).get("style") == "conservative"
    
    if (budget >= 500 and 
        companion >= 2 and 
        has_experience and 
        not existing_pets and 
        pos_cases >= neg_cases and 
        not is_conservative):
        
        reasons = [
            "核心指标（预算/陪伴）远超基准",
            "具备既往养宠经验",
            "家庭环境简单（无原住宠冲突）",
            "历史相似案例整体偏正向"
        ]
        return _build_result("FAST_TRACK", 0.12, reasons, requires_committee=False)

    # --- T2: DEEP_REVIEW (深度委员会评审路径) ---
    if not has_experience:
        reasons.append("新手领养：需重点评估学习意愿与应急能力")
    if existing_pets:
        reasons.append(f"多宠环境：存在原住宠 ({existing_pets})，需评估社交兼容性")
    if is_conservative:
        reasons.append("送养人要求严格：触发高标准专家审计")
    if neg_cases > pos_cases:
        reasons.append("风险锚点命中：历史相似背景案例中存在负向偏离")
    if budget < 200 or companion < 1:
        reasons.append("指标接近临界值：需专家进行压力测试")
    
    # 兜底：如果没有任何特殊项，但也不满足 Fast Track，默认进入 Deep Review
    if not reasons:
        reasons.append("常规多维评估：综合指标处于中位区间")

    return _build_result("DEEP_REVIEW", 0.45, reasons, requires_committee=True)

def _build_result(tier: str, risk: float, reasons: List[str], requires_committee: bool = False) -> Dict[str, Any]:
    return {
        "tier": tier,
        "risk_score": round(risk, 2),
        "confidence": 0.92,
        "requires_committee": requires_committee,
        "route_reason": reasons,
    }
