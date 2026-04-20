# 宠物领养评估闭环系统实施方案

## 1. 文档目的

本文档用于给出“基于多智能体的宠物领养评估系统设计与实现”的完整落地方案，目标不是只实现一次性的 AI 打分，而是实现一套可运行、可追踪、可补充信息、可人工复核、可后验学习的闭环领养评估系统。

该方案结合当前项目已有基础能力，并参考 [rizhi.md](/d:/2026毕业设计/project/rizhi.md:1) 中提出的三条关键方向：

- 宠物信息增强展示
- 送养人约束规则前置透明化
- 领养申请从“一键提交”升级为“渐进式交互评估”

同时，方案会覆盖：

- 后端框架与服务层拆分逻辑
- 多智能体构建方式与多种协同架构
- 领养人、送养人、管理员三类使用者的前端交互
- 从申请、评估、追问、复核到反馈学习的完整生命周期

---

## 2. 当前项目现状与主要缺口

### 2.1 已有能力

当前项目已经具备较强的“评估核心引擎”基础，具体包括：

- `src/web/services/assessment_service.py`
  已实现规则预筛、知识上下文构建、历史记忆加载、AI 评估融合、七维评分、共识融合、风险路由与审计日志。
- `src/agents/agents.py`
  已实现基于 CrewAI 的多智能体领养评估核心逻辑，包含百科基准、申请人画像、历史复盘、共处风险、审计质疑、共识协调等角色。
- `src/web/services/adoption_flow_engine.py`
  已有领养评估状态机与流程事件记录机制。
- `src/web/services/adoption_memory.py`
  已有案例记忆、AI 评审快照、追问记录、信号权重更新的基础设施。
- `src/web/services/db_service.py`
  已定义 `applications`、`adoption_ai_reviews`、`adoption_followups`、`adoption_case_memory`、`adoption_flow_events`、`adoption_signal_weights` 等闭环所需表结构。
- 前端 `pet-frontend/src/views/AdoptView.vue`
  已有领养入口、候选宠物列表、初步意向选择与 AI 驱动入口。

### 2.2 当前缺口

当前系统的核心问题不是“没有 AI”，而是“业务闭环还没有打通”：

- 缺少正式的领养申请创建接口与前端调用路径
- 前端把 `pet.id` 当作 `application_id` 使用，导致申请与评估流程脱节
- 正式评估接口中，异步后台任务仍是占位逻辑，没有完成结果回写
- 补充信息、人工复核、后验反馈接口仍是占位返回
- 流程状态虽然存在，但没有在申请、评估、复核、反馈全过程中持续推进
- 多智能体评估结果虽可生成，但没有完整沉淀为“申请级闭环资产”
- 前端还未按“领养人”和“送养人”两个业务身份设计完整交互

### 2.3 本文档的目标结论

本方案的目标不是再增加几个零散页面，而是把系统升级为：

“一个以申请记录为主线，以多智能体评估为中枢，以流程状态机为骨架，以后验反馈学习为闭环的宠物领养评估系统。”

---

## 3. 角色模型与权限设计

## 3.1 认证角色与业务身份分离

当前代码中的认证角色只有两级：

- `user`
- `admin`

这一点应保留，不建议为了业务流程再新增大量认证角色。

在领养评估系统中，建议引入“业务身份”概念，而不是新增 JWT 角色：

- 领养人：当前用户作为申请发起者
- 送养人：当前用户作为宠物拥有者或送养帖发布者
- 管理员：平台管理与人工复核角色，对应现有 `admin`

因此，权限判断遵循下面的原则：

- `user + application.user_id == current_user.id`
  视为领养人身份
- `user + application.pet_owner_id == current_user.id`
  视为送养人身份
- `admin`
  视为平台管理员身份

这种设计的优点：

- 不破坏现有认证体系
- 兼容同一用户既能发布送养宠物，也能申请领养其他宠物的场景
- 更符合平台型系统的真实业务模型

