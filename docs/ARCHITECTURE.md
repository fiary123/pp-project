# 智慧宠物养护系统架构说明 (毕业设计参考)

## 1. 系统总体架构图 (Layered Architecture)

系统采用典型的前后端分离架构，核心逻辑由多智能体协同引擎驱动。

### [表现层] (Frontend)
- **技术栈**: Vue 3 + Vite + TypeScript + TailwindCSS (Optional)
- **核心模块**: 
  - 智能助手交互 (Chat)
  - 动态营养看板 (Nutrition)
  - 风险分诊报告 (Triage)
  - 管理员溯源后台 (Admin Trace)

### [接口与业务逻辑层] (FastAPI Backend)
- **API Routers**: 
  - `auth.py`: JWT 鉴权与 Bcrypt 安全加密。
  - `ai.py`: 多智能体任务分发。
  - `community.py`: 动态与公告管理。
  - `admin.py`: 权限校验与审计日志。
- **Services**:
  - `ai_service.py`: 封装 Agent 调用、耗时统计与 Trace 记录。
  - `db_service.py`: 数据库版本化与持久化。

### [多智能体协同层] (Multi-Agent Layer)
- **Agent Roles**:
  - **NutritionPlanner**: 负责计算 RER/DER 及配餐规划。
  - **TriageExpert**: 基于医学知识库的分诊决策。
  - **KnowledgeExpert**: 宠物饲养百科知识检索。
  - **NutritionOptimizer**: 基于执行反馈的闭环优化（本系统核心亮点）。
- **Safety Mechanism**: 
  - **Fallback Engine**: 在依赖（如向量库）故障时自动切换至规则引擎。

### [数据持久层] (Data Layer)
- **Relational**: SQLite (User, Post, Application, TraceLog, NutritionPlan)
- **Vector DB**: ChromaDB (Pet Encyclopedia, Medical Knowledge)

---

## 2. 核心业务时序图 (Sequence Diagram) - 以营养再规划为例

1. **用户** -> **Web 端**: 提交宠物近 7 天体重/食欲反馈数据
2. **Web 端** -> **AI API**: 调用 `/api/nutrition/replan`
3. **AI API** -> **AI Service**: 检索原始方案 ID 及对应的反馈记录
4. **AI Service** -> **NutritionOptimizer (Agent)**: 
   - 分析权重变化趋势
   - 判定是否存在医疗风险 (Requires_Vet)
5. **NutritionOptimizer** -> **AI Service**: 生成调整方案 (Daily_Kcal 调整 + 复查建议)
6. **AI Service** -> **Trace Log**: 记录执行路径、耗时及 Agent 状态
7. **AI Service** -> **Database**: 持久化新方案，标记旧方案为历史状态
8. **AI API** -> **用户**: 展示带有“置信度”评分的全新营养报告
