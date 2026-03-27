“状态化编排”

你现有领养评估更像一个服务函数：收输入，跑规则，跑模型，出结果。
现在要升级的是把它变成一条有状态的流程：

申请进入 → 规则预筛 → 专家评估 → 分歧检测 → 必要时追问 → 发布者/管理员复核 → 最终建议 → 领养后反馈回流

CrewAI 的 Flows 正是用来做这种事件驱动、多步骤、可分支流程的。官方文档明确说 Flows 支持状态管理、事件驱动、条件逻辑、循环和分支。

这部分是核心改动，但它是编排层重构，不是所有业务代码重写。

2. 把“专家并列调用”改成“manager 调度”

如果你现在是自己手动写几个 Agent 顺序调用，那改成 CrewAI 的 hierarchical process 时，主要变化是引入一个 manager_agent 负责规划、委派、验证，而不是把任务预先写死给每个 Agent。CrewAI 官方就支持 custom manager agent，hierarchical process 也要求设置 manager_llm 或 manager_agent。

这部分改动不算大到伤筋动骨，因为你现有专家能力本身可以保留。
你要变的是“谁来调它们”，不是“每个专家都重写”。

3. “专家共识层”需要你自己补

这里是唯一稍微“新一点”的地方。

CrewAI 官方当前实现的 process 是 sequential 和 hierarchical；consensual process 还是 planned，还没有正式实现。

这反而对你是好事。
因为你完全可以把“共识层”写成自己的创新：

多个专家先独立输出
manager 汇总
计算一致性/冲突度
决定直接给建议、继续追问，还是转人工

也就是说，这块不是等框架给你现成功能，而是你在 Flow 或 manager 逻辑里自己实现。

先给你一个总判断：改动量分级
低改动版

只加 manager_agent，其他逻辑基本不动。
适合快速做出“我不是纯顺序调用”的变化。

中改动版

manager_agent + Flow 状态机 + human feedback。
这是我最推荐的，因为论文效果和实现成本比较平衡。

高改动版

再加 共识层 + feedback memory + hooks 全链路治理。
这个最完整，但如果时间紧，不一定要一次全做完。

对你来说，最合理的是先做“中改动版”，然后把共识层和反馈记忆写成可扩展优化点。

具体怎么实现：我建议按 5 步落地
第一步：先不动前端，大部分复用现有接口

你现在前端已经有：

领养申请页面
审核页面
AI 日志页面
回访反馈页面

这些都不用先推翻。

你先改后端，把原来的：

evaluate_adoption(application_id)

改成：

run_adoption_flow(application_id)

也就是从“单函数评估”升级为“流程驱动评估”。

这一步新增的数据状态建议

给领养申请表或评估表增加这些字段：

flow_status：submitted / prechecked / expert_review / need_more_info / waiting_publisher / approved / rejected / manual_reviewflow_status ： submitted / prechecked / expert_review / need_more_info / waiting_publisher / approved / rejected / manual_review
risk_level
consensus_score
missing_fields
publisher_feedback
manual_review_reason
memory_scope

这不算大改，只是把“一个结果”扩展成“一个过程”。

第二步：把规则预筛单独拆成一个开始节点

你论文里已经有“规则预筛”，这一步直接复用。

在 Flow 里它就是 @start() 后的第一个阶段：

检查预算是否明显过低
陪伴时间是否明显不足
住房是否明确不允许
是否缺关键字段

如果明显不满足底线，就不要让后面一堆 Agent 白跑。
这也符合你论文原本的思路。

伪代码
class AdoptionFlow(Flow):
    @start()
    def load_application(self):
        self.state["app"] = load_application_from_db(self.application_id)

    @listen(load_application)
    def precheck(self):
        result = run_rule_precheck(self.state["app"])
        self.state["precheck"] = result
        if result["block"]:
            self.state["flow_status"] = "manual_review"
        elif result["need_more_info"]:
            self.state["flow_status"] = "need_more_info"
        else:
            self.state["flow_status"] = "expert_review"

这一步基本只是把你现有规则逻辑搬进 Flow。

第三步：把现有专家调用换成 hierarchical crew + custom manager

CrewAI 的 hierarchical process 允许 manager 负责委派和校验。custom manager agent 就是你可控的“总协调者”。

你可以保留的专家
申请人画像 Agent
宠物需求 Agent
环境评估 Agent
风险评估 Agent
解释报告 Agent
新增一个 manager

它不直接给结论，而是做：

决定先调哪几个专家
看专家结果是否冲突
发现缺关键信息时要求追问
最后组织结构化报告
伪代码
from crewai import Agent, Task, Crew, Process

manager = Agent(
    role="Adoption Decision Manager",
    goal="Coordinate expert review and produce a reliable adoption recommendation",
    allow_delegation=True,
)

profile_agent = Agent(...)
pet_need_agent = Agent(...)
risk_agent = Agent(...)
explain_agent = Agent(...)

crew = Crew(
    agents=[profile_agent, pet_need_agent, risk_agent, explain_agent],
    tasks=[profile_task, pet_need_task, risk_task, report_task],
    process=Process.hierarchical,
    manager_agent=manager
)

这里最大的变化不是 Agent 本身，而是 manager 取代了你手写的顺序编排。

第四步：共识层不要等 CrewAI 内置，自己写

因为 CrewAI 官方把 consensual process 标成 planned，所以你最稳的做法是：先跑专家，再自己做一个轻量共识融合器。

你不需要做得很复杂

先做一个简单版本就够论文用了：