## 3.2 三类角色在闭环中的职责

### 领养人

- 浏览宠物完整档案
- 查看送养人公开约束
- 按渐进式步骤提交申请
- 查看评估状态与结果
- 针对追问补充资料
- 领养成功后填写回访反馈

### 送养人

- 发布宠物与设置领养约束
- 查看收到的申请及 AI 评估结果
- 对存在分歧的申请发起追问或直接裁决
- 对 AI 建议做“采纳/不采纳”决策
- 在领养后查看回访结果

### 管理员

- 查看高风险或高分歧申请
- 进行人工复核和终局裁决
- 查看审计轨迹、模型输出、冲突来源
- 统计系统性能与闭环效果

---

## 4. 业务目标与闭环定义

完整的闭环流程应包含以下 8 个阶段：

1. 送养人发布宠物并设置约束规则
2. 领养人在宠物详情页查看档案与约束
3. 领养人提交正式申请，生成 `application`
4. 系统自动触发多智能体评估并输出结论
5. 根据不确定性进入：
   `waiting_publisher` / `need_more_info` / `manual_review` / `rejected`
6. 若进入追问，领养人补充资料后重新评估
7. 送养人或管理员完成最终裁决
8. 领养完成后写入反馈，反哺案例记忆与信号权重

这 8 步全部打通，才可以称为“完整实现宠物领养评估系统”。

---

## 5. 系统总体架构方案

## 5.1 分层架构

建议继续沿用当前前后端分离架构，并将领养评估系统划分为 5 层：

### 表现层

- Vue 3 + TypeScript + Pinia
- 页面：领养页、申请详情页、个人中心、送养人审核页、管理员复核页

### API 层

- FastAPI Router
- 负责参数校验、权限校验、状态返回

### 业务编排层

- `ApplicationService`
- `AdoptionAssessmentService`
- `AdoptionFlowEngine`
- `AdoptionMemoryService`

该层负责：

- 正式申请创建
- 评估流程发起
- 状态流转
- 结果落库
- 追问重评
- 反馈闭环

### 多智能体协同层

- CrewAI Agents
- Rule Engine
- Consensus Router
- Case Memory

该层负责：

- 候选证据收集
- 专家评审
- 冲突仲裁
- 决策协调
- 追问生成
- 反馈学习

### 数据层

- SQLite：业务记录与流程状态
- ChromaDB：知识检索与向量化案例记忆

---

## 6. 核心数据主线设计

## 6.1 以 `applications` 作为流程主实体

整个系统的主线必须围绕 `applications` 表展开，而不是围绕 `pet` 或单次 AI 调用展开。

每一次正式领养申请都对应一条唯一记录：

- `id`
- `user_id`
- `pet_id`
- `pet_owner_id`
- `apply_reason`
- `assessment_payload`
- `flow_status`
- `status`
- `ai_decision`
- `ai_readiness_score`
- `risk_level`
- `consensus_score`
- `missing_fields`
- `conflict_notes`
- `followup_questions`
- `evaluation_trace_id`
- `owner_followed_ai`

### 设计原则

- 宠物是被申请对象，不是流程对象
- AI 评估结果必须绑定到 `application_id`
- 同一个宠物可以有多个申请，每个申请必须独立评估

## 6.2 评估相关附属表职责

### `adoption_ai_reviews`

记录一次 AI 评估快照：

- agent 输出
- 共识结果
- 路由决策
- 综合分
- 风险等级

### `adoption_followups`

记录追问与补充材料：

- question
- answer
- source
- impact_score
- trace_id

### `adoption_case_memory`

记录案例沉淀，用于相似案例召回：

- case_summary
- decision_result
- owner_followed_ai
- risk_tags_json
- feature_snapshot_json

### `adoption_flow_events`

记录流程状态迁移与非法跳转尝试。

### `adoption_signal_weights`

记录后验统计信号，用于动态修正路由和建议。

---

## 7. 多智能体总体设计

