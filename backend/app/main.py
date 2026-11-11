"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, history, plan
from app.db import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库连接池，关闭时释放。"""
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="旅行规划 Agent", version="0.1.0", lifespan=lifespan)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(plan.router, prefix="/api", tags=["plan"])
app.include_router(history.router, prefix="/api", tags=["history"])
