"""预算校验节点：汇总行程费用并与目标预算比对。

费用构成：
1. POI 费用：所有景点门票 + 美食消费（来自 POI 的 estimated_cost）。
2. 每日基础开销：住宿 + 餐饮 + 市内交通的粗略估算（按天计）。

超支判断：总费用 > 目标预算。
"""

from app.agents.state import AgentState, BudgetResult

# 每日基础开销估算（元/人/天）：住宿 + 餐饮 + 交通
DAILY_BASE_COST = 300.0
# 住宿费用估算（元/晚）
DAILY_HOTEL_COST = 200.0


def budget_check(state: AgentState) -> dict:
    """校验行程预算，返回分项明细与超支判断。"""
    days = len(state.itinerary)
    target = state.requirement.budget if state.requirement else 0

    # 1. POI 费用
    poi_total = sum(p.estimated_cost for day in state.itinerary for p in day.items)

    # 2. 基础开销（按天）
    hotel_total = DAILY_HOTEL_COST * max(days - 1, 0)  # 住宿按"晚"算，天数-1
    base_total = DAILY_BASE_COST * days

    total = poi_total + hotel_total + base_total

    breakdown = {
        "景点与美食": round(poi_total, 2),
        "住宿": round(hotel_total, 2),
        "餐饮交通等基础开销": round(base_total, 2),
    }

    budget = BudgetResult(
        total_estimated=round(total, 2),
        target_budget=target or 0,
        over_budget=bool(target and total > target),
        gap=round((target or 0) - total, 2),
        breakdown=breakdown,
    )
    return {"budget": budget}