## 7.1 设计原则

多智能体不是为了“看起来高级”，而是为了把不同职责拆开，形成：

- 输入解释
- 规则校验
- 领域推理
- 风险审计
- 冲突协调
- 最终裁决

这样的多层推理链。

建议将系统中的评估智能体分为三组：

- 评估前智能体
- 评估中智能体
- 评估后智能体

## 7.2 智能体角色设计

### A. 评估前智能体

#### 1. IntakeNormalizerAgent

职责：

- 将前端渐进式交互输入转换为统一 `assessment_payload`
- 补齐字段命名、枚举值、默认值
- 把自然语言申请理由和结构化选项整理成评估上下文

输出：

- 标准化申请快照

#### 2. RulePrescreenAgent

职责：

- 对照 `pet_requirements` 与 `publisher_preferences`
- 检查硬约束与明显不匹配项
- 输出是否可继续深评

输出：

- `passed`
- `rule_flags`
- `hard_block`
- `prescreen_summary`

### B. 评估中智能体

#### 3. PetProfileAgent

职责：

- 解读宠物特征
- 从 `pet_features` 和知识上下文提取照护基线
- 给出适配关注点

输入：

- 宠物结构化特征
- 物种知识上下文

#### 4. ApplicantProfilerAgent

职责：

- 从申请理由、个人情况、结构化条件中抽取申请人画像
- 评估责任意识、养宠经验、稳定性与动机强度

#### 5. CohabitationRiskAgent

职责：

- 评估居住环境、家庭结构、原住宠物共处风险

#### 6. MemoryRecallAgent

职责：

- 检索历史相似案例
- 召回高相似度申请的后验结果

#### 7. AuditChallengeAgent

职责：

- 对前述专家意见进行质疑与证据校验
- 主动指出高风险或信息不足点

#### 8. ConflictMediationAgent

职责：

- 当多个专家结论分歧较大时，提炼争议焦点
- 将“分歧”转化为“可追问问题”或“需人工确认项”

#### 9. DecisionCoordinatorAgent

职责：

- 综合各专家输出
- 输出结构化最终结论

输出字段建议固定为：

- `readiness_score`
- `decision`
- `risk_level`
- `confidence`
- `risk_factors`
- `recommendations`
- `followup_questions`
- `conflict_notes`
- `summary`

### C. 评估后智能体

#### 10. FollowupInterviewAgent

职责：

- 针对缺失字段与冲突点生成下一轮追问
- 将自由文本补充转化为可重评输入

#### 11. FeedbackLearningAgent

职责：

- 基于回访反馈更新风险标签权重
- 调整后续路由策略与案例参考可信度

---

## 8. 多智能体协同架构方案

本系统不应只支持一种协同方式。建议按评估阶段使用不同架构。

## 8.1 架构一：顺序式协作

适用场景：

- 提交前即时预评估
- 成本受限的快速判断

流程：

`RulePrescreen -> ApplicantProfiler -> DecisionCoordinator`

优点：

- 快
- 成本低
- 可用于前台即时预估

缺点：

- 证据深度不足

## 8.2 架构二：分层式协作

适用场景：

- 正式申请后的深度评估

流程：

- Manager / Coordinator 负责调度
- `MemoryRecallAgent`、`PetProfileAgent`、`ApplicantProfilerAgent`、`CohabitationRiskAgent` 并发分析
- `AuditChallengeAgent` 进行审计质疑
- `ConflictMediationAgent` 整理争议
- `DecisionCoordinatorAgent` 输出最终结论

这正是当前项目最适合延续的主架构，也是论文中“多智能体协同评估”的主要呈现方式。

## 8.3 架构三：委员会共识式协作

适用场景：

- 高风险样本
- 送养人偏好保守
- 专家结论分歧较大

流程：

- 每个专家独立输出建议
- 共识层对比分数、风险标签、缺失项
- 若共识度低，则自动路由到：
  `followup` 或 `manual_review`

