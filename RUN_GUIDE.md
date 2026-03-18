# 宠物领养平台项目运行指南

本项目采用前后端分离架构。前端基于 **Vue.js 3 + TypeScript + Vite**，后端基于 **FastAPI + CrewAI + ChromaDB**。

---

## 1. 环境准备

确保您的系统中已安装以下软件：
- **Node.js** (推荐 v18 或更高版本)
- **Python** (推荐 v3.10 或更高版本)
- **Git**

---

## 2. 每次启动步骤

打开**两个终端**，分别运行：

**终端 1 — 后端：**
```powershell
conda activate pet_adoption
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 — 前端：**
```powershell
cd pet-frontend
npm run dev
```

启动后浏览器访问 **http://127.0.0.1:5173**

> **首次运行前**，请先完成第 3 节的环境初始化。

---

## 3. 首次运行初始化

### 3.1 激活 Python 环境

```powershell
conda activate pet_adoption
```

### 3.2 安装 Python 依赖

```powershell
pip install -r requirements.txt
```

### 3.3 安装前端依赖

```powershell
cd pet-frontend
npm install
cd ..
```

### 3.4 初始化数据库

```powershell
python src/database/init_db.py
```

> 以上步骤只需执行一次。之后每次启动直接双击 `启动SmartPet.bat` 即可。

---

## 4. 访问地址

| 场景 | 地址 |
| :--- | :--- |
| 本机访问前端 | http://127.0.0.1:5173 |
| 本机访问后端 API | http://127.0.0.1:8000 |
| 本机查看 API 文档 | http://127.0.0.1:8000/docs |
| **局域网其他设备访问** | http://本机IP:5173 |

**查询本机 IP（局域网演示用）：**
```powershell
ipconfig
# 找到形如 192.168.x.x 的地址，其他设备用该地址访问
```

---

## 5. 手动启动（备用）

如需手动启动，请在项目根目录执行：

| 功能 | 命令 | 目录 |
| :--- | :--- | :--- |
| 启动后端 | `uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000` | 根目录 |
| 启动前端 | `npm run dev` | `pet-frontend` |
| 初始化 DB | `python src/database/init_db.py` | 根目录 |
| 同步知识库 | `python src/database/sync_data.py` | 根目录 |

---

## 6. 注意事项

- **AI 功能**：智能匹配、宠物专家等功能依赖 LLM，请确保根目录 `.env` 文件中已正确配置 `OPENAI_API_KEY`。
- **知识库**：ChromaDB 知识库位于 `src/database/data/knowledge`，如需更新请运行 `python src/database/sync_data.py`。
- **智能接口降级**：AI 接口不可用时自动降级为规则/模板回复，保证系统基本可用性。

---

## 7. 已有接口清单

- 认证：`/api/register`, `/api/login`
- 宠物：`/api/pets`, `/api/pets/{id}`, `/api/pets/smart-match`
- 社区：`/api/posts`, `/api/posts/{id}/like`, `/api/posts/{id}/comments`
- 智能：`/api/chat`, `/api/triage/analyze`, `/api/nutrition/plan`, `/api/adoption/assess`
- 用户：`/api/user/change-password`, `/api/user/applications/{user_id}`
- 管理：`/api/admin/users`, `/api/admin/users/sanction`, `/api/admin/users/reactivate`, `/api/admin/applications`, `/api/admin/applications/update`, `/api/admin/moderation/logs`
- 其他：`/api/announcements`, `/api/upload`

---

## 8. 功能模块说明

| 模块 | 前端路径 | 说明 |
| :--- | :--- | :--- |
| 首页 | `/` | 公告栏、平台导航 |
| 领养中心 | `/adopt` | 宠物列表、AI 智能匹配、领养资质评估 |
| 社区 | `/community` | 帖子发布、点赞、评论 |
| 百科 | `/wiki` | 宠物养护知识、AI 专家问答 |
| 智能分诊 | `/triage` | 上传症状图片/描述，AI 预诊 |
| 营养规划 | `/nutrition` | 输入宠物参数，生成个性化喂养方案 |
| 个人中心 | `/profile` | 修改密码、查看领养申请记录 |
| 管理后台 | `/dashboard` | 审核申请、用户管理、发布公告（管理员专属） |
