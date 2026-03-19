import json
import uuid
import time
from typing import Dict, List, Any
from src.web.services.db_service import get_db
from src.web.services.ai_service import ai_service

class AdoptionAssessmentService:
    """
    领养决策支持引擎 (Innovation Point 1 & 2)
    实现：规则硬约束 + LLM 语义推理 + 风险标签化
    """
    def __init__(self):
        self.rules = {
            "min_monthly_budget": 200, # 基础生活费门槛
            "min_companion_hours": 2,   # 每日最低陪伴时长
            "blacklist_check": True     # 是否启用黑名单核验
        }

    async def run_full_assessment(self, user_id: int, applicant_data: Dict) -> Dict:
        trace_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 1. 规则层：硬约束预筛 (Rule-based Pre-screening)
        # 这一步体现了系统的不盲目依赖AI，保证了决策的稳定性
        rule_result = self._check_hard_rules(applicant_data)
        if not rule_result["passed"]:
            return self._format_response(rule_result, "Rule_Engine", trace_id, start_time)

        # 2. LLM 层：多维度语义推理 (LLM-based Reasoning)
        # 调用 AI 分析用户的领养动机、心理准备度和潜在冲突
        ai_analysis = await self._run_ai_reasoning(applicant_data)
        
        # 3. 风险评分与置信度计算 (Quantification)
        final_decision = self._merge_results(rule_result, ai_analysis)
        
        # 4. 写入审计日志 (Audit Traceability - Innovation Point 4)
        self._log_audit(user_id, trace_id, applicant_data, final_decision)
        
        return self._format_response(final_decision, "Hybrid_Engine", trace_id, start_time)

    def _check_hard_rules(self, data: Dict) -> Dict:
        """规则引擎判定"""
        flags = []
        is_passed = True
        
        if data.get("monthly_budget", 0) < self.rules["min_monthly_budget"]:
            flags.append("经济能力可能无法覆盖基础养护支出")
            is_passed = False
            
        if data.get("daily_companion_hours", 0) < self.rules["min_companion_hours"]:
            flags.append("每日陪伴时间严重不足")
            is_passed = False
            
        return {
            "passed": is_passed,
            "rule_flags": flags,
            "base_score": 100 if is_passed else 40
        }

    async def _run_ai_reasoning(self, data: Dict) -> Dict:
        """LLM 语义风险识别"""
        prompt = f"""
        请作为宠物心理与福利专家，评估以下领养申请人的隐性风险。
        申请数据: {json.dumps(data, ensure_ascii=False)}
        
        请从以下维度分析并给出 0-1 的得分：
        1. 动机纯正度 (motivation): 是否存在冲动领养、虐待倾向或短期玩乐心态。
        2. 环境匹配度 (environment): 居住环境（如租房稳定性）与宠物的契合度。
        3. 责任感模型 (responsibility): 对宠物患病、调皮等负面情况的容忍度。
        
        请输出 JSON 格式：
        {{
            "scores": {{"motivation": 0.x, "environment": 0.x, "responsibility": 0.x}},
            "risk_tags": ["风险标签1", "风险标签2"],
            "summary": "专家分析摘要",
            "confidence_level": 0.x
        }}
        """
        response = await ai_service.ask(prompt)
        try:
            return json.loads(response)
        except:
            return {"scores": {"motivation": 0.5}, "risk_tags": ["解析异常"], "confidence_level": 0.3}

    def _merge_results(self, rule_res: Dict, ai_res: Dict) -> Dict:
        """结果融合算法"""
        # 加权计算准备度评分 (Readiness Score)
        ai_scores = ai_res.get("scores", {})
        avg_ai_score = sum(ai_scores.values()) / len(ai_scores) if ai_scores else 0.5
        
        readiness_score = (rule_res["base_score"] * 0.4) + (avg_ai_score * 100 * 0.6)
        
        decision = "Approved" if readiness_score >= 80 else ("Manual_Review" if readiness_score >= 60 else "Rejected")
        
        return {
            "readiness_score": round(readiness_score, 2),
            "decision": decision,
            "risk_tags": rule_res.get("rule_flags", []) + ai_res.get("risk_tags", []),
            "expert_summary": ai_res.get("summary", ""),
            "confidence_level": ai_res.get("confidence_level", 0.8)
        }

    def _log_audit(self, user_id, trace_id, input_data, result):
        """记录详细的决策追踪日志 (Traceability)"""
        with get_db() as conn:
            conn.execute('''
                INSERT INTO agent_trace_logs 
                (trace_id, endpoint, agent_name, input_msg, output_msg, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (trace_id, "adoption_assessment", "DecisionCoordinator", 
                  json.dumps(input_data), json.dumps(result), 0))
            conn.commit()

    def _format_response(self, result, engine, trace_id, start_time):
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "engine": engine,
                "trace_id": trace_id,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        }
