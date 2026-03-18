# 智慧宠物养护系统架构说明 (毕业设计参考)

## 1. 系统总体架构图 (Layered Architecture)

系统采用典型的前后端分离架构，核心逻辑由多智能体协同引擎驱动。各层职责清晰，通过依赖注入和服务层解耦，符合单一职责原则。

### [表现层] (Frontend)
- **技术栈**: Vue 3 + Vite + TypeScript + TailwindCSS + Pinia
- **核心模块**:
  - 智能助手交互 (Chat)
  - 动态营养看板 (Nutrition)
  - 风险分诊报告 (Triage)
  - 管理员溯源后台 (Admin Trace)

### [接口与业务逻辑层] (FastAPI Backend)

路由模块按单一职责原则拆分，每个文件只负责一类业务：

- **API Routers**:
  - `auth.py`: JWT 鉴权与 Bcrypt 安全加密，含限流保护。
  - `ai.py`: 多智能体任务分发（分诊/营养/问答/智能匹配）。
  - `posts.py`: 帖子与评论管理，所有写操作需登录鉴权。
  - `pets.py`: 宠物信息管理，修改/删除需验证所有权。
  - `announcements.py`: 公告管理，创建/删除仅限管理员。
  - `uploads.py`: 文件上传，含魔数检测与大小限制。
  - `admin.py`: 权限校验与审计日志。
  - `user.py`: 用户个人数据（密码修改需 bcrypt 验证，消息/申请仅限本人访问）。

- **Services**:
  - `ai_service.py`: 封装 Agent 调用、耗时统计与 Trace 记录，含 Fallback 降级。
  - `auth_service.py`: JWT 签发/解析，bcrypt 密码哈希。
  - `db_service.py`: 数据库连接上下文管理（统一使用 `with get_db()` 防止连接泄漏）。

- **Security**:
  - `dependencies.py`: `get_current_user` / `require_admin` 依赖注入，RBAC 三级权限。
  - 所有敏感配置（JWT 密钥、AI API Key、地图 API Key）统一从 `.env` 环境变量读取。

### [多智能体协同层] (Multi-Agent Layer)
- **Agent Roles**:
  - **NutritionPlanner**: 负责计算 RER/DER（基于 Kleiber 定律）及个性化配餐规划。
  - **NutritionOptimizer**: 基于执行反馈的闭环优化，输出置信度评分（本系统核心亮点）。
  - **TriageExpert**: 基于 ChromaDB 医学知识库的分诊决策，输出风险等级。
  - **KnowledgeExpert**: 宠物饲养百科知识 RAG 检索。
- **Safety Mechanism**:
  - **Fallback Engine**: ChromaDB 或 LLM API 故障时自动降级至本地规则引擎，保证核心功能不中断。
  - **Agent Trace Log**: 每次 AI 调用均记录 `trace_id`、`latency_ms`、`fallback_used`，支持审计溯源。

### [数据持久层] (Data Layer)
- **关系型数据库**: SQLite（含索引优化：email、post create_time、trace_id 等高频查询字段）
  - 表：users, posts, pets, applications, comments, messages, announcements, moderation_logs, user_sanctions, agent_trace_logs, nutrition_plans, nutrition_feedbacks, adopt_records
- **向量数据库**: ChromaDB（宠物健康知识库，支持语义 RAG 检索，启动时自动同步）

---

## 2. 安全设计说明 (Security Design)

| 安全层面 | 实现方式 |
|---------|---------|
| 身份认证 | JWT Bearer Token，24小时过期，`jose` 库签发/验证 |
| 密码存储 | bcrypt 哈希，`passlib` 管理，禁止明文存储与比对 |
| 权限控制 | RBAC 三级（individual / org_admin / root），路由级 `Depends` 注入 |
| 资源鉴权 | 写操作验证资源归属（只能操作自己的帖子/消息/申请） |
| 文件上传 | 魔数（Magic Bytes）检测真实类型，限制 10MB，UUID 文件名防路径遍历 |
| 限流保护 | `slowapi` 对登录(10/min)、注册(5/min)、AI接口(10-20/min) 独立限流 |
| 敏感配置 | 所有 API Key / 密钥通过 `.env` + `os.getenv()` 管理，不硬编码 |

---

## 3. 核心业务时序图 (Sequence Diagram) - 以营养再规划为例

1. **用户** -> **Web 端**: 提交宠物近 7 天体重/食欲/排便反馈数据
2. **Web 端** -> **AI API** (`/api/nutrition/replan`): 携带 JWT Token 请求
3. **AI API** -> **dependencies**: 验证 Token 及用户状态
4. **AI API** -> **AI Service**: 检索原始方案 ID 及对应反馈记录
5. **AI Service** -> **NutritionOptimizer (Agent)**:
   - 分析体重变化趋势与喂食执行情况
   - 判定是否存在医疗风险（requires_vet）
6. **NutritionOptimizer** -> **AI Service**: 生成调整方案（daily_kcal 调整 + 置信度）
7. **AI Service** -> **agent_trace_logs**: 记录执行路径、耗时及 fallback_used
8. **AI Service** -> **nutrition_plans**: 持久化新方案，标记旧方案为历史状态
9. **AI API** -> **用户**: 返回带”置信度”评分的全新营养报告
