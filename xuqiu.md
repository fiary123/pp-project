Week 1：架构重构（不改业务，先降维护风险）
目标
把当前“超大 app.py”拆分为模块，减少后续迭代冲突。

当前痛点
src/web/app.py 同时承担 schema、建表、业务逻辑和全部路由，规模已很大。.

任务
新建目录：

src/web/routers/auth.py

src/web/routers/community.py

src/web/routers/ai.py

src/web/routers/admin.py

src/web/routers/user.py

新建服务层：

src/web/services/db_service.py（get_db_connection, ensure_tables）

src/web/services/ai_service.py（chat/triage/smart-match 调度）

app.py 保留：应用初始化 + include_router。

验收标准
功能不变、路由地址不变。

测试全部通过（至少你现有两套）。

Week 2：鉴权与安全（答辩会被问到）
目标
解决“管理接口无权限保护”的问题，增强论文工程性。

当前现状
管理接口可调用，但未见统一鉴权依赖。.

任务
增加 JWT（或简化 token）登录态。

新增 require_admin 依赖，挂到 /api/admin/*。

密码从明文改 bcrypt 存储（至少新用户走哈希）。

对关键写操作（删帖、禁言、审核）写入操作日志。

验收标准
非管理员访问 /api/admin/* 返回 403。

密码字段不再明文存储（新注册用户）。

Week 3：多智能体可观测（核心亮点）
目标
把“多智能体”从逻辑存在，升级为可展示、可追踪。

当前现状
已有 triage 多智能体入口，但缺 trace。.

任务
增加 agent_trace_logs 表：

trace_id, endpoint, agent_name, tool_name, latency_ms, fallback_used, created_at

chat/triage/nutrition 接口返回 trace_id。

管理端新增“智能执行日志”页（最简表格即可）。

验收标准
每次智能接口请求可查到 trace 记录。

能明确看到“是否走了 fallback”。

Week 4：营养专家精细化（你论文主打点）
目标
从“静态计算”升级为“闭环优化”。

当前现状
营养计划模型和规则已成形。.

任务
新增馈接口：POST /api/nutrition/feedback

输入：7天体重变化、食欲、粪便状态、活动变化

新增再规划接口：POST /api/nutrition/replan

输出新增字段：

confidence_level

recheck_in_days

requires_vet（布尔）

验收标准
同一宠物档案可形成 “初始方案 -> 反馈 -> 再方案”闭环。

页面可展示“本次建议置信度”。

Week 5：数据与评估体系（论文第4章核心）
目标
拿到可量化结果，支撑“智能化提升”。

任务
构造样本集（建议 80~120 条）：

营养（40）

分诊（30）

匹配/管理（20+）

建立指标：

结构化完整率（字段齐全）

风险提示覆盖率

平均响应时延

用户可执行性评分（问卷1~5）

做对照实验：

A：规则/模板

B：多智能体优先+降级

验收标准
输出表格和图（柱状图/雷达图至少各1）。

Week 6：论文与答辩演示封装
目标
从“代码完成”转成“可答辩”。

任务
输出 1 页系统架构图（前端->API->Agent->Tool->DB）。

输出 1 页多智能体时序图（chat/triage/nutrition）。

录制 3 条演示视频（每条 1~2 分钟）：

营养方案生成与再规划

分诊->风险等级->管理查看 trace

社区操作+管理审核闭环

撰写“局限性与未来工作”：

语义准确度依赖模型

地域化兽医知识待扩展

更多物种支持

四、风险与规避（你答辩时也可说）
风险1：重构引入回归 bug

规避：先拆分文件，不改逻辑，跑回归测试。

风险2：模型调用不稳定

规避：你已实现 fallback，继续加强并记录日志。.

风险3：演示时网络问题

规避：准备规则回退演示路径，保证离线可展示核心流程。

五、建议你补的“里程碑文档”（老师很爱看）
docs/ROADMAP.md（按周计划）

docs/ARCHITECTURE.md（模块图 + 时序图）

docs/EVALUATION.md（指标定义与结果）