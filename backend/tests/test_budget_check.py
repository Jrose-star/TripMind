"""预算校验节点的单元测试。"""

from app.agents.nodes.budget_check import (
    DAILY_BASE_COST,
    DAILY_HOTEL_COST,
    budget_check,
)
from app.agents.state import AgentState, DayPlan, POI, TravelRequirement


def _poi(name, cost=50.0):
    return POI(id=name, name=name, estimated_cost=cost)


def _make_state(days_plan, budget):
    req = TravelRequirement(destination="武汉", days=len(days_plan) or 1, budget=budget)
    return AgentState(requirement=req, itinerary=days_plan)


class TestBudgetCheck:
    def test_empty_itinerary(self):
        """空行程：无 POI 费用，无住宿，仅基础开销。"""
        state = _make_state([], 1000)
        result = budget_check(state)["budget"]
        assert result.total_estimated == 0  # days=0，全部为 0

    def test_poi_cost_sum(self):
        """POI 费用正确累加。"""
        day = DayPlan(day=1, items=[_poi("A", 100), _poi("B", 50)])
        state = _make_state([day], 10000)
        result = budget_check(state)["budget"]
        assert result.breakdown["景点与美食"] == 150.0

    def test_hotel_cost_is_nights_not_days(self):
        """住宿按"晚"算：3 天 = 2 晚。"""
        days = [DayPlan(day=i) for i in range(1, 4)]  # 3 天
        state = _make_state(days, 100000)
        result = budget_check(state)["budget"]
        assert result.breakdown["住宿"] == DAILY_HOTEL_COST * 2

    def test_base_cost_per_day(self):
        """基础开销 = 每日基数 × 天数。"""
        days = [DayPlan(day=i) for i in range(1, 3)]  # 2 天
        state = _make_state(days, 100000)
        result = budget_check(state)["budget"]
        assert result.breakdown["餐饮交通等基础开销"] == DAILY_BASE_COST * 2

    def test_over_budget_detection(self):
        """超支判断。"""
        day = DayPlan(day=1, items=[_poi("A", 5000)])
        state = _make_state([day], 1000)
        result = budget_check(state)["budget"]
        assert result.over_budget is True
        assert result.gap < 0  # gap 为负，表示超支

    def test_within_budget(self):
        """预算充足时不超支。"""
        day = DayPlan(day=1, items=[_poi("A", 100)])
        state = _make_state([day], 100000)
        result = budget_check(state)["budget"]
        assert result.over_budget is False
        assert result.gap > 0

    def test_no_budget_target(self):
        """未设预算时，over_budget 恒为 False。"""
        day = DayPlan(day=1, items=[_poi("A", 100)])
        state = _make_state([day], None)
        result = budget_check(state)["budget"]
        assert result.over_budget is False
        assert result.target_budget == 0

    def test_total_equals_sum_of_breakdown(self):
        """总额 = 各分项之和。"""
        day = DayPlan(day=1, items=[_poi("A", 123.45)])
        state = _make_state([day], 100000)
        result = budget_check(state)["budget"]
        breakdown_sum = sum(result.breakdown.values())
        assert abs(result.total_estimated - breakdown_sum) < 0.01
