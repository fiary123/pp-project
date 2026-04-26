import asyncio
import json
import uuid
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from src.web.services.db_service import get_db, ensure_tables
from src.web.services.adoption_flow_engine import flow_engine

logger = logging.getLogger(__name__)

class AdoptionAssessmentService:
    """
    领养资质评估服务 (Lifecycle Management)
    负责驱动整个评估生命周期：从申请收集、规则预筛、Agent委员会评审到最终决策记录。
    """
    
    def __init__(self):
        # 确保相关表已初始化
        with get_db() as conn:
            ensure_tables(conn)

    async def _before_stage(self, trace_id: str, stage: str, payload: Any):
        logger.info(f"[Assessment] Trace:{trace_id} Entering Stage:{stage}")

    async def _after_stage(self, trace_id: str, stage: str, result: Any):
        logger.info(f"[Assessment] Trace:{trace_id} Finished Stage:{stage}")

    def _check_hard_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """L1 物理约束/硬规则过滤"""
        budget = float(data.get("monthly_budget", 0))
        if budget < 100:
            return {"passed": False, "reason": "养宠预算过低(最低要求100元/月)"}
        return {"passed": True}

    def _blocked_response(self, rule_result, data, trace_id, started_at, lifecycle):
        return {
            "readiness_score": 0,
            "decision": "reject",
            "risk_level": "High",
            "risk_factors": [{"dimension": "rule", "description": rule_result["reason"]}],
            "recommendations": ["解决硬拦截约束后再尝试"],
            "summary": f"评估未通过：{rule_result['reason']}",
            "trace_id": trace_id,
            "latency": int((time.time() - started_at) * 1000),
            "lifecycle": lifecycle
        }

    def _build_knowledge_context(self, data: Dict[str, Any]) -> str:
        """[核心增强] 接入 RAG：从 ChromaDB 检索针对该宠物特性的专业养护知识"""
        try:
            from src.agents.tools import search_pet_knowledge_hits
            query = f"{data.get('target_species', '')} {data.get('target_pet_name', '')} 养护要点 常见疾病"
            hits = search_pet_knowledge_hits(query, limit=2)
            if hits:
                knowledge_text = "\n".join([f"- {h['text']}" for h in hits])
                return f"【专业知识库参考】\n{knowledge_text}"
        except Exception as e:
            logger.warning(f"Knowledge retrieval failed: {e}")
        return "基于通用养宠常识进行评估。"

    def _build_memory_context(self, user_id: int, data: Dict[str, Any]) -> str:
        """[核心增强] 接入 Memory：从历史案例库中寻找相似结局参考"""
        try:
            from src.web.services.adoption_memory import memory_service
            # 使用当前领养人特征寻找历史相似案例
            similar_cases = memory_service.retrieve_similar_cases(current_data=data, limit=2)
            if similar_cases:
                memory_text = ""
                for case in similar_cases:
                    outcome = "成功且满意度高" if case.get('decision_result') == 'success' else "存在挑战或反馈一般"
                    memory_text += f"- 案例参考(ID:{case['application_id']}): 背景:{case['case_summary'][:60]}... 最终结局:{outcome}\n"
                return f"【历史相似案例参考】\n{memory_text}"
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
        return "暂无相似历史先例参考。"

    def _log_audit(self, user_id: int, trace_id: str, input_data: Any, output_data: Any):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO agent_trace_logs 
                   (trace_id, user_id, endpoint, input_msg, output_msg, latency_ms) 
                   VALUES (?,?,?,?,?,?)""",
                (
                    trace_id, 
                    user_id, 
                    'adoption_assessment', # [核心修复] 补全统计契约字段
                    json.dumps(input_data, ensure_ascii=False), 
                    json.dumps(output_data, ensure_ascii=False), 
                    output_data.get("latency", 0)
                )
            )
            conn.commit()

    def _build_memory_context_from_cases(self, cases: List[Dict[str, Any]], signal: Dict[str, Any]) -> str:
        """从检索到的案例和信号中构建 AI 可读的记忆上下文"""
        if not cases:
            return "暂无相似历史先例参考。"
        
        memory_text = f"【历史相似案例统计】正向反馈: {signal.get('positive_count', 0)}, 负向反馈: {signal.get('negative_count', 0)}\n"
        for case in cases:
            outcome = "成功且满意度高" if case.get('decision_result') == 'success' else "存在挑战或反馈一般"
            memory_text += f"- 案例(ID:{case['application_id']}): 关键特征:{case['case_summary'][:80]}... 最终结局:{outcome}\n"
        return memory_text

    async def _run_fast_track(self, applicant_data: Dict[str, Any], triage: Dict[str, Any]) -> Dict[str, Any]:
        """[路径 A] 快速通过评估路径：使用轻量级单智能体进行验证"""
        logger.info("Executing AI-powered Fast Track assessment path.")
        
        from src.agents.agents import analyze_pet_interview
        
        # 执行真实的 AI 初审扫描
        lite_scan = await analyze_pet_interview(
            user_msg=f"核心申请背景：{applicant_data.get('applicant_info', '')}",
            pet_name=applicant_data.get("target_pet_name", "宠物"),
            pet_species=applicant_data.get("target_species", "dog"),
            pet_desc="快速通过路径验证模式"
        )
        
        score = lite_scan.get("readiness_score", 90)
        
        return {
            "readiness_score": score,
            "risk_level": "Low",
            "decision": "pass",
            "summary": f"【系统快速评估】{lite_scan.get('summary', '申请人指标优异，符合直接通过标准。')}",
            "architecture": "Adaptive-Fast-Track-v2",
            "confidence_level": 0.95,
            "phase1_contracts": {
                "FastTrackRouter": {
                    "agent_name": "分诊路由器",
                    "score": score,
                    "recommendation": "pass",
                    "evidence": triage["route_reason"],
                    "risk_tags": lite_scan.get("risk_flags", []),
                    "confidence": 0.95
                }
            },
            "phase2_vote": {
                "vote_decision": "pass",
                "weighted_score": score,
                "disagreement": 0.0,
                "avg_confidence": 0.95,
                "needs_mediation": False
            },
            "phase3_mediation": None,
        }

    async def _run_deep_review(self, applicant_data: Dict[str, Any], knowledge: str, memory: str) -> Dict[str, Any]:
        """[路径 B] 深度专家委员会评估路径"""
        logger.info("Escalating to Deep Committee Review path.")
        from src.agents.agents import adoption_llm
        from src.agents.committee_review import run_committee_assessment
        
        result = await asyncio.to_thread(
            run_committee_assessment,
            adoption_llm,
            applicant_info=applicant_data.get("applicant_info", ""),
            target_species=applicant_data.get("target_species", "dog"),
            target_pet_name=applicant_data.get("target_pet_name", "宠物"),
            monthly_budget=float(applicant_data.get("monthly_budget", 0)),
            daily_companion_hours=float(applicant_data.get("daily_companion_hours", 0)),
            has_pet_experience=bool(applicant_data.get("has_pet_experience", False)),
            housing_type=applicant_data.get("housing_type", "apartment"),
            application_reason=applicant_data.get("application_reason", ""),
            existing_pets=applicant_data.get("existing_pets", ""),
            publisher_preferences=applicant_data.get("publisher_preferences"),
            knowledge_context=knowledge,
            memory_context=memory
        )
        result["architecture"] = "Adaptive-Committee-Path"
        return result

    async def run_full_assessment(self, user_id: int, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        [主生命周期] 驱动分级评估 Pipeline。
        """
        from src.web.services.adoption_tier_router import route_adoption_tier
        from src.web.services.adoption_memory import (
            memory_service, 
            summarize_case_feedback_signal,
            build_case_anchor_context
        )
        
        trace_id = str(uuid.uuid4())
        started_at = time.time()
        
        try:
            # 1. 知识库 RAG 增强
            knowledge_context = self._build_knowledge_context(applicant_data)

            # 2. 相似案例记忆检索与【判例锚定】信号提取
            similar_cases = memory_service.retrieve_similar_cases(current_data=applicant_data, limit=3)
            memory_signal = summarize_case_feedback_signal(similar_cases)
            
            # 构建结构化锚点文本 (Case-based Anchoring)
            anchor_res = build_case_anchor_context(similar_cases, memory_signal)
            memory_context = anchor_res["case_anchor_text"]
            
            # 3. 动态分流分诊 (Triage)
            triage = route_adoption_tier(applicant_data, memory_signal, applicant_data.get("publisher_preferences"))
            tier = triage["tier"]
            
            # 4. 按 Tier 执行对应路径
            if tier == "HARD_REJECT":
                rule_result = {"passed": False, "reason": " | ".join(triage["route_reason"])}
                ai_result = self._blocked_response(rule_result, applicant_data, trace_id, started_at, ["prescreen"])
            
            elif tier == "FAST_TRACK":
                ai_result = await self._run_fast_track(applicant_data, triage)
            
            else:  # DEEP_REVIEW
                ai_result = await self._run_deep_review(applicant_data, knowledge_context, memory_context)
            
            # 5. [核心增强] 注入全生命周期元数据 (Observed Data)
            ai_result.update({
                "tier": tier,
                "triage_tier": tier, # 冗余保留兼容旧代码
                "tier_route": triage,
                "triage_reasons": triage["route_reason"],
                "case_signal": memory_signal,
                "case_anchors": similar_cases, # 保存相似案例快照以供溯源
                "architecture": "Dynamic-Tiered-Assessment",
                "trace_id": trace_id,
                "latency": int((time.time() - started_at) * 1000)
            })
            
            self._log_audit(user_id, trace_id, applicant_data, ai_result)
            return ai_result
            
        except Exception as e:
            logger.exception(f"Assessment Pipeline crashed: {e}")
            return {"readiness_score": 50, "decision": "manual_review", "summary": "内部链路异常"}

    async def start_application_evaluation(self, application_id: int):
        """异步深度评估并回写结果"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
            app_row = cursor.fetchone()
            if not app_row: return
            app_data = dict(app_row)
            
            payload = {}
            if app_data.get("assessment_payload"):
                try: payload = json.loads(app_data["assessment_payload"])
                except: pass
            
            # 执行评估
            result = await self.run_full_assessment(app_data["user_id"], payload)
            
            # 1. 路由与主动追问 (Proactive Probing)
            from src.web.services.adoption_router import uncertainty_router
            route = uncertainty_router(result, app_data.get("publisher_preferences"))
            
            # [核心修复] 统一状态映射：使用 flow_engine 将路由指令转换为业务状态名
            # route.next_action (如 followup) -> final_flow_status (如 need_more_info)
            final_flow_status = flow_engine.resolve_result_flow_status({"route_decision": route})
            
            prioritized_questions = route.get("prioritized_questions", [])
            
            # 2. [优化] 轻量级反事实模拟 (不再重跑 AI)
            cf_advice = ""
            current_score = result.get("readiness_score", 100)
            if current_score < 80:
                # 规则 A: 预算探测
                if float(payload.get("monthly_budget", 0)) < 500:
                    cf_advice = "💡 建议：如果月均预算能提升至 500 元以上，匹配分将有显著提升空间。"
                # 规则 B: 时间探测
                elif float(payload.get("daily_companion_hours", 0)) < 2.0:
                    cf_advice = "💡 提示：如果每日能多抽出 1-2 小时陪伴宠物，匹配专家将对您的申请更有信心。"
            
            summary = result.get("summary", "")
            if prioritized_questions:
                summary = f"【AI 建议追问】{prioritized_questions[0]} 等关键信息缺失。{summary}"
            if cf_advice:
                summary = f"{summary}\n\n{cf_advice}"

            # 3. 回写数据库
            cursor.execute(
                """UPDATE applications SET 
                   ai_summary = ?, ai_readiness_score = ?, risk_level = ?, 
                   flow_status = ?, followup_questions = ?,
                   assessment_tier = ?, route_reasons = ?
                   WHERE id = ?""",
                (
                    summary, 
                    result.get("readiness_score", 0), 
                    result.get("risk_level", "Medium"), 
                    final_flow_status, 
                    json.dumps(prioritized_questions, ensure_ascii=False),
                    result.get("triage_tier"),
                    json.dumps(result.get("triage_reasons", []), ensure_ascii=False),
                    application_id
                )
            )
            
            # [核心修复] 补全 AI 详细审计报告字段，支持统计与前端深度展示
            vote_data = result.get("phase2_vote") or {}
            cursor.execute(
                """INSERT INTO adoption_ai_reviews 
                   (application_id, trace_id, agent_outputs_json, ai_readiness_score, overall_score, 
                    consensus_score, disagreement_score, risk_level, ai_summary, route_decision) 
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    application_id, 
                    result["trace_id"], 
                    json.dumps(result, ensure_ascii=False), 
                    result.get("readiness_score", 0),
                    result.get("readiness_score", 0), # overall_score 冗余存储以兼容旧统计
                    float(vote_data.get("avg_confidence", 0)),
                    float(vote_data.get("disagreement", 0)),
                    result.get("risk_level"),
                    summary,
                    json.dumps(route, ensure_ascii=False)
                )
            )
            
            flow_engine.append_event(
                conn, application_id=application_id, event_type="FINISH_EVALUATION",
                from_status="evaluating", to_status=final_flow_status,
                actor_role="system", payload={"trace_id": result["trace_id"], "route": final_flow_status}
            )
            conn.commit()

    async def re_evaluate_application(self, application_id: int, supplemental_data: Dict[str, Any]):
        """补资料后重评闭环"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
            app_row = cursor.fetchone()
            if not app_row: return
            app_data = dict(app_row)
            
            original_payload = {}
            if app_data.get("assessment_payload"):
                try: original_payload = json.loads(app_data["assessment_payload"])
                except: pass
            
            merged_payload = {**original_payload, **supplemental_data}
            cursor.execute(
                "UPDATE applications SET assessment_payload = ?, flow_status = 'evaluating', status = 'evaluating' WHERE id = ?",
                (json.dumps(merged_payload, ensure_ascii=False), application_id)
            )
            
            flow_engine.append_event(
                conn, application_id=application_id, event_type="SUPPLEMENT_INFO",
                from_status=app_data.get("flow_status"), to_status="evaluating",
                actor_role="applicant", actor_id=app_data["user_id"], payload=supplemental_data
            )
            conn.commit()

        await self.start_application_evaluation(application_id)
