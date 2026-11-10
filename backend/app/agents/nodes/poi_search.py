"""POI 检索节点：通过 MCP 检索候选兴趣点。

本阶段 MCP 为空壳，返回占位 POI。
"""

from app.agents.state import AgentState, POI


def poi_search(state: AgentState) -> dict:
    """检索候选 POI。

    TODO(后续阶段): 通过 MCP 客户端调用真实高德地图 / 天气服务。
    本阶段返回占位数据，保证编排链路能跑通。
    """
    pois = [
        POI(id="placeholder-1", name="示例景点（待接真实 MCP）", category="景点"),
        POI(id="placeholder-2", name="示例美食（待接真实 MCP）", category="美食"),
    ]
    return {"pois": pois}
