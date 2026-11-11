"""MCP 客户端封装：通过 MCP 协议调用外部工具（高德 POI 检索等）。

本模块负责「后端作为 MCP 客户端」这一侧的逻辑：
- 通过 stdio 传输启动 mcp/server.py 作为子进程 MCP Server
- 用 langchain_mcp_adapters 的 MultiServerMCPClient 建立连接
- 暴露同步接口 call_tool(name, **kwargs) 供各节点调用

设计要点：
- MCP Server 是独立进程，这里用懒加载 + 单例缓存，避免每次检索都重启子进程
- 连接建立有开销（子进程启动 + 握手），所以用 asyncio.Lock 防止并发重复初始化
- 调用失败（Server 未起、网络、限流）一律返回空结果，交由上层降级
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection

from app.config import settings

# mcp/server.py 的绝对路径（相对 backend 目录定位）
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_SERVER_PATH = _BACKEND_DIR.parent / "mcp" / "server.py"


def _build_connection() -> StdioConnection:
    """构造指向 mcp/server.py 的 stdio 连接配置。

    子进程环境变量中注入 AMAP_API_KEY，供 MCP Server 读取。
    """
    env: dict[str, str] = dict(os.environ)
    # 从 settings（pydantic-settings 已读 .env）显式注入，覆盖/补充进程环境
    if settings.amap_api_key:
        env["AMAP_API_KEY"] = settings.amap_api_key

    return {
        "transport": "stdio",
        "command": "python",
        "args": [str(_SERVER_PATH)],
        "cwd": str(_BACKEND_DIR),
        "env": env,
    }


class MCPToolClient:
    """MCP 工具调用客户端（单例懒加载）。"""

    _instance: "MCPToolClient | None" = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self):
        self._client: MultiServerMCPClient | None = None
        self._tools: dict[str, Any] = {}
        self._ready = False

    @classmethod
    async def _get_instance(cls) -> "MCPToolClient":
        """获取单例（异步安全）。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _ensure_connected(self) -> None:
        """确保已连接到 MCP Server 并加载工具。"""
        if self._ready:
            return

        async with self._lock:
            if self._ready:  # 双重检查，避免并发重复初始化
                return
            try:
                self._client = MultiServerMCPClient(
                    connections={"travel-agent": _build_connection()}
                )
                tools = await self._client.get_tools()
                self._tools = {t.name: t for t in tools}
                self._ready = True
            except Exception:
                # 连接失败时保持未就绪状态，下次调用会重试
                self._client = None
                self._tools = {}
                self._ready = False

    async def call_tool(self, name: str, **kwargs: Any) -> list[dict[str, Any]]:
        """调用 MCP 工具，返回标准化的字典列表。

        失败时返回空列表（不抛异常），由上层决定是否降级。
        """
        await self._ensure_connected()
        if not self._ready or name not in self._tools:
            return []

        tool = self._tools[name]
        try:
            # BaseTool 异步调用：优先 ainvoke
            result = await tool.ainvoke(kwargs)
        except Exception:
            return []

        return _parse_tool_result(result)


def _parse_tool_result(result: Any) -> list[dict[str, Any]]:
    """把 MCP 工具返回结果解析为字典列表。

    兼容多层嵌套结构。langchain_mcp_adapters 的 ainvoke 返回值经过
    MCP 协议封装后可能是：
        [{'type': 'text', 'text': '{"content":[{"type":"text","text":"[...]"}]}'}]
    这里递归地剥掉所有 content/text 包装层，直到找到真正的 POI 列表。
    """
    return _unwrap(result, depth=0)


def _unwrap(node: Any, depth: int) -> list[dict[str, Any]]:
    """递归解析：从任意嵌套结构里提取 POI 字典列表。"""
    if depth > 8:  # 防御：避免异常结构导致无限递归
        return []

    # 1. 字符串 → 尝试按 JSON 解析
    if isinstance(node, str):
        text = node.strip()
        if not text:
            return []
        try:
            return _unwrap(json.loads(text), depth + 1)
        except json.JSONDecodeError:
            return []

    # 2. 列表 → 若元素是 dict 且像 POI（含 name），则直接返回；否则继续下钻
    if isinstance(node, list):
        if node and all(isinstance(x, dict) for x in node):
            # 判断是否为 POI 列表（含 name 字段），而非 content 包装
            if any("name" in x for x in node):
                return node
            # 否则是 content 包装列表，逐个下钻
            merged: list[dict[str, Any]] = []
            for item in node:
                merged.extend(_unwrap(item, depth + 1))
            return merged
        return []

    # 3. 字典 → 优先取 content / text 字段下钻
    if isinstance(node, dict):
        if "name" in node:
            return [node]  # 单个 POI
        for key in ("content", "text", "data", "result", "pois"):
            if key in node:
                parsed = _unwrap(node[key], depth + 1)
                if parsed:
                    return parsed
        # 既不是 POI，也不是已知包装层 → 把它本身当作业务数据对象返回
        # （如天气结果 {"city":..., "casts":[...]}）
        return [node]

    return []


async def acall_mcp_tool(name: str, **kwargs: Any) -> list[dict[str, Any]]:
    """模块级便捷入口：异步调用 MCP 工具。

    供需要直接 await 的场景使用。
    """
    client = await MCPToolClient._get_instance()
    return await client.call_tool(name, **kwargs)


def call_mcp_tool(name: str, **kwargs: Any) -> list[dict[str, Any]]:
    """模块级便捷入口：同步调用 MCP 工具。

    供同步节点使用。兼容两种调用上下文：
    - 无事件循环（普通脚本 / 同步 invoke）→ 直接 asyncio.run
    - 已有运行中的事件循环（FastAPI async 端点内）→ 在新线程里跑 asyncio.run，
      避免 "cannot be called from a running event loop" 报错
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 无运行中的事件循环
        return asyncio.run(acall_mcp_tool(name, **kwargs))

    # 已有运行中的事件循环：用独立线程跑，避免冲突
    result: list[dict[str, Any]] = []
    error: BaseException | None = None

    def _runner() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(acall_mcp_tool(name, **kwargs))
        except BaseException as e:  # noqa: BLE001
            error = e

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error is not None:
        raise error
    return result
