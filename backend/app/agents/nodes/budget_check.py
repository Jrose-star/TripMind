"""预算校验节点：汇总分项预算，判断是否超支。

本阶段为占位实现。
"""

from app.agents.state import AgentState, BudgetResult


def budget_check(state: AgentState) -> dict:
    """校验行程预算。

    TODO(核心阶段): 按 POI 估算分项费用，与目标预算比对，超支则触发重排。
    """
    total = sum(p.estimated_cost for day in state.itinerary for p in day.items)
    target = state.requirement.budget if state.requirement else 0
    budget = BudgetResult(
        total_estimated=total,
        target_budget=target or 0,
        over_budget=bool(target and total > target),
        gap=(target or 0) - total,
    )
    return {"budget": budget}
