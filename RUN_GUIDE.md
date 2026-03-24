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

## 6. 安全配置（必读）

### 6.1 JWT 密钥

`JWT_SECRET_KEY` **必须**设置，否则后端启动时会直接报错退出。
请用以下命令生成一个高强度随机密钥，填入 `.env`：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 6.2 AI 模型配置（DeepSeek）

本项目使用 **DeepSeek** 模型服务（兼容 OpenAI 接口），在 `.env` 中配置：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

> **隐私说明**：用户在聊天、营养方案、领养评估、互助匹配等功能中输入的文字内容会被发送至 DeepSeek 模型服务进行处理。
> 请在实际部署前确认：
> - 是否符合所在组织/学校的数据合规要求
> - 是否需要向用户展示数据处理声明
> - DeepSeek 服务隐私政策：https://www.deepseek.com/privacy

如需替换为其他模型（如本地 Ollama、其他 API），修改以下两个环境变量即可：
```env
DEEPSEEK_BASE_URL=http://localhost:11434/v1   # Ollama 示例
DEEPSEEK_API_KEY=ollama                        # Ollama 不需要真实 key
```

### 6.3 CORS 跨域白名单

默认仅允许本地开发端口，**生产部署时必须修改**：

```env
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 6.4 Token 有效期

默认 60 分钟，调试时可临时改为 1440（24 小时）：

```env
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## 7. 注意事项

- **知识库**：ChromaDB 知识库位于 `src/database/data/knowledge`，如需更新请运行 `python src/database/sync_data.py`。
- **智能接口降级**：AI 接口不可用时自动降级为规则/模板回复，保证系统基本可用性。
- **`.env` 文件**：包含敏感密钥，已加入 `.gitignore`，请勿提交到版本库。

---

## 8. 已有接口清单

- 认证：`/api/register`, `/api/login`
- 宠物：`/api/pets`, `/api/pets/{id}`, `/api/pets/smart-match`
- 社区：`/api/posts`, `/api/posts/{id}/like`, `/api/posts/{id}/comments`
- 智能：`/api/chat`, `/api/nutrition/plan`, `/api/adoption/assess`, `/api/mutual-aid/tasks`, `/api/mutual-aid/match`
- 用户：`/api/user/change-password`, `/api/user/applications/{user_id}`
- 管理：`/api/admin/users`, `/api/admin/users/sanction`, `/api/admin/users/reactivate`, `/api/admin/applications`, `/api/admin/applications/update`, `/api/admin/moderation/logs`, `/api/admin/mutual-aid/stats`, `/api/admin/mutual-aid/reports`
- 其他：`/api/announcements`, `/api/upload`

---

## 9. 功能模块说明

| 模块 | 前端路径 | 说明 |
| :--- | :--- | :--- |
| 首页 | `/` | 公告栏、平台导航 |
| 领养中心 | `/adopt` | 宠物列表、AI 智能匹配、领养资质评估 |
| 社区 | `/community` | 帖子发布、点赞、评论 |
| 百科 | `/wiki` | 宠物养护知识、AI 专家问答 |
| 宠物互助 | `/mutual-aid` | 发布/接单互助任务，AI 双智能体匹配推荐 |
| 营养规划 | `/nutrition` | 输入宠物参数，生成个性化喂养方案 |
| 个人中心 | `/profile` | 修改密码、查看领养申请记录 |
| 管理后台 | `/dashboard` | 审核申请、用户管理、发布公告、互助监控（管理员专属） |

---

## 10. 演示账号

| 账号 | 密码 | 角色 | 说明 |
| :--- | :--- | :--- | :--- |
| `admin@demo.com` | `admin123` | org_admin | 管理员，可访问后台 |
| `demo@demo.com` | `demo123` | individual | 普通用户 |

> 如需重建演示账号，运行：`python scripts/create_demo_accounts.py`
