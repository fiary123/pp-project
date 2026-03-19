# 🐾 智慧宠物养护与领养管理系统 (Smart Pet Care & Adoption System)

> **2026届毕业设计项目**：基于 FastAPI 与多智能体协同架构的综合性宠物服务平台。

本系统不仅是一个传统的领养与社区平台，更是一个集成了 **AI 营养专家**、**风险分诊专家** 和 **百科知识库** 的智能化养护系统。通过多智能体（Multi-Agent）协同工作，为用户提供科学、动态、可追溯的宠物养护建议。

---

## 🌟 核心亮点 (Thesis Highlights)

- **🚀 现代化模块化架构**：从单体脚本重构为 FastAPI 驱动的 **Router-Service-Dependency** 三层架构，确保高内聚、低耦合。
- **🤖 多智能体闭环优化**：首创“初始方案 -> 执行反馈 -> 动态再规划”的营养闭环系统，引入 `confidence_level`（置信度）量化 AI 建议。
- **🛡️ 工业级安全标准**：采用 **JWT** 无状态认证与 **Bcrypt** 密码哈希存储，严格保护用户信息。
- **📊 智能体全链路可观测**：内置 `agent_trace_logs` 审计体系，实时记录 AI 决策路径、调用工具及毫秒级响应延迟，解决 AI “黑盒”问题。
- **📉 完备的评估体系**：通过 100+ 真实样本进行 A/B 对照实验，量化证明多智能体系统在复杂场景下的优越性。

---

## 🛠️ 技术栈 (Tech Stack)

| 领域 | 技术方案 |
| :--- | :--- |
| **前端** | Vue 3 + Vite + TypeScript + Pinia |
| **后端** | FastAPI (Python 3.11+) + Uvicorn |
| **AI 引擎** | CrewAI + LangChain + OpenAI/Gemini API |
| **数据库** | SQLite (关系型) + ChromaDB (向量库) |
| **安全/工具** | JWT + Bcrypt + Pydantic v2 |

---

## 📦 功能模块 (Modules)

1.  **AI 智能助手**：基于检索增强生成 (RAG) 的宠物养护百科咨询。
2.  **动态营养专家**：根据宠物品种、年龄、运动量及反馈数据，动态调整 DER/RER 营养配比。
3.  **风险分诊系统**：模拟医学专家逻辑，对宠物异常症状进行风险分级（Low/Medium/High/Emergency）。
4.  **智能宠物匹配**：基于语义理解为领养者推荐最契合的宠物伴侣。
5.  **互动社区与领养**：支持动态发布、评论、私信、领养申请及管理员多级审核。
6.  **管理审计后台**：管理员可查阅 AI Trace 日志、管控用户状态及审核违规内容。

---

## 🚀 快速启动 (Quick Start)

### 1. 环境准备
确保已安装 Python 3.11+ 和 Node.js 18+。

### 2. 后端配置与启动
```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000 --reload
```

### 3. 前端配置与启动
```bash
cd pet-frontend
npm install
npm run dev
```

### 4. 评估实验运行 (用于论文数据收集)
```bash
$env:PYTHONPATH="."
python tests/eval_engine.py
```

---

## 📂 核心目录结构 (Project Structure)

```text
project/
├── src/
│   ├── web/                # Web 后端核心
│   │   ├── routers/        # 模块化路由 (auth, ai, community, admin, user)
│   │   ├── services/       # 核心业务逻辑 (AI 调度, 数据库操作)
│   │   ├── schemas.py      # Pydantic 数据模型
│   │   └── dependencies.py # JWT 鉴权与权限校验依赖
│   └── agents/             # AI 智能体逻辑 (CrewAI, LangChain)
├── pet-frontend/           # Vue 3 前端源码
├── tests/                  # 自动化测试与 A/B 对照实验脚本
├── docs/                   # 架构图、评估报告及演示指南
└── static/uploads/         # 资源上传目录
```

---

## 📖 演示指南
详细的演示场景（如营养再规划、高风险分诊、审计追踪）请参考 `docs/EVALUATION.md`。

---

## ⚖️ 局限性与展望
目前系统对语义解析深度及物种覆盖度（主要为猫犬）仍有提升空间。未来计划引入图像识别进行 BCS 自动评分，并对接地域化宠物医院地理信息。

---
**设计者**：[你的名字]  
**指导老师**：[老师的名字]  
**完成时间**：2026年3月
