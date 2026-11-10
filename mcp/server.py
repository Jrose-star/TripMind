"""MCP Server：把高德地图 / 天气等外部服务封装为 MCP 工具。

本文件是一个标准的 MCP Server（stdio 传输），对外暴露统一工具接口。
后端 POI 检索节点目前走进程内 AmapClient（等价实现），
本 Server 用于未来真正的 MCP 协议接入 / 独立部署。

工具：
- search_poi：高德 POI 检索
- get_weather：天气查询（占位）
"""

import asyncio
import json
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

app = Server("travel-agent-mcp")


def _get_api_key() -> str:
    """获取高德 Key：优先环境变量，其次从 backend/.env 读取。

    MCP Server 作为独立子进程运行时，父进程内存里的 settings 不可见，
    因此这里主动从 .env 文件兜底读取。
    """
    key = os.environ.get("AMAP_API_KEY", "")
    if key:
        return key

    # 兜底：从 backend/.env 读取（相对本文件定位 backend 目录）
    env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("AMAP_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    except OSError:
        pass
    return key


def _looks_scenic(raw_type: str) -> bool:
    """根据高德 POI 类型编码判断是否为风景/景点类。

    兼容两种编码来源：
    - typecode：数字编码，如 "110200|170200|071100"
    - type：中文文本，如 "风景名胜;公园广场;公园"
    """
    scenic_codes = {
        "110100",  # 风景名胜
        "110200",  # 公园广场
        "110000",  # 风景名胜大类
        "140000",  # 科教文化服务
        "140300",  # 博物馆
        "140400",  # 展览馆
        "140500",  # 会展中心
        "140600",  # 美术馆
        "140700",  # 图书馆
        "140800",  # 科技馆
        "141000",  # 文化宫
    }
    scenic_words = ("风景", "公园", "博物馆", "展览馆", "美术馆", "图书馆", "科技馆", "文化宫", "会展")

    for code in raw_type.replace("|", ";").split(";"):
        code = code.strip()
        if not code:
            continue
        if code in scenic_codes or code.startswith("110") or code.startswith("140"):
            return True
        if any(w in code for w in scenic_words):
            return True
    return False


def _estimate_cost(raw_type: str) -> float:
    """按 POI 类型粗略估算人均费用（元）。"""
    return 60.0 if _looks_scenic(raw_type) else 50.0


def _estimate_duration(raw_type: str) -> float:
    """按 POI 类型粗略估算游玩时长（小时）。"""
    return 2.0 if _looks_scenic(raw_type) else 1.0


async def _search_amap(city: str, keywords: str) -> str:
    """调用高德 POI 搜索，返回标准化的 JSON 文本。"""
    api_key = _get_api_key()
    if not api_key:
        return "[]"

    import httpx

    params = {
        "key": api_key,
        "city": city,
        "keywords": keywords,
        "offset": 10,
        "page": 1,
        "extensions": "base",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://restapi.amap.com/v3/place/text", params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "1":
        return "[]"

    pois = []
    for i, p in enumerate(data.get("pois", [])):
        raw_type = p.get("typecode", "") or p.get("type", "")
        category = "景点" if _looks_scenic(raw_type) else "美食"
        location = " ".join(
            x for x in [p.get("adname", ""), p.get("address", "")] if x
        )
        pois.append(
            {
                "id": p.get("id", f"amap-{i}"),
                "name": p.get("name", ""),
                "category": category,
                "location": location,
                "estimated_cost": _estimate_cost(raw_type),
                "estimated_duration": _estimate_duration(raw_type),
                "address": p.get("address", ""),
            }
        )
    return json.dumps(pois, ensure_ascii=False)


@app.list_tools()
async def list_tools():
    """列出可用工具。"""
    return [
        Tool(
            name="search_poi",
            description="通过高德地图检索兴趣点（景点、美食等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如「武汉」"},
                    "keywords": {"type": "string", "description": "检索关键字，如「江景」「景点」"},
                },
                "required": ["city", "keywords"],
            },
        ),
        Tool(
            name="get_weather",
            description="查询天气（占位，待接天气 API）",
            inputSchema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """处理工具调用。"""
    if name == "search_poi":
        city = arguments.get("city", "")
        keywords = arguments.get("keywords", "")
        text = await _search_amap(city, keywords)
        return {"content": [{"type": "text", "text": text}]}
    if name == "get_weather":
        return {"content": [{"type": "text", "text": f"占位天气结果: {arguments.get('city', '')}"}]}
    raise ValueError(f"未知工具: {name}")


async def main():
    """以 stdio 方式启动 MCP Server。"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
    asyncio.run(main())