这个架构不一定完全依赖 CrewAI 内置 process，可以由服务层完成共识融合。

## 8.4 推荐的实际组合

建议采用混合架构：

- 提交前预估：顺序式
- 正式评估：分层式
- 冲突仲裁：委员会共识式

这样既能兼顾实时性，也能突出论文中“多架构协同”的亮点。

---

## 9. 后端实现方案

## 9.1 路由层设计

建议新增或完善以下接口。

### 领养人侧

- `POST /api/user/applications`
  创建正式申请
- `GET /api/user/applications/{user_id}`
  查看我发出的申请
- `GET /api/ai/assessment/status/{application_id}`
  查看当前评估状态
- `POST /api/ai/assessment/followup/{application_id}`
  提交补充信息
- `POST /api/ai/assessment/feedback/{application_id}`
  提交领养后反馈

### 送养人侧

- `GET /api/user/applications/incoming`
  查看收到的申请
- `POST /api/user/applications/{application_id}/owner-decision`
  送养人裁决
- `POST /api/user/applications/{application_id}/owner-followup`
  送养人发起补充追问

### 管理员侧

- `GET /api/admin/applications`
  查看全平台申请
- `GET /api/ai/audit/report/{trace_id}`
  查看 AI 审计报告
- `POST /api/ai/audit/review/{application_id}`
  管理员人工复核

## 9.2 服务层设计

建议按职责拆分如下：

### `ApplicationService`

职责：

- 创建申请
- 读取申请详情
- 更新申请主记录
- 权限辅助判断

推荐方法：

- `create_application(user_id, payload)`
- `get_application(application_id)`
- `list_outgoing(user_id)`
- `list_incoming(owner_id)`
- `update_assessment_fields(application_id, result)`
- `update_owner_decision(application_id, decision_payload)`

### `AdoptionAssessmentService`

职责：

- 执行完整评估流程
- 生成结果
- 结果落库
- 重评与兜底

推荐新增方法：

- `run_full_assessment(user_id, applicant_data)`
- `start_application_evaluation(application_id)`
- `persist_assessment_result(application_id, result)`
- `rerun_after_followup(application_id, followup_payload)`

### `AdoptionFlowEngine`

职责：

- 校验状态迁移合法性
- 写入流程事件
- 提供当前状态重建能力

建议补齐：

- `resolve_review_flow_status(status)`
- `resolve_feedback_flow_status(status)`

### `AdoptionMemoryService`

职责：

- 相似案例召回
- AI 审核快照落库
- 后验权重更新
- 闭环统计输出

## 9.3 正式申请创建逻辑

领养申请创建时，后端应完成以下动作：

1. 验证用户登录
2. 检查宠物存在且可申请
3. 读取宠物特征、送养人要求、发布者偏好
4. 将前端渐进式输入整理为 `assessment_payload`
5. 写入 `applications`
6. 记录初始流程事件：
   `submitted -> evaluating`
7. 异步触发 `start_application_evaluation(application_id)`

## 9.4 正式评估逻辑

后台任务执行步骤建议为：

1. 从 `applications.assessment_payload` 取评估输入
2. 调用 `run_full_assessment`
3. 得到：
   - readiness_score
   - decision
   - risk_level
   - followup_questions
   - conflict_notes
   - consensus_result
   - route_decision
4. 根据 `route_decision.next_action` 映射流程状态：
   - `reject_candidate -> rejected`
   - `followup -> need_more_info`
   - `manual_review -> manual_review`
   - `publisher_review -> waiting_publisher`
5. 更新 `applications`
6. 写入 `adoption_ai_reviews`
7. 写入 `adoption_case_memory`
8. 写入 `adoption_flow_events`
9. 写入 `agent_trace_logs`

## 9.5 追问重评逻辑

当申请进入 `need_more_info`：

1. 领养人提交补充资料
2. 写入 `adoption_followups`
3. 原 `assessment_payload` 与补充信息合并
4. `flow_status: need_more_info -> evaluating`
5. 重新运行评估
6. 再次落库

