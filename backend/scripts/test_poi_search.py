"""4.3 POI 检索节点验证脚本。

用法：
    cd backend
    uv run python scripts/test_poi_search.py
"""

from app.agents.nodes.poi_search import poi_search
from app.agents.state import AgentState, TravelRequirement


def main():
    # 构造一个已解析好的需求（模拟意图解析的输出）
    requirement = TravelRequirement(
        destination="武汉",
        departure="武汉",
        days=3,
        budget=3000,
        preferences=["江景", "历史"],
    )
    state = AgentState(requirement=requirement)

    print("=" * 60)
    print("需求：武汉 3 天，预算 3000，偏好 江景+历史")
    print("-" * 60)

    result = poi_search(state)
    pois = result["pois"]

    if not pois:
        print("❌ 未检索到任何 POI")
        return

    print(f"✅ 共检索到 {len(pois)} 个 POI：\n")
    for p in pois:
        print(f"  • {p.name}")
        print(f"      类别: {p.category} | 位置: {p.location}")
        print(f"      预估费用: ¥{p.estimated_cost} | 预估时长: {p.estimated_duration}h")
    print("=" * 60)


if __name__ == "__main__":
    main()
