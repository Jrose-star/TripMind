"""MCP 通路验证脚本。

验证后端节点通过 MCP 协议（stdio）调用 mcp/server.py 的 search_poi 工具，
能否拿到真实高德 POI 数据。

用法：
    cd backend
    uv run python scripts/test_mcp.py
"""

import asyncio

from app.tools.mcp_client import acall_mcp_tool


async def main():
    print("开始通过 MCP 协议调用 search_poi 工具…")
    print("（后端作为 MCP 客户端，经 stdio 协议连 mcp/server.py 子进程）")
    print()

    pois = await acall_mcp_tool("search_poi", city="武汉", keywords="江景 景点")

    if not pois:
        print("未获取到 POI。可能原因：未配置 AMAP_API_KEY，或 MCP Server 调用失败。")
        print("（未配置时主链路会降级到 LLM，这是正常行为。）")
        return

    print(f"通过 MCP 协议成功返回 {len(pois)} 个 POI：")
    for p in pois:
        cost = p.get("estimated_cost", 0)
        dur = p.get("estimated_duration", 1.0)
        print(
            f"  - {p.get('name')}（{p.get('category')}，"
            f"{p.get('location')}，约 ¥{cost}，{dur}h）"
        )


if __name__ == "__main__":
    asyncio.run(main())
