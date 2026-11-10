"""MCP 空壳 Server：占位工具，供后续接真实高德/天气。

本阶段仅提供结构骨架，不接真实数据源。
"""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("travel-agent-mcp")


@app.list_tools()
async def list_tools():
    """列出可用工具（占位）。"""
    return [
        {
            "name": "search_poi",
            "description": "检索兴趣点（占位，待接高德地图）",
            "inputSchema": {
                "type": "object",
                "properties": {"keyword": {"type": "string"}},
                "required": ["keyword"],
            },
        },
        {
            "name": "get_weather",
            "description": "查询天气（占位，待接天气 API）",
            "inputSchema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """处理工具调用（占位实现）。"""
    if name == "search_poi":
        return {"content": [{"type": "text", "text": f"占位 POI 结果: {arguments.get('keyword', '')}"}]}
    if name == "get_weather":
        return {"content": [{"type": "text", "text": f"占位天气结果: {arguments.get('city', '')}"}]}
    raise ValueError(f"未知工具: {name}")


async def main():
    """以 stdio 方式启动 MCP Server。"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
