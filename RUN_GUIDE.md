# 宠物领养平台项目运行指南

本项目采用前后端分离架构。前端基于 **Vue.js 3 + TypeScript + Vite**，后端基于 **FastAPI + CrewAI + ChromaDB**。

## 1. 环境准备

确保您的系统中已安装以下软件：
- **Node.js** (推荐 v18 或更高版本)
- **Python** (推荐 v3.10 或更高版本)
- **Git**

---

## 2. 后端配置与运行 (Python)

后端位于项目根目录下的 `src` 文件夹中。

### 2.1 激活环境 (pet_adoption)
在项目根目录下运行：
```powershell
# 如果使用 Conda (推荐)
conda activate pet_adoption

# 如果使用 venv
.\pet_adoption\Scripts\activate
```

### 2.2 安装依赖
```powershell
pip install -r requirements.txt
```

### 2.3 初始化数据库
在启动应用前，请确保数据库已初始化：
```powershell
python src/database/init_db.py
```

### 2.4 启动后端服务
运行 FastAPI 应用（默认运行在 `http://127.0.0.1:8000`）：
```powershell
uvicorn src.web.app:app --reload
```

---

## 3. 前端配置与运行 (Vue.js)

前端位于 `pet-frontend` 文件夹中。

### 3.1 进入前端目录
```powershell
cd pet-frontend
```

### 3.2 安装依赖
```powershell
npm install
```

### 3.3 启动开发服务器
```powershell
npm run dev
```
启动后，您可以在浏览器中访问控制台输出的地址（通常是 `http://localhost:5173`）。

---

## 4. 注意事项

- **API 跨域问题**：后端已配置 CORS，允许来自前端开发服务器的请求。
- **AI 功能**：智能匹配和宠物专家功能依赖于 LLM 模型，请确保在环境变量或 `CREDENTIALS.md` 中正确配置了您的 API Key（如 OpenAI 或 Google Gemini）。
- **知识库**：ChromaDB 知识库位于 `src/database/data/knowledge`，如需更新知识库，请查看 `src/database/sync_data.py`。

---

## 5. 常用命令清单

| 功能 | 命令 | 目录 |
| :--- | :--- | :--- |
| 启动后端 | `uvicorn src.web.app:app --reload` | 根目录 |
| 启动前端 | `npm run dev` | `pet-frontend` |
| 初始化 DB | `python src/database/init_db.py` | 根目录 |
| 同步知识库 | `python src/database/sync_data.py` | 根目录 |


## 6. 新增功能：营养与喂养专家

前端访问路径：`/nutrition`。

输入：宠物类型、年龄（月）、体重（kg）、绝育状态、活动量、目标、粮食能量密度。

后端接口：`POST /api/nutrition/plan`，返回结构化喂养建议：
- 每日热量（kcal/day）
- 每日喂食量（g/day）
- 喂食频次与每餐克数
- 饮水建议
- 禁忌食物清单
- 7日换粮计划与风险提示

该功能适用于毕业设计中的“可量化智能推荐”展示。


## 7. 前后端接口对齐说明（新增）

为保证 Vue 前端页面可直接联调，后端已补齐以下接口：
- 认证：`/api/register`, `/api/login`
- 社区：`/api/posts`, `/api/posts/{id}/like`, `/api/posts/comment`, `/api/posts/{id}/comments`
- 智能：`/api/chat`, `/api/triage/analyze`, `/api/pets/smart-match`, `/api/nutrition/plan`
- 私信：`/api/messages/{user_id}`, `/api/messages/send`
- 用户中心：`/api/user/change-password`, `/api/user/applications/{user_id}`
- 管理端：`/api/admin/users`, `/api/admin/users/sanction`, `/api/admin/users/reactivate`, `/api/admin/applications`, `/api/admin/applications/update`, `/api/admin/moderation/logs`

说明：智能接口优先尝试多智能体调用，失败时自动降级为规则/模板回复，保证系统可用性。
