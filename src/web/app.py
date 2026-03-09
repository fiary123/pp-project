import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.web.routers import auth, community, ai, admin, user
from src.web.services.db_service import get_db_connection, ensure_tables

app = FastAPI(title="智慧宠物养护与领养管理系统 API")

# 跨域资源共享配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传目录存在
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 包含各个模块路由
app.include_router(auth.router)
app.include_router(community.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(user.router)

@app.on_event("startup")
async def startup_event():
    # 应用启动时确保数据库表已创建
    conn = get_db_connection()
    ensure_tables(conn)
    conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
