"""行程编排节点（贪心算法）的单元测试。

覆盖：
- 按位置/分类排序
- 每日 8 小时上限换天
- 天数上限截断（不超出要求天数）
- POI 不足时补"自由活动"占位天
- 无 POI 时仍生成占位行程
"""

from app.agents.nodes.itinerary_plan import DAILY_HOURS, itinerary_plan
from app.agents.state import AgentState, DayPlan, POI, TravelRequirement


def _poi(name, hours=2.0, cost=0.0, location="A区", category="景点"):
    return POI(
        id=name,
        name=name,
        category=category,
        location=location,
        estimated_cost=cost,
        estimated_duration=hours,
    )


def _state(days, pois):
    return AgentState(requirement=TravelRequirement(destination="武汉", days=days), pois=pois)


class TestItineraryPlan:
    def test_single_day_fits(self):
        """POI 总时长不超 8 小时，应全塞进第一天。"""
        pois = [_poi("A"), _poi("B"), _poi("C")]  # 共 6 小时
        result = itinerary_plan(_state(1, pois))
        assert len(result["itinerary"]) == 1
        assert len(result["itinerary"][0].items) == 3

    def test_daily_hour_limit_rollover(self):
        """超过 8 小时应换到第二天。"""
        # 5 个 POI 各 2 小时 = 10 小时，应拆成 4 + 1
        pois = [_poi(f"P{i}") for i in range(5)]
        result = itinerary_plan(_state(3, pois))
        assert len(result["itinerary"]) >= 2
        assert result["itinerary"][0].items[-1].name == "P3"  # 第4个起换天
        assert len(result["itinerary"][1].items) == 1

    def test_day_cap_truncation(self):
        """天数上限：POI 很多但只要求 2 天，不应出现第 3 天。"""
        pois = [_poi(f"P{i}") for i in range(20)]  # 远超 2 天能容纳
        result = itinerary_plan(_state(2, pois))
        assert len(result["itinerary"]) == 2
        assert all(d.day <= 2 for d in result["itinerary"])

    def test_no_poi_fills_free_days(self):
        """无 POI 时，每天都是自由活动占位。"""
        result = itinerary_plan(_state(3, []))
        assert len(result["itinerary"]) == 3
        assert all(d.items == [] for d in result["itinerary"])
        assert all("自由活动" in d.note for d in result["itinerary"])

    def test_poi_insufficient_fills_remaining_days(self):
        """POI 只够一天，剩余天数补自由活动。"""
        result = itinerary_plan(_state(3, [_poi("A")]))
        assert len(result["itinerary"]) == 3
        assert len(result["itinerary"][0].items) == 1
        assert result["itinerary"][1].items == []
        assert result["itinerary"][2].items == []

    def test_sorting_by_location(self):
        """POI 按 location 排序，相近区域相邻。"""
        pois = [
            _poi("C", location="武昌区"),
            _poi("A", location="汉口区"),
            _poi("B", location="汉阳区"),
        ]
        result = itinerary_plan(_state(1, pois))
        items = result["itinerary"][0].items
        # 按 location 字符串排序，验证结果确实按 location 升序
        locations = [p.location for p in items]
        assert locations == sorted(locations)
        # 且三个 POI 都在同一天（总时长未超限）
        assert len(items) == 3

    def test_days_default_to_one(self):
        """未指定天数时默认 1 天。"""
        state = AgentState(requirement=TravelRequirement(destination="武汉"), pois=[_poi("A")])
        result = itinerary_plan(state)
        assert len(result["itinerary"]) == 1

    def test_exact_boundary_no_rollover(self):
        """恰好 8 小时不应换天（但 days=2 会补一个自由活动占位天）。"""
        pois = [_poi("A", hours=4.0), _poi("B", hours=4.0)]
        result = itinerary_plan(_state(2, pois))
        # 两个 POI 恰好 8 小时，都在第一天
        assert len(result["itinerary"][0].items) == 2
        # 第二天因天数要求补的自由活动占位天
        assert result["itinerary"][1].items == []

    def test_single_poi_over_daily_limit(self):
        """单个 POI 超过 8 小时（异常数据）也照常放入，不崩溃。"""
        result = itinerary_plan(_state(1, [_poi("超长景点", hours=10.0)]))
        assert len(result["itinerary"]) == 1
        assert len(result["itinerary"][0].items) == 1
