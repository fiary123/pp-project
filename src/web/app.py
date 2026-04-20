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
from contextlib import asynccontextmanager

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

# 全局日志配置
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

from src.web.routers import auth, ai, admin, user, profile, recommendation
from src.web.routers import posts, pets, announcements, uploads
from src.web.services.db_service import get_db, ensure_tables
from src.database.sync_data import sync_knowledge_to_chroma

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动逻辑 (Startup) ---
    logger.info("系统正在启动 (Lifespan Mode)...")
    try:
        # 确保数据库表已创建
        with get_db() as conn:
            ensure_tables(conn)
        
        # 确保宠物健康知识库已同步到 ChromaDB
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
            logger.warning(f"ChromaDB 知识库初始化跳过或失败: {e}")
            
    except Exception as e:
        logger.error(f"启动时发生致命错误: {e}")

    yield
    # --- 关闭逻辑 (Shutdown) ---
    logger.info("系统正在关闭...")

app = FastAPI(title="智慧宠物养护与领养管理系统 API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# 跨域资源共享配置
_default_dev_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://192.168.1.80:5173"
_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", _default_dev_origins)
ALLOWED_ORIGINS = [origin.strip() for origin in _origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传目录存在
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
app.include_router(profile.router)
app.include_router(recommendation.router)

if __name__ == "__main__":
    import uvicorn
    # 在 Windows 环境下，使用 lifespan 模式能更好地处理 KeyboardInterrupt
    uvicorn.run(app, host="0.0.0.0", port=8000)
