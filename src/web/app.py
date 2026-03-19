import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.web.limiter import limiter

# 项目根目录（绝对路径，避免因 cwd 变化导致路径错误）
BASE_DIR = Path(__file__).parent.parent.parent

# 全局日志配置（日志写入 logs/ 目录）
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# 将项目根目录添加到 sys.path
sys.path.append(str(BASE_DIR))

from src.web.routers import auth, ai, admin, user
from src.web.routers import posts, pets, announcements, uploads
from src.web.services.db_service import get_db, ensure_tables
from src.database.sync_data import sync_knowledge_to_chroma

app = FastAPI(title="智慧宠物养护与领养管理系统 API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 跨域资源共享配置（限制来源，防止 CSRF）
# 生产环境请通过环境变量 CORS_ALLOWED_ORIGINS 配置域名，多个域名用逗号分隔
# 例如：CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
_default_dev_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", _default_dev_origins)
ALLOWED_ORIGINS = [origin.strip() for origin in _origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传目录存在（使用绝对路径）
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 包含各个模块路由
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(pets.router)
app.include_router(announcements.router)
app.include_router(uploads.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(user.router)

@app.on_event("startup")
async def startup_event():
    # 确保数据库表已创建
    with get_db() as conn:
        ensure_tables(conn)
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
