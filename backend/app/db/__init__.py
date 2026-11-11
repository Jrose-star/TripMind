"""数据库连接层：PostgreSQL 连接池（asyncpg）。

采用连接池复用，避免每次请求都新建连接。
- 应用启动时初始化池（main.py lifespan）
- 各存储层通过 get_pool() 取池执行 SQL
- 数据库不可用时降级为空操作（不阻塞主链路）
"""

from __future__ import annotations

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """初始化连接池（应用启动时调用）。"""
    global _pool
    if _pool is not None:
        return
    if not settings.postgres_dsn:
        return  # 未配置 DSN，跳过（数据库能力禁用）
    try:
        _pool = await asyncpg.create_pool(
            settings.postgres_dsn,
            min_size=1,
            max_size=10,
        )
    except Exception:
        # 数据库连不上时不崩溃，后续操作走降级
        _pool = None


async def close_pool() -> None:
    """关闭连接池（应用关闭时调用）。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool | None:
    """获取连接池（可能为 None，表示数据库未启用）。"""
    return _pool


async def is_available() -> bool:
    """数据库是否可用（供健康检查）。"""
    pool = get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False
