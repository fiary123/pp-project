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
