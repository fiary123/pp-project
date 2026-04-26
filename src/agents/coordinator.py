import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """
    顶层协调智能体（The Brain）
    负责：意图识别 → 会话状态管理 → 路由到对应子 Agent Crew → 返回结构化响应
    所有 Mock 方法已替换为真实 Agent/Crew 调用。
    """

    def __init__(self, llm_service, db_session):
        self.llm = llm_service
        self.db = db_session
        if not hasattr(self, '_session_store'):
            self._session_store: Dict[str, Dict] = {}

    # ─────────────────────────────────────────────────────────────────
    # 主入口
    # ─────────────────────────────────────────────────────────────────

    async def handle_user_input(
        self,
        session_id: str,
        user_id: int,
        user_message: str,
        followup_answers: dict | None = None,
        target_pet_name: str | None = None,
        target_species: str | None = None,
    ) -> Dict[str, Any]:
        """核心处理管道：读状态 → 意图分类 → 路由子 Agent → 更新状态"""
        context = self._get_session_context(session_id)

        # 将前端传入的补充信息写入上下文
        if followup_answers:
            prefs = context.get("preferences", {})
            prefs["followup_answers"] = followup_answers
            prefs["followup_done"] = True
            context["preferences"] = prefs
        if target_pet_name:
            context["target_pet"] = target_pet_name
        if target_species:
            context["target_species"] = target_species

        # 已处于明确阶段时直接路由，避免重复意图分类
        stage = context.get("current_stage", "idle")
        if stage == "profiling":
            intent = "preference_collection"
        elif stage == "auditing":
            intent = "adoption_audit"
        else:
            intent = await self._classify_intent(user_message)

        response_data = await self._route_to_agent(intent, user_message, context, user_id)
        self._save_session_context(session_id, response_data["new_context"])

        return {
            "reply":      response_data["reply"],
            "ui_actions": response_data.get("ui_actions", []),
            "stage":      response_data["new_context"].get("current_stage", "idle"),
        }

    # ─────────────────────────────────────────────────────────────────
    # 意图识别
    # ─────────────────────────────────────────────────────────────────

    async def _classify_intent(self, message: str) -> str:
        prompt = f"""你是宠物领养平台的中央调度员。请将用户输入归类为以下意图之一：
- preference_collection：表达对宠物的喜好，或描述自己的生活状态
- adoption_audit：明确申请领养某只具体宠物
- knowledge_qa：询问养宠相关知识
- general_chat：无意义的闲聊或打招呼

用户输入："{message}"
只返回上述意图的英文关键字，不要其他文字。"""
        try:
            response = await self.llm.ask(prompt)
            intent = response.strip().lower()
            valid = {"preference_collection", "adoption_audit", "knowledge_qa", "general_chat"}
            return intent if intent in valid else "general_chat"
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "general_chat"

    # ─────────────────────────────────────────────────────────────────
    # 路由分发
    # ─────────────────────────────────────────────────────────────────

    async def _route_to_agent(
        self, intent: str, message: str, context: Dict, user_id: int
    ) -> Dict:
        new_context = context.copy()
        reply_text = ""
        ui_actions: list = []

        # ── 偏好收集与宠物匹配 ───────────────────────────────────────
        if intent == "preference_collection":
            new_context["current_stage"] = "profiling"
            prefs = context.get("preferences", {})

            # 第一轮：生成追问（NeedAnalyzer Agent + generate_followup_questions 工具）
            if not prefs.get("followup_done"):
                try:
                    from src.agents.agents import run_match_followup
                    questions = run_match_followup(message)
                    new_context["preferences"] = {"initial_query": message}
                    new_context["followup_questions"] = questions
                    # 把追问拼成自然语言追问
                    q_texts = [f"{i+1}. {q['question']}" for i, q in enumerate(questions)]
                    reply_text = (
                        f"好的！我来帮您找最合适的宠物 🐾\n\n"
                        f"为了更精准地匹配，请回答以下几个问题：\n\n"
                        + "\n".join(q_texts)
                    )
                    ui_actions.append({"type": "show_followup_questions", "data": questions})
                except Exception as e:
                    logger.warning(f"run_match_followup failed: {e}")
                    reply_text = "您好！能告诉我您希望宠物是什么性格？以及您的居住环境大概是什么样的？"

            # 第二轮：收到追问答案后执行匹配（MatchScorer + MatchAdvisor Crew）
            else:
                initial_query = prefs.get("initial_query", message)
                followup_answers = prefs.get("followup_answers", {})
                try:
                    # 从数据库查询待领养宠物
                    pet_list = self._get_available_pets()
                    from src.agents.agents import run_smart_match
                    matches = run_smart_match(initial_query, pet_list, followup_answers)
                    new_context["current_stage"] = "matching_done"
                    new_context["last_matches"] = [m["id"] for m in matches]
                    reply_text = (
                        f"根据您的需求，我为您精选了以下宠物，请看推荐列表 👇\n"
                        f"（每只都附有匹配度分析和潜在挑战说明）"
                    )
                    ui_actions.append({"type": "show_pet_list", "data": matches})
                except Exception as e:
                    logger.warning(f"run_smart_match failed: {e}")
                    reply_text = "正在为您匹配合适的宠物，请稍候..."

        # ── 知识问答（KnowledgeRetriever + KnowledgeAdvisor Crew）────
        elif intent == "knowledge_qa":
            new_context["current_stage"] = "idle"
            try:
                from src.agents.agents import run_knowledge_expert
                reply_text = run_knowledge_expert(message)
            except Exception as e:
                logger.warning(f"run_knowledge_expert failed: {e}")
                reply_text = "知识库查询中，请稍候... 如急需帮助，可直接联系我们的客服。"

        # ── 领养资质评估（统一分级路由架构）──────────────────────────
        elif intent == "adoption_audit":
            new_context["current_stage"] = "auditing"
            target_pet = context.get("target_pet", "")
            try:
                from src.web.services.assessment_service import AdoptionAssessmentService
                
                # 构造符合 T1 路由协议的申请数据
                prefs = context.get("preferences", {})
                applicant_data = {
                    "applicant_info": message,
                    "target_species": context.get("target_species", "cat"),
                    "target_pet_name": target_pet or "未指定",
                    "monthly_budget": float(prefs.get("monthly_budget", 0)),
                    "daily_companion_hours": float(prefs.get("daily_companion_hours", 0)),
                    "has_pet_experience": bool(prefs.get("has_pet_experience", False)),
                    "housing_type": prefs.get("housing_type", "apartment"),
                    "existing_pets": prefs.get("existing_pets", ""),
                    "application_reason": message
                }

                # 调用统一服务（集成 T0 硬拦截、T1 分诊路由、T2 判例锚定及对抗辩论）
                service = AdoptionAssessmentService()
                result = await service.run_full_assessment(user_id=user_id, applicant_data=applicant_data)

                score = result.get("readiness_score", 0)
                tier = result.get("triage_tier", "DEEP_REVIEW")
                
                # 构造符合学术叙事的响应
                tier_label = {
                    "HARD_REJECT": "🚫 硬性拦截",
                    "FAST_TRACK": "⚡ 快速评估通道",
                    "DEEP_REVIEW": "🏛️ 专家委员会深度审议"
                }.get(tier, "🏛️ 专家委员会评审")

                reply_text = (
                    f"**领养资质评估完成**\n"
                    f"评估路径：{tier_label}\n"
                    f"准备度评分：**{score}/100**\n\n"
                    f"{result.get('summary', '评估结论已生成')}\n\n"
                    f"{result.get('final_summary', '')}"
                )
                new_context["current_stage"] = "audit_done"
                ui_actions.append({"type": "show_assessment_result", "data": result})
                new_context["last_score"] = score
            except Exception as e:
                logger.error(f"Coordinator audit logic failed: {e}")
                reply_text = "评估系统繁忙，请稍后再试或前往个人中心查看历史报告。"
                new_context["last_assessment"] = {"score": score, "decision": decision}
                ui_actions.append({"type": "show_assessment_result", "data": result})
            except Exception as e:
                logger.warning(f"run_adoption_assessment failed: {e}")
                reply_text = (
                    f"正在对您申请领养【{target_pet or '该宠物'}】进行资质评估，请描述一下您的居住环境和养宠经历，"
                    f"我们会尽快给出评估报告。"
                )

        # ── 通用对话 ─────────────────────────────────────────────────
        else:
            new_context["current_stage"] = "idle"
            reply_text = (
                "您好！我是您的宠物领养匹配官 🐾\n\n"
                "您可以：\n"
                "• 告诉我您的生活情况，我帮您推荐合适的宠物\n"
                "• 询问任何养宠相关的知识\n"
                "• 说出您想领养的宠物名称，我为您进行资质评估"
            )

        return {"reply": reply_text, "ui_actions": ui_actions, "new_context": new_context}

    # ─────────────────────────────────────────────────────────────────
    # 辅助方法
    # ─────────────────────────────────────────────────────────────────

    def _get_available_pets(self) -> list:
        """从数据库查询所有待领养宠物"""
        try:
            with self.db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, species, energy_level, is_shedding, description "
                    "FROM pets WHERE status = '待领养' LIMIT 30"
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"_get_available_pets failed: {e}")
            return []

    def _get_session_context(self, session_id: str) -> Dict:
        return self._session_store.get(session_id, {"current_stage": "idle"})

    def _save_session_context(self, session_id: str, context: Dict):
        self._session_store[session_id] = context
