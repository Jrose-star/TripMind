"""Checkpointer 管理层：Redis 持久化（可用时）+ 内存降级（不可用时）。

设计目标：
- 优先用 Redis 存储 LangGraph 状态（多轮追问的 checkpoint），
  让对话状态在服务重启后仍可恢复、多实例间可共享。
- Redis 未配置或不可用时，自动降级为内存 MemorySaver，
  保持"不阻塞主链路"的既有约定（与 PostgreSQL 连接池降级一致）。

说明：LangGraph 的 checkpointer 是同步/异步两套。本项目后端为 FastAPI
异步应用，图的调用走 ainvoke / astream，因此使用 AsyncRedisSaver。
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.config import settings

logger = logging.getLogger(__name__)

# 自定义序列化白名单：让 checkpointer 能安全地序列化/反序列化我们的 Pydantic 类型，
# 消除 "Deserializing unregistered type" 警告。
CUSTOM_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ("app.agents.state", "TravelRequirement"),
        ("app.agents.state", "POI"),
        ("app.agents.state", "DayPlan"),
        ("app.agents.state", "BudgetResult"),
        ("app.agents.state", "WeatherInfo"),
        ("app.agents.state", "WeatherCast"),
    ]
)


def _memory_checkpointer() -> MemorySaver:
    """内存 checkpointer（降级兜底）。"""
    return MemorySaver(serde=CUSTOM_SERDE)


def build_checkpointer():
    """创建 checkpointer：优先 Redis，不可用则内存降级。

    返回 (checkpointer, kind)，kind ∈ {"redis", "memory"}。
    Redis checkpointer 需由调用方 await setup_checkpointer() 完成索引初始化。
    """
    if not settings.redis_url:
        logger.info("未配置 REDIS_URL，使用内存 checkpointer（重启后追问状态不保留）")
        return _memory_checkpointer(), "memory"

    try:
        # 延迟导入，避免未安装 langgraph-checkpoint-redis 时启动失败
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        # 直接实例化（而非 from_conn_string 的上下文管理器），
        # 拿到持久 saver 实例，由应用生命周期统一管理
        saver = AsyncRedisSaver(redis_url=settings.redis_url)
        return saver, "redis"
    except ImportError:
        logger.warning(
            "未安装 langgraph-checkpoint-redis，使用内存 checkpointer。"
            "如需持久化请执行：uv pip install langgraph-checkpoint-redis"
        )
        return _memory_checkpointer(), "memory"
    except Exception as e:
        logger.warning("Redis checkpointer 初始化失败，降级为内存：%s", e)
        return _memory_checkpointer(), "memory"


async def setup_checkpointer(checkpointer, kind: str) -> bool:
    """对 Redis checkpointer 执行一次性 setup（创建索引，幂等）。

    返回是否 setup 成功。失败时（如 Redis 缺模块/不可达）调用方应降级为内存。
    """
    if kind != "redis":
        return False
    try:
        await checkpointer.asetup()
        logger.info("Redis checkpointer setup 完成，追问状态将持久化")
        return True
    except Exception as e:
        logger.warning("Redis checkpointer setup 失败，将降级为内存：%s", e)
        return False
