"""行程编排节点：按天、按时段编排行程。

本阶段为占位实现。
"""

from app.agents.state import AgentState, DayPlan


def itinerary_plan(state: AgentState) -> dict:
    """根据 POI 和约束编排分天行程。

    TODO(核心阶段): 地理聚类 + 时间预算 + 偏好排序，生成分天分时段行程。
    """
    days = state.requirement.days if state.requirement else 1
    itinerary = [DayPlan(day=i + 1, items=state.pois, note="占位行程") for i in range(days or 1)]
    return {"itinerary": itinerary}
