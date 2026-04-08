"""Smart Cut API - FastAPI 应用入口

FastAPI 应用主入口，注册所有路由和中间件。
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from configs.database import (
    check_database_connection,
    get_scheduler_database_url,
    init_db,
    init_scheduler_db,
)
from apps.api.routes import api_router

logger = logging.getLogger(__name__)

# ============ 生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理
    
    启动时初始化数据库，关闭时清理资源。
    """
    # 启动时
    init_db()
    scheduler_url = get_scheduler_database_url(fallback_to_database_url=False)
    scheduler_engine = None
    if scheduler_url:
        scheduler_engine = init_scheduler_db(scheduler_url)
        check_database_connection(scheduler_engine)
        logger.info("API scheduler database bootstrap completed")
    yield
    # 关闭时（如有需要可添加清理逻辑）
    if scheduler_engine is not None:
        scheduler_engine.dispose()


# ============ 创建 FastAPI 应用 ============

app = FastAPI(
    title="Smart Cut API",
    description="智能剪辑任务管理服务 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============ CORS 中间件 ============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 异常处理 ============

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理 HTTP 异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数验证异常"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理通用异常"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"}
    )


# ============ 注册路由 ============

# 注册所有 API 路由
app.include_router(api_router)


# ============ 健康检查 ============

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """健康检查端点"""
    return {"status": "healthy"}


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """API 根路径"""
    return {
        "name": "Smart Cut API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# ============ 启动入口 (仅用于开发) ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
