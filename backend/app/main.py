from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from app.core.config import get_settings
from app.api import auth, users, dashboard, market, watchlist, portfolio, journal, ai_assistant, assets, admin
from app.models.database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)
if settings.AUTO_SEED_DB:
    from app.data.seed_data import seed_all
    seed_all()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI驱动的每日股票复盘与价值投资研究系统",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(market.router, prefix="/api/market", tags=["市场行情"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["自选股"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["持仓组合"])
app.include_router(journal.router, prefix="/api/journal", tags=["投资日志"])
app.include_router(ai_assistant.router, prefix="/api/ai", tags=["AI助手"])
app.include_router(assets.router, prefix="/api/assets", tags=["资产配置"])
app.include_router(admin.router, prefix="/api/admin", tags=["后台管理"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
