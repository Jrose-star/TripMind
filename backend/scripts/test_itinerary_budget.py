"""4.4 行程编排 + 预算校验验证脚本（串联前 4 个节点）。

用法：
    cd backend
    uv run python scripts/test_itinerary_budget.py
"""

from app.agents.nodes.budget_check import budget_check
from app.agents.nodes.intent_parse import intent_parse
from app.agents.nodes.itinerary_plan import itinerary_plan
from app.agents.nodes.poi_search import poi_search
from app.agents.state import AgentState


def main():
    user_input = "武汉出发，3天，预算3000，想看江景和历史景点"

    # 串联：意图解析 → POI 检索 → 行程编排 → 预算校验
    state = AgentState(user_input=user_input)

    print("=" * 60)
    print(f"用户输入：{user_input}\n")

    # 1. 意图解析
    state = state.model_copy(update=intent_parse(state))
    req = state.requirement
    print(f"【意图解析】目的地={req.destination}, 天数={req.days}, 预算={req.budget}, 偏好={req.preferences}\n")

    # 2. POI 检索
    state = state.model_copy(update=poi_search(state))
    print(f"【POI 检索】共 {len(state.pois)} 个 POI\n")

    # 3. 行程编排
    state = state.model_copy(update=itinerary_plan(state))
    print("【行程编排】")
    for day in state.itinerary:
        names = " → ".join(p.name for p in day.items) if day.items else "（自由活动）"
        hours = sum(p.estimated_duration for p in day.items)
        print(f"  第{day.day}天（{hours:.1f}h）: {names}")
    print()

    # 4. 预算校验
    state = state.model_copy(update=budget_check(state))
    b = state.budget
    print("【预算校验】")
    print(f"  目标预算：¥{b.target_budget}")
    print(f"  预估总费用：¥{b.total_estimated}")
    for k, v in b.breakdown.items():
        print(f"    - {k}: ¥{v}")
    if b.over_budget:
        print(f"  ⚠️ 超支 ¥{abs(b.gap)}")
    else:
        print(f"  ✅ 结余 ¥{b.gap}")
    print("=" * 60)


if __name__ == "__main__":
    main()
