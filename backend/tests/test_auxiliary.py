"""追问与攻略兜底等辅助逻辑的单元测试。"""

from app.agents.nodes.clarify import _build_question
from app.agents.nodes.guide_write import _build_guide_json, _fallback_template
from app.agents.state import (
    AgentState,
    BudgetResult,
    DayPlan,
    POI,
    TravelRequirement,
    WeatherCast,
    WeatherInfo,
)


class TestBuildQuestion:
    def test_multiple_missing(self):
        q = _build_question(["destination", "days", "budget"])
        assert "想去哪个城市/目的地" in q
        assert "计划玩几天" in q
        assert "预算大概多少" in q

    def test_single_missing(self):
        q = _build_question(["days"])
        assert q == "还需要补充几个信息：计划玩几天？"

    def test_unknown_field_ignored(self):
        q = _build_question(["unknown_field"])
        assert q == "请补充一下你的旅行需求。"

    def test_empty_list(self):
        q = _build_question([])
        assert q == "请补充一下你的旅行需求。"


class TestBuildGuideJson:
    def test_full_state(self):
        req = TravelRequirement(destination="武汉", days=2, budget=3000)
        poi = POI(id="1", name="黄鹤楼", category="景点")
        day = DayPlan(day=1, items=[poi], note="第 1 天")
        budget = BudgetResult(total_estimated=2000, target_budget=3000)
        state = AgentState(requirement=req, itinerary=[day], budget=budget)

        guide = _build_guide_json(state)
        assert guide["destination"] == "武汉"
        assert guide["days"] == 2
        assert guide["budget"]["total_estimated"] == 2000
        assert len(guide["itinerary"]) == 1
        assert guide["itinerary"][0]["items"][0]["name"] == "黄鹤楼"

    def test_empty_state(self):
        state = AgentState()
        guide = _build_guide_json(state)
        assert guide["destination"] == ""
        assert guide["days"] is None
        assert guide["budget"] is None
        assert guide["weather"] is None
        assert guide["itinerary"] == []


class TestFallbackTemplate:
    def test_contains_basic_sections(self):
        req = TravelRequirement(destination="武汉", days=2, preferences=["江景"])
        day = DayPlan(day=1, items=[POI(id="1", name="黄鹤楼", category="景点", estimated_duration=2.0)])
        state = AgentState(requirement=req, itinerary=[day])

        md = _fallback_template(state)
        assert "# 武汉 旅行攻略" in md
        assert "## 行程概览" in md
        assert "## 分天安排" in md
        assert "黄鹤楼" in md
        assert "2.0 小时" in md

    def test_with_weather_and_budget(self):
        req = TravelRequirement(destination="武汉", days=1, budget=3000)
        day = DayPlan(day=1, items=[])
        weather = WeatherInfo(
            city="武汉",
            casts=[WeatherCast(date="2026-11-13", day_weather="晴", day_temp="20")],
        )
        budget = BudgetResult(total_estimated=1000, target_budget=3000, breakdown={"住宿": 0})
        state = AgentState(requirement=req, itinerary=[day], weather=weather, budget=budget)

        md = _fallback_template(state)
        assert "## 天气预报" in md
        assert "晴" in md
        assert "## 费用预估" in md
        assert "¥3000" in md

    def test_free_activity_when_no_items(self):
        req = TravelRequirement(destination="武汉", days=1)
        day = DayPlan(day=1, items=[])
        state = AgentState(requirement=req, itinerary=[day])

        md = _fallback_template(state)
        assert "自由活动 / 休息调整" in md
