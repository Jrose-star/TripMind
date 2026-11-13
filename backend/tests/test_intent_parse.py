"""意图解析节点的单元测试。

覆盖纯函数逻辑（不依赖 LLM）：
- _extract_json：各种 LLM 输出格式的稳健解析
- _build_requirement：dict → TravelRequirement，含"出发地兜底目的地"规则
- _merge_existing：追问合并逻辑（新值优先，空值回退）
- _calc_missing：缺失字段计算
- _format_existing：已有需求文本化
"""

from app.agents.nodes.intent_parse import (
    _build_requirement,
    _calc_missing,
    _extract_json,
    _format_existing,
    _merge_existing,
)
from app.agents.state import TravelRequirement


class TestExtractJson:
    def test_plain_json(self):
        assert _extract_json('{"destination": "武汉"}') == {"destination": "武汉"}

    def test_json_with_code_block(self):
        text = '```json\n{"destination": "武汉", "days": 3}\n```'
        assert _extract_json(text) == {"destination": "武汉", "days": 3}

    def test_json_with_surrounding_text(self):
        text = '好的，以下是结果：{"destination": "成都"} 希望能帮到你'
        assert _extract_json(text) == {"destination": "成都"}

    def test_invalid_returns_empty_dict(self):
        assert _extract_json("这不是 JSON") == {}

    def test_empty_string(self):
        assert _extract_json("") == {}


class TestBuildRequirement:
    def test_full_fields(self):
        data = {
            "destination": "武汉",
            "departure": "北京",
            "days": 3,
            "budget": 3000,
            "preferences": ["江景", "历史"],
            "travelers": 2,
        }
        req = _build_requirement(data)
        assert req.destination == "武汉"
        assert req.departure == "北京"
        assert req.days == 3
        assert req.budget == 3000
        assert req.preferences == ["江景", "历史"]
        assert req.travelers == 2

    def test_departure_as_destination_fallback(self):
        """只给出发地时，默认目的地 = 出发地（本地游玩）。"""
        req = _build_requirement({"departure": "武汉"})
        assert req.destination == "武汉"
        assert req.departure == "武汉"

    def test_missing_fields_default(self):
        req = _build_requirement({})
        assert req.destination is None
        assert req.days is None
        assert req.budget is None
        assert req.preferences == []

    def test_preferences_none_becomes_empty_list(self):
        req = _build_requirement({"destination": "武汉", "preferences": None})
        assert req.preferences == []


class TestMergeExisting:
    def test_new_value_priority(self):
        old = TravelRequirement(destination="武汉", days=3, budget=3000)
        new = {"destination": "成都"}
        merged = _merge_existing(old, new)
        assert merged.destination == "成都"  # 新值优先
        assert merged.days == 3  # 未提供则回退旧值
        assert merged.budget == 3000

    def test_old_none(self):
        merged = _merge_existing(None, {"destination": "成都", "days": 2})
        assert merged.destination == "成都"
        assert merged.days == 2

    def test_new_data_none(self):
        old = TravelRequirement(destination="武汉", days=3)
        merged = _merge_existing(old, None)
        assert merged.destination == "武汉"
        assert merged.days == 3

    def test_empty_value_falls_back_to_old(self):
        """新值为空字符串/None 时，应回退到旧值而非覆盖为空。"""
        old = TravelRequirement(destination="武汉", days=3, budget=3000)
        merged = _merge_existing(old, {"destination": "", "budget": None})
        assert merged.destination == "武汉"
        assert merged.budget == 3000


class TestCalcMissing:
    def test_all_missing(self):
        req = TravelRequirement()
        assert set(_calc_missing(req)) == {"destination", "days", "budget"}

    def test_none_missing(self):
        req = TravelRequirement(destination="武汉", days=3, budget=3000)
        assert _calc_missing(req) == []

    def test_partial_missing(self):
        req = TravelRequirement(destination="武汉")  # 缺 days 和 budget
        assert set(_calc_missing(req)) == {"days", "budget"}

    def test_zero_budget_counts_as_missing(self):
        """budget=0 应视为缺失（falsy）。"""
        req = TravelRequirement(destination="武汉", days=3, budget=0)
        assert "budget" in _calc_missing(req)


class TestFormatExisting:
    def test_empty_requirement(self):
        assert _format_existing(None) == "无"
        assert _format_existing(TravelRequirement()) == "无"

    def test_full_requirement(self):
        req = TravelRequirement(destination="武汉", departure="北京", days=3, budget=3000, preferences=["江景"])
        text = _format_existing(req)
        assert "目的地=武汉" in text
        assert "天数=3" in text
        assert "预算=3000" in text
        assert "偏好=江景" in text