每个专家都输出：
score
risk_tags
missing_info
recommendation
再写一个函数：
统计均值
统计分歧度
识别冲突标签
决定是否追问/人工复核
示例逻辑
def consensus_fusion(outputs):
    scores = [o["score"] for o in outputs]
    avg_score = sum(scores) / len(scores)
    disagreement = max(scores) - min(scores)

    merged_risks = sorted(set(tag for o in outputs for tag in o["risk_tags"]))
    merged_missing = sorted(set(f for o in outputs for f in o["missing_info"]))

    if disagreement >= 30 or "housing_conflict" in merged_risks:
        next_action = "need_followup"
    elif avg_score < 50:
        next_action = "manual_review"
    else:
        next_action = "publisher_review"

    return {
        "avg_score": avg_score,
        "disagreement": disagreement,
        "risk_tags": merged_risks,
        "missing_info": merged_missing,
        "next_action": next_action
    }

这就是你的“专家共识层”。
论文里完全可以写成你自己的创新。

第五步：把 human feedback 放在“最终拍板”位置

你前面已经想得很对：最终不是平台一刀切，而是发布者决定。
那最合适的做法就是把 human feedback 放在AI 给出结构化建议之后。

CrewAI 在 Flow 中支持 @human_feedback，会暂停流程、展示结果、收集人工反馈，并且支持根据反馈路由到不同分支；这个能力要求版本 1.8.0 及以上。

你可以这样用

AI 先生成：

申请人画像摘要
适配度评分
风险标签
建议追问
初步建议

然后把它发给发布者或管理员审核：

通过
拒绝
要求补充信息
转人工复核
Flow 伪代码
from crewai.flow.human_feedback import human_feedback

class AdoptionFlow(Flow):
    @listen(run_expert_crew)
    @human_feedback(message="请审核该领养评估报告，并给出：通过/拒绝/补充信息/人工复核")
    def publisher_review(self):
        return self.state["draft_report"]

    @listen(publisher_review)
    def finalize(self, result):
        self.state["publisher_feedback"] = result.feedback
        if "补充" in result.feedback:
            self.state["flow_status"] = "need_more_info"
        elif "人工复核" in result.feedback:
            self.state["flow_status"] = "manual_review"
        elif "拒绝" in result.feedback:
            self.state["flow_status"] = "rejected"
        else:
            self.state["flow_status"] = "approved"

如果你暂时不想上 Flow 的 @human_feedback，也可以先用 Task 的 human_input=True 做更简单的人机介入。官方 Tasks 文档和 Human Input 页面都支持这个属性。

feedback memory 怎么做，才不会很重

这一步很多人会想复杂。
其实你完全可以先做成案例记忆库，不需要一开始就上很复杂的自学习。

CrewAI Memory 支持 scope 树和子树视图，也就是你可以按 /adoption/pet_123、/publisher/user_45、/applicant/user_89 这样的路径存记忆。官方明确说 recall 会限制在对应 scope 内，这样更准、更高效。

你的最小可用实现

把这些写入 memory：

申请摘要
AI 评分与风险标签
发布者最终决定
领养后回访结果
退养/挑战标签
示例
memory.remember(
    "申请人A申请宠物P，AI评分78，发布者要求补充租房许可，最终通过，30天回访良好",
    scope="/adoption/pet_P/cases"
)

下次同类型宠物或同发布者再审核时，先 recall 相似案例。
这就已经足够写成“反馈记忆闭环”。

Execution Hooks 在你项目里最好怎么用

你现稿已经有 AI 日志、trace_id、耗时、fallback_used，这跟 Execution Hooks 非常契合。

CrewAI 的 Execution Hooks 支持在运行时拦截操作、增加安全检查和监控。

你最值得先做的 3 个 hook
LLM 调用前
检查输入 JSON 是否齐全、是否有敏感字段、是否缺关键字段。
LLM 调用后
校验输出是不是你要求的 JSON 结构，缺字段就 fallback。
工具调用前后
记录耗时、异常、重试次数，写入你的 AI 日志表。

这样你原本的日志页就不需要大改，只是日志来源更规范了。

你最小代价的落地顺序

这是我最建议你的版本。

第一阶段：先做 3 个点
Flow 状态机
manager_agent男人
human feedback人类反馈

这三项最能体现“从普通调用升级为多智能体协作机制”，但改动还可控。
而且和你现有论文最容易对接。

第二阶段：再补 2 个点
共识层
feedback memory反馈

这两项更像“深入优化与创新”，适合写成后续增强或论文主创新。

第三阶段：最后再做
execution hooks 全链路治理

这个偏工程加分项，不一定非得先做完。

我帮你直说：哪些地方改动会大，哪些不会
改动不大的
规则预筛逻辑
现有专家 Agent 能力
日志表结构
回访反馈模块
大部分前端页面

这些基本都能复用。

改动中等的
领养评估服务层
AI 调用编排方式
申请状态流转
审核交互逻辑

这些是你真正要重构的核心。

改动较大的
如果你想做“发布者独立审核面板”
如果你想做“复杂记忆召回排序”
如果你想把所有智能模块都迁到 Flow

这些就属于后续扩展，不建议你一开始全做。

最后给你一个明确结论

这套方案对你现有功能来说不是“大改到做不动”，而是“后端编排层的中等重构”。

更直白地说：

不是推倒重来
不是页面全重写
不是数据库全改
真正要改的是：
“原来一次性跑完的智能领养评估，改成一个可分阶段、可追问、可人工拍板、可回写记忆的状态化流程。”

这才是这次升级的本质。
而且它和你论文现有内容是接得上的，不会显得像突然换题。