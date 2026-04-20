import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.web.services.db_service import get_db
from src.agents.adoption_profiler import AdoptionProfiler
from src.agents.agents import AdoptionCrew
from src.web.services.adoption_memory import build_case_summary, upsert_case_memory

logger = logging.getLogger(__name__)

class AdoptionAssessmentEngine:
    """
    领养评估多智能体核心引擎 (Thesis Core Engine)
    论文架构对应：规则预筛 -> 记忆增强 -> 专家协同 -> 共识裁决 -> 审计反馈
    """
    
    def __init__(self, user_id: int, config: Optional[Dict[str, bool]] = None):
        self.user_id = user_id
        self.trace_id = f"trace_{user_id}_{int(datetime.now().timestamp())}"
        self.profiler = AdoptionProfiler()
        self.crew = AdoptionCrew()
        # 实验配置：支持动态关闭某些层级以进行对比实验
        self.config = config or {
            "use_rules": True,
            "use_memory": True,
            "use_multi_agents": True,
            "use_consensus": True
        }

    async def run_pipeline(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行可配置的评估流水线"""
        start_time = datetime.now()
        
        # --- Layer 1: 规则预筛 ---
        screen_res = {"pass": True, "violations": []}
        if self.config.get("use_rules"):
            screen_res = self._layer_pre_screening(applicant_data)
            if not screen_res["pass"]:
                return self._wrap_result("Rules", screen_res, start_time)

        # --- Layer 2: 记忆增强 ---
        enriched_data = applicant_data
        if self.config.get("use_memory"):
            enriched_data = await self._layer_memory_hydration(applicant_data)

        # --- Layer 3 & 4: 专家协同与共识 ---
        if self.config.get("use_multi_agents"):
            # 完整模式：多 Agent 协作
            ai_output = await self.crew.run_assessment(enriched_data)
        else:
            # 基准模式：单模型直接预测 (模拟论文中的 Baseline)
            ai_output = await self._run_single_model_baseline(enriched_data)

        # --- Layer 5: 审计与反馈 ---
        final_report = self._layer_audit_generation(ai_output, screen_res)
        final_report["latency_ms"] = (datetime.now() - start_time).total_seconds() * 1000
        
        return final_report

    async def _run_single_model_baseline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """单模型基准对比逻辑"""
        # 模拟直接调用 LLM，不经过多 Agent 角色拆分与冲突检测
        return {
            "decision": "approved",
            "readiness_score": 75,
            "final_summary": "基于单模型分析，该申请人条件基本符合。"
        }

    def _layer_pre_screening(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """规则层：拦截明显的风险点"""
        violations = []
        if data.get("age", 25) < 18: violations.append("未成年人禁入")
        if data.get("monthly_budget", 500) < 50: violations.append("经济能力不足以维持基础养护")
        
        return {
            "pass": len(violations) == 0,
            "violations": violations,
            "timestamp": datetime.now().isoformat()
        }

    async def _layer_memory_hydration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """增强层：从长期记忆中提取该用户的历史评估偏好与相似案例"""
        with get_db() as conn:
            # 模拟从向量库或数据库提取相似案例结论
            cursor = conn.cursor()
            cursor.execute("SELECT case_summary, decision_result FROM adoption_case_memory WHERE application_id IN (SELECT id FROM applications WHERE user_id = ?) LIMIT 2", (self.user_id,))
            history = cursor.fetchall()
            data["interaction_history_summary"] = [dict(h) for h in history]
        return data

    def _layer_audit_generation(self, ai_output: Dict[str, Any], screen_res: Dict[str, Any]) -> Dict[str, Any]:
        """审计层：生成可解释的 Trace 数据"""
        report = {
            "trace_id": self.trace_id,
            "engine_version": "v4.2-MultiAgent",
            "decision": ai_output.get("decision", "rejected"),
            "readiness_score": ai_output.get("readiness_score", 0),
            "logic_chain": {
                "screening_stage": screen_res,
                "agent_collaboration": ai_output.get("expert_opinions", []),
                "consensus_reasoning": ai_output.get("final_summary", "")
            },
            "risk_level": ai_output.get("risk_level", "Medium")
        }
        # 持久化审计快照
        self._persist_audit_log(report)
        return report

    def _persist_audit_log(self, report: Dict[str, Any]):
        """存入 agent_trace_logs 供论文实验分析使用"""
        with get_db() as conn:
            conn.execute(
                "INSERT INTO agent_trace_logs (trace_id, agent_name, output_msg) VALUES (?,?,?)",
                (self.trace_id, "AssessmentEngine", json.dumps(report, ensure_ascii=False))
            )
            conn.commit()

    def _wrap_result(self, stage: str, details: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "decision": "rejected",
            "readiness_score": 0,
            "message": f"评估在{stage}阶段被拦截",
            "details": details
        }
