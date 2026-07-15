"""FastAPI 应用入口"""
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.router import router as auth_router
from app.kb.router import router as kb_router
from app.chat.router import router as chat_router
from app.admin.router import router as admin_router
from app.config import settings
from app.database import init_db
from app.logging import logger, set_request_id, new_request_id

# 预导入所有模型，确保 Base.metadata 包含所有表
import app.auth.models  # noqa: F401
import app.kb.models    # noqa: F401
import app.chat.models  # noqa: F401

# 全局限流器
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求注入唯一 ID，用于日志追踪"""
    async def dispatch(self, request: Request, call_next):
        rid = new_request_id()
        set_request_id(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和种子数据"""
    # 启动前校验
    if not settings.jwt_secret_key:
        logger.error("JWT_SECRET_KEY 未配置！请在 .env 中设置或通过环境变量传入")
        raise RuntimeError("JWT_SECRET_KEY is required")

    if not settings.dashscope_api_key:
        logger.error("DASHSCOPE_API_KEY 未配置！请在 .env 中设置或通过环境变量传入")
        raise RuntimeError("DASHSCOPE_API_KEY is required")

    await init_db()

    # 确保管理员账号存在
    from app.auth.utils import hash_password
    from app.database import async_session_factory
    from sqlalchemy import select
    from app.auth.models import User

    admin_password = os.getenv("ADMIN_PASSWORD", "")

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if admin is None:
            if not admin_password:
                admin_password = secrets.token_urlsafe(12)
                logger.info("未设置 ADMIN_PASSWORD 环境变量，已生成随机密码")
            admin = User(
                username="admin",
                password_hash=hash_password(admin_password),
                email="admin@example.com",
                role="admin",
            )
            db.add(admin)
            await db.commit()
            logger.info(f"管理员账号已创建 — 用户名: admin, 密码: {admin_password}")
            logger.warning("请立即登录并修改管理员密码！")

    logger.info(f"服务启动 — http://{settings.host}:{settings.port}")
    logger.info(f"API 文档 — http://{settings.host}:{settings.port}/docs")
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="企业级 RAG 知识库问答系统",
    description="基于 LangChain + 阿里云百炼的知识库问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册限流器的异常处理器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request ID 中间件（需在 CORS 之前）
app.add_middleware(RequestIDMiddleware)

# CORS 中间件
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "RAG 知识库问答系统运行中"}


@app.get("/api/health")
async def health():
    """健康检查接口"""
    return {"status": "healthy"}
