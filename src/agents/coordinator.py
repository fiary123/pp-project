import json
from typing import Dict, Any

class CoordinatorAgent:
    """
    顶层协调智能体 (The Brain)
    负责意图识别、状态管理、消息路由以及智能体间的数据传递。
    """
    def __init__(self, llm_service, db_session):
        self.llm = llm_service
        self.db = db_session
        
        # 假设我们已经有了以下专业子智能体 (后续可以按需导入实际类)
        # self.demand_agent = DemandUnderstandingAgent(llm_service)
        # self.match_agent = PetMatchingAgent(db_session)
        # self.audit_agent = AdoptionAuditAgent(llm_service)
        # self.wiki_agent = WikiAgent(llm_service)

    async def handle_user_input(self, session_id: str, user_id: int, user_message: str) -> Dict[str, Any]:
        """核心处理管道"""
        # 1. 读取当前会话状态
        context = self._get_session_context(session_id)
        
        # 2. 意图分类与状态路由
        if context.get("current_stage") == "auditing":
            # 如果当前明确在审核阶段，直接路由给审核智能体
            intent = "adoption_audit"
        elif context.get("current_stage") == "profiling":
            # 如果在偏好收集阶段，直接路由给需求智能体
            intent = "preference_collection"
        else:
            # 自由对话阶段，调用 LLM 进行意图识别
            intent = await self._classify_intent(user_message)

        # 3. 根据意图分发给特定的子智能体，并传递必要的结构化数据
        response_data = await self._route_to_agent(intent, user_message, context, user_id)
        
        # 4. 更新并持久化状态
        self._save_session_context(session_id, response_data["new_context"])
        
        # 返回给前端的最终响应
        return {
            "reply": response_data["reply"],
            "ui_actions": response_data.get("ui_actions", []), # 控制前端展现哪些卡片 (如宠物列表)
            "stage": response_data["new_context"].get("current_stage", "idle")
        }

    async def _classify_intent(self, message: str) -> str:
        """
        [步骤一] 意图识别：将用户的话分类到不同的技能路径
        """
        prompt = f"""
        你是一个宠物领养平台的中央调度员。请分析用户的输入，将其归类为以下意图之一：
        - "preference_collection": 表达对宠物的喜好，或描述自己的生活状态（如“我想养只猫”、“我一个人住”）。
        - "adoption_audit": 明确表达要申请领养某只具体的宠物。
        - "knowledge_qa": 询问养宠相关的知识或问题（如“布偶猫怎么养”、“狗吃什么好”）。
        - "general_chat": 无意义的闲聊或打招呼。
        
        用户输入: "{message}"
        请仅返回上述意图的英文关键字。
        """
        response = await self.llm.ask(prompt)
        return response.strip().lower()

    async def _route_to_agent(self, intent: str, message: str, context: Dict, user_id: int) -> Dict:
        """
        [步骤二 & 三] 读取状态 -> 调用子智能体 -> 接收结构化输出
        """
        new_context = context.copy()
        reply_text = ""
        ui_actions = []

        if intent == "preference_collection":
            # 路由到：需求理解智能体
            new_context["current_stage"] = "profiling"
            # 模拟调用: result = await self.demand_agent.process(message, context.get("preferences", {}))
            result = await self._mock_demand_agent(message, context)
            
            if result["is_complete"]:
                # 如果需求收集完成，自动流转到：匹配推荐智能体
                new_context["current_stage"] = "matching_done"
                new_context["preferences"] = result["preferences"]
                
                # 模拟调用: match_result = self.match_agent.match(result["preferences"])
                match_result = self._mock_match_agent(result["preferences"])
                
                reply_text = f"我已经完全了解您的需求了！结合您的画像（{result['preferences']['living_env']}，能陪伴{result['preferences']['time_budget']}），我为您找到了最匹配的几位毛孩子，请看推荐列表👇"
                ui_actions.append({"type": "show_pet_list", "data": match_result["pets"]})
            else:
                # 需求还不完整，返回追问
                new_context["preferences"] = result["preferences"]
                reply_text = result["follow_up_question"]

        elif intent == "adoption_audit":
            # 路由到：资质审核智能体
            new_context["current_stage"] = "auditing"
            target_pet = context.get("target_pet", "未知宠物")
            
            # 模拟调用审核逻辑
            reply_text = f"好的，您想要申请领养【{target_pet}】。为了对毛孩子负责，我们需要进行一个简短的评估。请问您家里封窗了吗？如果猫咪抓坏了沙发您会怎么处理？"

        elif intent == "knowledge_qa":
            # 路由到：百科知识智能体
            # 模拟调用: reply_text = await self.wiki_agent.answer(message)
            reply_text = "关于您问的知识，根据《宠物饲养百科》：..."
            new_context["current_stage"] = "idle" # 问答结束回到空闲态

        else:
            reply_text = "您好！我是您的宠物领养匹配官。您可以告诉我您想养什么宠物，或者描述一下您的生活状态，我帮您推荐~"

        return {
            "reply": reply_text,
            "ui_actions": ui_actions,
            "new_context": new_context
        }

    # --- 以下为模拟子智能体行为的 Mock 方法（实际应替换为真实的 Agent 类调用） ---
    
    async def _mock_demand_agent(self, message: str, context: Dict):
        """模拟需求理解智能体"""
        prefs = context.get("preferences", {})
        prompt = f"""
        你是一个宠物需求提取器。用户输入: "{message}"
        当前已有信息: {json.dumps(prefs)}
        请提取新信息并与已有信息合并。如果已知信息包含了居住环境(living_env)和每日陪伴时间(time_budget)，则标记 is_complete 为 true，否则生成一个追问(follow_up_question)。
        返回 JSON。
        """
        # 这里硬编码模拟 LLM 返回
        if "一个人住" in message or "上班" in message:
            return {
                "is_complete": False,
                "preferences": {"living_env": "公寓", "time_budget": "下班后"},
                "follow_up_question": "明白了，您是上班族。那您周末有时间带它出去玩吗？还是更希望它能在家里安静陪伴您？"
            }
        else:
            # 假设第二轮回答触发完成
            return {
                "is_complete": True,
                "preferences": {"living_env": "公寓", "time_budget": "周末有空", "energy_level": "安静"},
                "follow_up_question": ""
            }

    def _mock_match_agent(self, preferences: Dict):
        """模拟匹配推荐智能体"""
        return {
            "pets": [
                {"id": 1, "name": "布偶猫", "match_score": 92, "reason": "布偶猫性格安静，适合公寓饲养，能适应您上班时的独处。"},
                {"id": 2, "name": "英国短毛猫", "match_score": 88, "reason": "独立性强，不需要过多运动，非常契合您的时间预算。"}
            ]
        }

    # --- 状态持久化存取 ---
    def _get_session_context(self, session_id: str) -> Dict:
        # 实际项目中应从 Redis 或 数据库 (sessions 表) 读取
        # 这里用内存临时模拟
        if not hasattr(self, '_session_store'):
            self._session_store = {}
        return self._session_store.get(session_id, {"current_stage": "idle"})

    def _save_session_context(self, session_id: str, context: Dict):
        if not hasattr(self, '_session_store'):
            self._session_store = {}
        self._session_store[session_id] = context
