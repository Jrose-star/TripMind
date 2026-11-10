"""高德 POI 检索验证脚本。

验证 AmapClient 的配置检测与真实调用：
- 未配置 AMAP_API_KEY 时，is_configured 为 False，search_poi 返回空列表
- 已配置时，返回真实 POI 数据

用法：
    cd backend
    uv run python scripts/test_amap.py
"""

import asyncio

from app.tools.amap_client import AmapClient


async def main():
    client = AmapClient()
    print(f"AMAP_API_KEY 已配置: {client.is_configured}")

    if not client.is_configured:
        print("未配置高德 Key，跳过真实调用（这是正常的，未配置时主链路会降级到 LLM）。")
        print()
        print("要启用真实 POI 检索，请在 backend/.env 中设置 AMAP_API_KEY=你的高德Key")
        print("注册地址：https://lbs.amap.com → 控制台 → 应用管理 → 创建应用 → 添加 Key（选「Web服务」）")
        return

    print("开始调用高德 POI 搜索…")
    pois = await client.search_poi(city="武汉", keywords="江景 景点", limit=10)
    print(f"返回 {len(pois)} 个 POI：")
    for p in pois:
        print(f"  - {p['name']}（{p['category']}，{p['location']}）")


if __name__ == "__main__":
    asyncio.run(main())
