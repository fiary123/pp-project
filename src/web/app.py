import os
import sys
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 全局日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.web.routers import auth, community, ai, admin, user
from src.web.services.db_service import get_db_connection, ensure_tables
from src.database.sync_data import sync_knowledge_to_chroma

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
app.include_router(user.compat_router)

@app.on_event("startup")
async def startup_event():
    # 确保数据库表已创建
    conn = get_db_connection()
    ensure_tables(conn)
    conn.close()
    # 确保宠物健康知识库已同步到 ChromaDB（仅在知识库为空时执行）
    try:
        import chromadb
        from src.database.db_config import CHROMA_DB_PATH
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_or_create_collection(name="pet_knowledge")
        if collection.count() == 0:
            logger.info("ChromaDB 知识库为空，开始同步宠物健康知识库...")
            sync_knowledge_to_chroma()
            logger.info("ChromaDB 知识库同步完成。")
        else:
            logger.info(f"ChromaDB 知识库已就绪，共 {collection.count()} 条记录。")
    except Exception as e:
        logger.warning(f"ChromaDB 知识库初始化失败（不影响主功能）: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