## 9.6 人工复核逻辑

当申请进入 `manual_review`：

1. 管理员查看：
   - AI 结论
   - 审计轨迹
   - 风险标签
   - 追问历史
2. 管理员提交：
   - `approved`
   - `rejected`
   - `probing`
   - `human_review`
3. 流程引擎更新最终状态
4. 记录人机一致性：
   `owner_followed_ai`

## 9.7 反馈学习逻辑

领养完成后：

1. 领养人提交满意度、亲密度、挑战问题、推荐意愿
2. 写入 `adoption_feedbacks`
3. 更新 `adoption_case_memory.followup_outcome`
4. 调用 `update_signal_weights_from_feedback`
5. 触发：
   `adopted -> followup_completed`

这一步是论文中“后验闭环优化”的核心。

---

## 10. 前端展示与互动方案

## 10.1 领养人侧页面设计

### A. 领养页 AdoptView

应从“选 3 个标签立即提交”升级为 4 块区域：

#### 1. 宠物档案卡

参考 `rizhi.md` 的建议，完整展示：

- 基础信息：性别、年龄段、绝育状态、健康状态
- 性格与行为：精力、社交性、是否适合新手、是否适合有孩家庭、是否能与其他宠物共处
- 特殊需求：医疗需求、特殊照护、成本等级、陪伴需求

#### 2. 送养人要求卡

提前展示：

- 是否允许新手
- 最低预算
- 最低陪伴时长
- 是否要求稳定住房
- 是否禁止有幼儿
- 是否允许家中已有宠物
- 是否要求回访
- 地域限制
- 发布者备注
- 风险容忍度

#### 3. 渐进式申请面板

建议三步式：

- Step 1：领养动机与经验
- Step 2：条件确认
- Step 3：申请摘要与风险提示

#### 4. 提交后状态卡

提交后展示：

- 当前流程状态
- AI 准备度评分
- 风险等级
- 是否需要补充资料
- 当前追问问题
- 最终建议

### B. 我的申请页

领养人查看自己发出的申请，重点显示：

- 申请的宠物
- 当前流程节点
- AI 评估结果
- 缺失信息
- 追问问题
- 是否已被送养人处理
- 是否需要提交回访反馈

## 10.2 送养人侧页面设计

### A. 发布送养宠物/帖子页面

新增“领养条件设置”区域：

- allow_beginner
- min_budget_level
- min_companion_hours
- require_stable_housing
- forbid_children
- forbid_other_pets
- require_return_visit
- region_limit
- special_notes
- risk_tolerance

### B. 送养人审核页

每条申请应显示：

- 申请人基本情况
- AI 综合分与风险等级
- 七维评分
- 冲突说明
- 建议追问
- AI 推荐结论
- 是否存在历史相似案例

送养人可执行：

- 通过
- 拒绝
- 发起补充追问
- 提交人工复核

### C. 送养人决策辅助设计

界面上需明确区分：

- AI 建议
- 送养人最终决定

并记录：

- 是否采纳 AI
- 不采纳原因

## 10.3 管理员侧页面设计

管理员重点查看：

- 高风险申请
- 高分歧申请
- 长时间未处理申请
- 被多次追问的复杂申请

管理员页需提供：

- 审计轨迹视图
- 多智能体输出对比视图
- 流程时间轴
- 人工复核入口
- 闭环统计看板

---

## 11. 状态机设计

推荐以当前状态机为基础，使用如下主状态：

- `submitted`
- `evaluating`
- `need_more_info`
- `waiting_publisher`
- `manual_review`
- `approved`
- `rejected`
- `adopted`
- `followup_completed`

推荐迁移规则：

