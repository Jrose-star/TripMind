"""Agent 编排包。

app_graph / planning_graph 为默认（内存 checkpointer）编译实例。
应用启动时（main.py lifespan）若配置了 Redis，会调用 init_checkpointing()
重新编译为 Redis 持久化版本，并更新本模块的全局引用。
"""

from app.agents.graph import app_graph, planning_graph, build_graph, build_planning_graph
from app.agents import checkpointer as _checkpointer

__all__ = [
    "app_graph",
    "planning_graph",
    "build_graph",
    "build_planning_graph",
    "init_checkpointing",
]


async def init_checkpointing() -> None:
    """应用启动时调用：用 Redis checkpointer 重新编译图（若 Redis 可用）。

    若 Redis 未配置/不可用/setup 失败，则保持默认内存 checkpointer，不改变现有行为。
    """
    global app_graph, planning_graph

    cp, kind = _checkpointer.build_checkpointer()

    if kind == "redis":
        ok = await _checkpointer.setup_checkpointer(cp, kind)
        if ok:
            app_graph = build_graph(checkpointer=cp)
            planning_graph = build_planning_graph(checkpointer=cp)
        # setup 失败时保持内存版本，不影响主链路
