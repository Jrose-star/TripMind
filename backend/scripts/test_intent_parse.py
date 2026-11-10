"""4.2 意图解析节点验证脚本。

用法：
    cd backend
    uv run python scripts/test_intent_parse.py
"""

from app.agents.nodes.intent_parse import intent_parse
from app.agents.state import AgentState

TEST_CASES = [
    "武汉出发，3天，预算3000，想看江景和历史景点",
    "带6岁孩子去广州玩2天，要亲子友好",
    "上海1天特种兵，预算500，吃小吃",
    "帮我规划一次旅行",  # 信息严重不足，应触发追问
]


def main():
    print("=" * 60)
    for i, text in enumerate(TEST_CASES, 1):
        state = AgentState(user_input=text)
        result = intent_parse(state)
        req = result["requirement"]
        print(f"\n【用例 {i}】{text}")
        print(f"  目的地: {req.destination}")
        print(f"  出发地: {req.departure}")
        print(f"  天数: {req.days}")
        print(f"  预算: {req.budget}")
        print(f"  偏好: {req.preferences}")
        print(f"  人数: {req.travelers}")
        print(f"  缺失字段: {req.missing_fields}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
