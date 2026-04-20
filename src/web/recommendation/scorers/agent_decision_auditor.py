import asyncio
from src.agents.agents import analyze_pet_interview

class AgentDecisionAuditor:
    """
    推荐决策审计 Agent - 推荐链路的多智能体化重构核心
    在数值评分结束后，利用 LLM 对 Top 结果进行横向评审，给出更具说服力的推荐理由。
    """
    async def score(self, query, candidates):
        # 仅针对排序靠前的 3 位进行 Agent 复核，平衡性能与效果
        top_candidates = [c for c in candidates if c.final_score >= 60][:3]
        if not top_candidates:
            return candidates

        for candidate in top_candidates:
            pet = candidate.features.get("pet", {})
            profile = query.user_profile
            
            # 构建审计 Prompt 上下文
            audit_context = (
                f"领养人背景：{profile.get('housing_type')}居住，养宠经验{profile.get('pet_experience')}，"
                f"每日可用时间 {profile.get('available_time')}h。\n"
                f"目标宠物：{pet.get('species')}({pet.get('age_stage')})，性格：{pet.get('temperament_tags')}。\n"
                f"系统计算初分：{candidate.final_score}。"
            )

            try:
                # 调用 Agent 进行语义审计 (复用现有的分析逻辑)
                review = await analyze_pet_interview(
                    user_msg=f"作为资深动物福利官，请评价这个匹配度。上下文：{audit_context}",
                    pet_name="审计专家",
                    pet_species="系统",
                    pet_desc="内部推荐审计"
                )
                
                if not isinstance(review, dict):
                    continue

                # 将 Agent 评价注入推荐理由
                summary = review.get("summary")
                if summary and "画像" not in summary:
                    # 确保 summary 是字符串
                    summary_str = str(summary)
                    candidate.reasons.insert(0, f"专家点评：{summary_str}")
                
                # 如果 Agent 发现重大风险，扣除部分信用分（体现多智能体纠偏）
                risk_flags = review.get("risk_flags")
                if risk_flags:
                    candidate.final_score -= 5.0
                    # 健壮性修复：确保只有 list 才能 extend
                    if isinstance(risk_flags, list):
                        candidate.risk_flags.extend([str(flag) for flag in risk_flags])
                    elif isinstance(risk_flags, dict):
                        # 如果是 dict，尝试提取其中的值或作为单个条目
                        candidate.risk_flags.append(str(risk_flags))
                    else:
                        candidate.risk_flags.append(str(risk_flags))

            except Exception as e:
                print(f"DecisionAuditor: Agent review failed: {e}")

        return candidates
