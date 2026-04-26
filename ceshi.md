5.2.1 宠物档案与送养约束展示
领养申请的输入质量，直接影响后续评估结果的有效性。为减少明显不适配申请进入正式评估流程，系统在申请入口处先展示宠物档案、送养要求和特殊限制条件，再引导用户进入申请填写阶段。这样的处理方式并不是单纯增加展示内容，而是将原本隐含在审核阶段的约束前移到申请之前，使申请行为建立在充分知情的基础上，从源头上降低无效申请比例。
图5-1 宠物档案与送养约束展示页面
图注居中：图5-1 宠物档案与送养约束展示页面
在实现上，该环节依赖宠物特征、送养要求和宠物基础信息的联合读取，用于为后续动态问题生成和申请预筛提供统一输入基础。相关数据读取逻辑位于 src/web/routers/ai.py 中，对 pet_features、pet_requirements 和 pets 表进行查询处理。 
5.2.2 动态问题生成与分步填写
静态表单能够完成基础信息收集，但难以适应宠物差异、送养约束差异和申请人画像差异同时存在的场景。为此，系统在申请填写阶段引入了动态问题生成机制，根据宠物特征、送养要求以及用户画像中的信息缺口，自动生成针对性问题，并按照优先级组织为渐进式填写过程。这样做可以使申请输入与评估目标更紧密对应，而不是停留在通用字段层面。

图5-2 渐进式领养申请填写页面
该机制并不依赖大模型即时生成，而是采用规则驱动方式实现，以提高响应速度和输入一致性。系统通过动态问题生成接口返回当前场景下最需要补足的信息项，相关实现位于 src/web/routers/ai.py 中的 generate_adoption_questions 逻辑。
@router.get("/adoption-questions/{pet_id}")
async def generate_adoption_questions(pet_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (current_user["id"],))
        row = cursor.fetchone()
        profile = dict(row) if row else {}
    questions = _build_smart_questions(pet_info, features, requirements, profile)
    return {"questions": questions[:4], "pet_name": pet_info.get("name", ""), "profile_loaded": bool(profile)}
5.2.3 申请信息规范化与预筛结果返回
申请提交并不意味着立即进入正式评估。系统会先对输入内容进行统一整理，并通过规则预筛机制识别明显不满足基础条件的情况，例如预算不足、陪伴时间严重偏低或存在硬性限制冲突。通过这一层过滤，系统能够在正式调用多智能体评估前完成一次确定性判断，从而避免将本可直接处理的问题继续交给后续复杂分析流程。

【图5-3 申请预筛结果或申请提交成功页面（此处插入）】
这里的关键不在于简单地“拦截不合格申请”，而在于将输入标准化与规则前置结合起来，使正式评估阶段处理的是已经过初步清洗和约束判断的申请数据。相关预筛逻辑由评估服务层完成，具体实现在 src/web/services/assessment_service.py 中的基础规则判断部分，包括预算、陪伴时长以及硬性条件的校验。
def _check_hard_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
    flags = []
    passed = True
if float(data.get("monthly_budget", 0) or 0) < self.rules["min_monthly_budget"]:
        flags.append("经济能力可能无法覆盖基础养护支出")
        passed = False
If float(data.get("daily_companion_hours", 0) or 0) < self.rules["min_companion_hours"]:
        flags.append("每日陪伴时间严重不足")
        passed = False
    return {"passed": passed, "rule_flags": flags}
5.3 正式申请的多智能体评估实现
5.3.1 申请主记录创建与评估触发
正式评估并不是围绕宠物对象直接发起一次 AI 分析，而是围绕领养申请主记录展开。这样设计的意义在于，将每一次领养申请作为独立的流程对象进行管理，使同一只宠物面对不同申请人时，能够形成彼此独立的评估状态、审核结果和后续反馈记录。通过这种方式，评估过程不再是单次调用后的即时返回，而是成为申请生命周期中的正式环节。

图5-4 申请提交后的评估处理中页面
在实现上，系统会先创建正式申请记录，再以后台任务方式启动评估流程。相关逻辑位于 src/web/routers/user.py 中的申请创建接口，该接口将申请信息落库后，再调用评估服务的异步入口继续推进后续流程。
@router.post('/applications')
async def create_adoption_application(
request: AdoptionAssessmentRequest,
background_tasks: BackgroundTasks,
current_user: dict = Depends(get_current_user)):
    app_id = ApplicationService.create_application(
        user_id=current_user['id'],
        pet_id=request.pet_id,
        applicant_data=request.dict()
)
background_tasks.add_task(AdoptionAssessmentService().start_application_evaluation, app_id)
    return {"status": "success", "application_id": app_id}
5.3.2 多智能体创建与分工执行过程
领养评估中的多智能体并不是多个简单的聊天角色，而是按评估任务进行职责划分。系统首先根据不同功能构建不同模型实例，再据此创建百科基准、申请人画像、共处风险、审计质疑和共识协调等专项智能体。这样的构建方式能够使复杂的审核任务从单模型一次性生成，转变为分步骤、分职责的协同处理过程，从而提高评估过程的稳定性和可解释性。
【图5-5 多智能体评估结果处理中界面（此处插入）】

