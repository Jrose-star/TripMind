"""4.5 攻略写作 + 全链路端到端验证脚本。

串联全部 5 个节点：意图解析 → POI 检索 → 行程编排 → 预算校验 → 攻略写作。

用法：
    cd backend
    uv run python scripts/test_full_pipeline.py
"""

from app.agents.nodes.budget_check import budget_check
from app.agents.nodes.guide_write import guide_write
from app.agents.nodes.intent_parse import intent_parse
from app.agents.nodes.itinerary_plan import itinerary_plan
from app.agents.nodes.poi_search import poi_search
from app.agents.state import AgentState


def main():
    user_input = "武汉出发，3天，预算3000，想看江景和历史景点"

    print("=" * 60)
    print(f"🎯 用户输入：{user_input}\n")

    state = AgentState(user_input=user_input)

    # 依次串联 5 个节点
    state = state.model_copy(update=intent_parse(state))
    state = state.model_copy(update=poi_search(state))
    state = state.model_copy(update=itinerary_plan(state))
    state = state.model_copy(update=budget_check(state))
    state = state.model_copy(update=guide_write(state))

    print("📝 生成的攻略：\n")
    print(state.guide_markdown)
    print("\n" + "=" * 60)
    print("✅ 全链路跑通！结构化数据也已生成（guide_json）。")


if __name__ == "__main__":
    main()
