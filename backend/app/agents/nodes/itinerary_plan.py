"""行程编排节点：把候选 POI 贪心分配到每一天。

编排策略（贪心算法，可解释、易扩展）：
1. 按"位置"粗排序，让相近区域尽量相邻。
2. 按天循环，每天往里塞 POI，累计游玩时长超过每日上限（默认 8 小时）就换下一天。
3. 美食优先安排在午餐/晚餐时段附近（本阶段简化：穿插在景点之间）。
"""

from app.agents.state import AgentState, DayPlan

# 每天可用于游玩的时长上限（小时）
DAILY_HOURS = 8.0


def itinerary_plan(state: AgentState) -> dict:
    """根据 POI 和天数约束，生成分天行程。"""
    days = state.requirement.days if state.requirement and state.requirement.days else 1
    days = max(days, 1)
    pois = state.pois

    # 按位置排序，让相近区域相邻（简单地理聚类）
    sorted_pois = sorted(pois, key=lambda p: (p.location or "", p.category))

    itinerary: list[DayPlan] = []
    current_items = []
    current_hours = 0.0
    day_index = 1

    for poi in sorted_pois:
        # 天数约束：行程最多只编排到第 days 天，超出就不再塞入
        # （POI 检索通常返回远多于天数能容纳的数量，需按天数截断）
        if day_index > days:
            break
        # 如果当天塞不下（超过每日上限）且已有内容，换下一天
        if current_items and current_hours + poi.estimated_duration > DAILY_HOURS:
            itinerary.append(
                DayPlan(day=day_index, items=current_items, note=f"第 {day_index} 天")
            )
            day_index += 1
            current_items = []
            current_hours = 0.0
        # 换天后若已超过天数上限，停止塞入
        if day_index > days:
            break
        current_items.append(poi)
        current_hours += poi.estimated_duration

    # 收尾：最后一天
    if current_items and day_index <= days:
        itinerary.append(DayPlan(day=day_index, items=current_items, note=f"第 {day_index} 天"))

    # 若 POI 不足填满天数，补充"自由活动"占位天
    while len(itinerary) < days:
        itinerary.append(
            DayPlan(day=len(itinerary) + 1, items=[], note="自由活动 / 休息调整")
        )

    return {"itinerary": itinerary}