这一部分的核心实现位于 src/agents/agents.py。系统先通过功能分流方式创建 adoption_llm、chat_llm 和 common_llm，再进一步构建百科智能体、画像智能体、风险智能体和共识协调智能体，并将它们纳入统一的任务编排流程。
adoption_llm = create_llm_instance("ADOPTION")
e_agent = get_encyclopedia_agent(adoption_llm)
p_agent = get_adoption_profiler_agent(adoption_llm)
a_agent = get_audit_expert_agent(adoption_llm)
ch_agent = get_cohabitation_risk_agent(adoption_llm)
c_agent = get_consensus_coordinator_agent(adoption_llm)
res = Crew(
    agents=[h_expert, e_agent, p_agent, a_agent, c_agent, ch_agent],
    tasks=[t_recall, t_ency, t_cohab, t_prop, t_audit, t_cons],
    process=Process.hierarchical,
    manager_llm=adoption_llm,
    memory=True
).kickoff()
5.3.3 结构化评估结果展示
多智能体评估完成后，系统不会直接返回一段自由文本，而是将结果整理为准备度评分、风险等级、风险点、建议补充项和审核参考意见等结构化内容。这种输出方式一方面便于页面展示，另一方面也更适合送养方和管理员快速定位问题重点，从而提高审核效率。
【图5-6 结构化评估结果展示页面（此处插入）】

这里的关键并不只是“把结果显示出来”，而在于将多智能体的分散分析结果整合为统一的审核参考。对应实现主要位于 src/web/services/assessment_service.py 中的结果整合与持久化逻辑，系统会将评分、风险等级、冲突说明和追问问题等内容统一写回申请主记录和评估快照表中。
5.3.4 评估状态查询与补充信息交互
正式评估并不是一次性结束的过程。当系统判断当前申请信息仍存在缺口或冲突时，会将缺失字段、冲突说明和补充问题返回给前端，由申请人进一步补充材料后重新进入评估流程。这样可以使评估从“提交后直接得到结论”的静态过程，转变为“补充—再评估—再反馈”的动态过程。
【图5-7 申请状态查询与补充信息页面（此处插入）】

状态查询与补充信息交互的相关实现位于 src/web/routers/ai.py 中的状态查询接口和补充资料接口。系统会将申请记录中的缺失项、冲突说明和追问内容解析后返回给页面展示，再由用户围绕这些内容进行二次补充，从而支持多轮迭代式评估
5.4 检索增强与案例记忆实现
5.4.1 知识检索支撑实现
领养评估不仅依赖申请人填写的文本内容，还需要结合宠物照护知识、送养注意事项和常见风险说明等外部信息。若仅依靠模型自身的参数记忆生成结论，容易出现依据不清或结果不稳定的问题。因此，系统在评估链路中引入知识检索机制，将知识库内容作为风险分析和结果生成的辅助依据。
【图5-8 知识依据或风险提示展示页面（此处插入）】

在实现上，系统使用 ChromaDB 保存宠物知识向量索引，并在服务启动时检查知识集合是否已经初始化。若知识集合为空，则自动执行知识同步操作，使后续评估能够直接调用相关知识片段。该逻辑位于 src/web/app.py 的生命周期初始化过程中。
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_or_create_collection(name="pet_knowledge")
if collection.count() == 0:
    sync_knowledge_to_chroma()
5.4.2 相似案例匹配与经验调用
除领域知识外，历史申请中的处理结果和回访反馈也是领养评估的重要参考。实际审核中，送养方往往会参考以往类似申请的结果，例如相似家庭条件下的领养稳定性、相似宠物类型的适应情况，以及后续回访中暴露出的风险问题。为体现这一经验复用过程，系统在评估服务中加入案例记忆机制，将历史申请、送养方决策模式、回访反馈和相似案例统一组织为记忆上下文。
【图5-9 相似案例参考或案例摘要展示页面（此处插入）】

在实现过程中，系统会根据当前申请信息召回相似案例，并将历史申请记录、后验反馈和案例记忆一并纳入评估上下文。相关逻辑主要位于 src/web/services/assessment_service.py 中的记忆上下文构建部分，其中包含历史申请查询、回访反馈读取和相似案例召回等处理 。同时，闭环实施方案中也将案例记忆作为反馈学习的重要组成部分，用于支撑后续相似申请的判断。
5.5 审核裁决与反馈闭环实现
5.5.1 送养用户审核处理实现
系统生成结构化评估结果后，申请并不会直接由 AI 自动决定最终结果，而是进入送养用户审核环节。这样设计的原因在于，宠物领养具有明显的责任判断和个体差异，AI 评估结果更适合作为辅助参考，而不应完全替代人工裁决。送养用户在查看申请详情时，可以同时看到申请人基本信息、评估摘要、风险等级、主要风险点和补充建议，从而在更充分的信息基础上作出处理。
图5-10 送养用户审核处理页面

5.5.2 管理员复核与审计追踪实现
对于风险等级较高、评估结果存在冲突，或者需要进一步确认的申请，系统提供管理员复核与审计追踪机制。该机制的作用在于将多智能体评估过程从“不可见的模型输出”转化为可以查询、可以复核的过程记录。管理员可以根据评估追踪标识查看输入快照、输出结果、耗时信息和关键阶段记录，从而判断评估结果是否需要人工干预。

图5-11 管理员复核与审计页面
审计追踪的核心实现位于 src/web/routers/ai.py 中。系统通过 trace_id 查询智能体评估过程中保存的日志记录，并将输入快照、输出内容和耗时信息返回给管理员页面。
@router.get("/audit/report/{trace_id}")
async def get_audit_report(trace_id: str, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT input_msg, output_msg, latency_ms FROM agent_trace_logs WHERE trace_id = ?", (trace_id,))
        row = cursor.fetchone()
    return {"trace": json.loads(row[1]), "snapshot": json.loads(row[0]), "latency": row[2]}
5.5.3 回访反馈与案例沉淀实现
领养评估的价值不应只停留在申请审核阶段。宠物被成功领养后，实际照护情况、适应情况和领养人反馈都可以作为后续评估的重要经验来源。因此，系统在审核完成后继续保留回访反馈机制，将领养后的真实结果沉淀为案例记忆，用于支撑后续相似申请的判断
图5-12 回访反馈与闭环结果页面
