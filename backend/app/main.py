"""
FastAPI 应用主入口

FinanceAI Platform 后端服务
"""

import logging
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Use the repo's unified logging pipeline (stdout + rotating files with context).
# This must run before importing Pydantic models to capture early warnings/logs.
try:
    from AICrews.observability.logging import configure_logging

    configure_logging(force=True)
    logging.captureWarnings(True)
except Exception as exc:
    warnings.warn(f"Failed to configure unified logging: {exc!r}")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

logger = logging.getLogger(__name__)

from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.lifespan import lifespan
from backend.app.security import get_current_user_optional
from backend.app.ws.router import router as ws_router


app = FastAPI(
    title="FinanceAI Platform API",
    description="""
    ## 多智能体金融分析平台 API
    
    提供基于 CrewAI 的智能金融分析服务。
    
    ### 功能特性
    - 📊 **多策略分析**: 支持巴菲特、索罗斯、桥水等投资风格
    - 🤖 **智能辩论**: 多个 AI 智能体协作分析
    - 💬 **AI 助手**: 针对分析结果进行深入对话
    - 📈 **实时进度**: 任务状态实时查询
    
    ### 使用流程
    1. 调用 `/api/v1/analysis/start` 提交分析任务
    2. 使用 `/api/v1/analysis/status/{job_id}` 轮询状态
    3. 任务完成后获取 Markdown 格式的分析报告
    4. 可选：使用 `/api/v1/chat` 与 AI 助手讨论报告
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 配置 - 允许前端访问
CORS_ORIGINS = [
    "http://localhost:3000",      # Next.js 开发服务器
    "http://127.0.0.1:3000",
    "http://localhost:3001",      # 备用端口
    "http://127.0.0.1:3001",
    "http://localhost:3002",      # 备用端口
    "http://127.0.0.1:3002",
    "http://localhost:8000",
    "http://localhost",           # Nginx Gateway (端口 80)
    "http://127.0.0.1",
]

# 支持通过环境变量添加额外的 CORS 源
extra_origins = os.getenv("CORS_ORIGINS", "")
if extra_origins:
    CORS_ORIGINS.extend([origin.strip() for origin in extra_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 允许前端访问响应头
)

# 🆕 Prometheus Metrics 端点
try:
    from prometheus_client import make_asgi_app, CollectorRegistry

    # 创建共享的 registry（确保所有 metrics 使用同一个 registry）
    shared_registry = CollectorRegistry()

    # 挂载 Prometheus metrics 端点（使用共享 registry）
    metrics_app = make_asgi_app(registry=shared_registry)
    app.mount("/metrics", metrics_app)

    # 设置共享 registry（供 TrackingService 的 get_metrics() 使用）
    from AICrews.infrastructure.metrics import set_shared_registry
    set_shared_registry(shared_registry)

    logger.info("Prometheus /metrics endpoint mounted with shared registry")
except ImportError:
    logger.warning("prometheus-client not installed, /metrics endpoint not available")
except Exception as e:
    logger.warning(f"Failed to initialize Prometheus metrics: {e}")

# 注册 API / WebSocket 路由
app.include_router(api_v1_router)
app.include_router(ws_router)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Minimal health check for load balancers and monitoring.

    Public endpoint - returns only status to minimize information disclosure.
    For detailed dependency checks, use /ready endpoint (requires authentication).
    """
    return {"status": "ok"}


@app.get("/ready", tags=["System"])
async def readiness_check(current_user=Depends(get_current_user_optional)):
    """
    Detailed readiness check with dependency health.

    Requires authentication - returns service status for monitoring.
    """
    from AICrews.database.db_manager import DBManager
    from AICrews.infrastructure.cache.redis_manager import get_redis_manager

    # Check database
    db_status = "ok"
    try:
        db = DBManager()
        with db.get_session() as session:
            # Simple query to test connection (SQLAlchemy 2.0 style)
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check Redis
    redis_status = "ok"
    try:
        redis_manager = get_redis_manager()
        # Get the async client and ping Redis
        if redis_manager._client is not None:
            await redis_manager._client.ping()
        else:
            redis_status = "error: Redis client not initialized"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "ready",
        "version": app.version,
        "timestamp": datetime.now().isoformat(),
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
        }
    }


@app.get("/", include_in_schema=False)
async def root():
    """根路径"""
    return {
        "name": "FinanceAI Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=[
            ".crewai",
            ".crewai/*",
            ".data",
            ".data/*",
            "*.json",
            "*.log",
            "__pycache__",
        ],
    )