- `submitted -> evaluating`
- `evaluating -> need_more_info`
- `evaluating -> waiting_publisher`
- `evaluating -> manual_review`
- `evaluating -> rejected`
- `need_more_info -> evaluating`
- `waiting_publisher -> approved`
- `waiting_publisher -> rejected`
- `waiting_publisher -> need_more_info`
- `waiting_publisher -> manual_review`
- `approved -> adopted`
- `adopted -> followup_completed`

说明：

- `approved` 表示流程通过但未进入领养后阶段
- `adopted` 表示送养关系成立
- `followup_completed` 表示完成回访闭环

---

## 12. 审计、可观测性与论文实验指标

## 12.1 审计指标

每一次正式评估必须有：

- `trace_id`
- 流程阶段日志
- agent 输出快照
- 共识结果
- 路由结果
- 最终人类决策

## 12.2 论文可展示指标

建议统计：

- 平均评估耗时
- 高风险样本比例
- 进入追问比例
- 进入人工复核比例
- 人机决策一致率
- 回访满意度
- 后验信号修正前后的一致率变化

## 12.3 可视化建议

可在后台或论文图表中展示：

- 领养流程漏斗图
- 风险等级分布图
- 七维评分雷达图
- 不同路由决策占比图
- 人机一致率折线图

---

## 13. 实施优先级

## P0：必须先完成

- 正式申请创建接口
- 前端申请路径改造为“先建申请，再启动评估”
- 正式评估结果回写 `applications`
- 送养人要求前置展示
- 渐进式申请面板
- 追问重评链路

## P1：完善闭环

- 送养人裁决页
- 管理员复核页
- AI 审计报告页
- 回访反馈与后验权重更新
- 案例记忆优化

## P2：论文亮点增强

- 冲突仲裁智能体
- 智能追问智能体
- 更精细的案例召回
- 更复杂的多架构协同实验

---

## 14. 文件级落地建议

建议优先改造这些文件：

- `src/web/routers/user.py`
  增加正式申请创建、送养人决策接口
- `src/web/services/application_service.py`
  承担申请创建与主记录更新
- `src/web/routers/ai.py`
  补齐评估启动、追问、反馈、人工复核逻辑
- `src/web/services/assessment_service.py`
  增加申请级评估编排与结果持久化
- `src/web/services/adoption_flow_engine.py`
  补齐完整流程映射方法
- `src/web/services/adoption_memory.py`
  修正案例记忆检索与反馈权重更新
- `pet-frontend/src/views/AdoptView.vue`
  改为完整宠物档案 + 送养规则 + 渐进式申请
- `pet-frontend/src/views/ProfileView.vue`
  增加申请状态、追问回复、回访反馈
- `pet-frontend/src/views/DashboardView.vue`
  增加送养人审核与管理员复核能力

---

## 15. 验收标准

当以下条件全部满足时，可认为该课题的“领养评估系统闭环”已经实现：

- 用户可以创建正式申请记录，而不是只触发一次 AI 调用
- 每条申请都有独立的 `application_id`、`trace_id` 和流程状态
- AI 评估结果能够完整落库并被送养人查看
- 系统可以基于缺失信息进入追问并完成重评
- 送养人和管理员都可以做最终裁决
- 领养完成后，回访反馈可以回写到案例记忆与信号权重
- 前端对领养人和送养人分别提供完整交互入口
- 多智能体协作不只是概念，而是已经融入正式评估主链路

---

## 16. 最终建议

本项目后续实现时，应坚持以下原则：

- 不再围绕单次 AI 输出开发，而是围绕 `application` 生命周期开发
- 不把“送养人”和“领养人”混成同一套页面逻辑
- 不把“多智能体”只当成生成报告的工具，而要作为流程决策中枢
- 不把“闭环”理解为日志记录，而要真正实现“申请 -> 评估 -> 追问 -> 裁决 -> 反馈 -> 学习”

如果严格按本方案推进，那么你的课题将从“有一个多智能体评估原型”升级为“有一套完整的多智能体领养评估业务系统”，这对毕业设计的完整性、说服力和答辩表现都会有明显提升。
