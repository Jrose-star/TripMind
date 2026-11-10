"""多轮追问闭环验证脚本。

流程：信息不足 → 系统追问 → 用户回答 → 系统恢复 → 出攻略。

用法：
    cd backend
    uv run python scripts/test_clarify.py
"""

import uuid

from app.agents import app_graph
from app.agents.state import AgentState
from langgraph.types import Command


def extract_interrupt(result) -> str | None:
    interrupts = result.get("__interrupt__")
    if interrupts:
        first = interrupts[0]
        return first.value if hasattr(first, "value") else str(first)
    return None


def main():
    thread_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}

    # 场景：信息严重不足
    user_input = "帮我规划一次旅行"

    print("=" * 60)
    print(f"用户输入：{user_input}\n")

    # 第一次调用：应该被 interrupt 暂停，返回追问
    state = AgentState(user_input=user_input)
    result1 = app_graph.invoke(state.model_dump(), config=config)
    question = extract_interrupt(result1)

    if question:
        print(f"✅ 系统追问：{question}\n")
    else:
        print("❌ 预期应触发追问，但直接出了结果")
        return

    # 用户回答
    answer = "去成都，玩3天，预算2000"
    print(f"用户回答：{answer}\n")

    # 第二次调用：恢复执行
    result2 = app_graph.invoke(Command(resume=answer), config=config)

    question2 = extract_interrupt(result2)
    if question2:
        print(f"系统再次追问：{question2}")
        return

    guide = result2.get("guide_markdown", "")
    print(f"✅ 恢复成功，生成攻略（{len(guide)} 字符）：\n")
    print(guide[:300])
    print("...")
    print("\n" + "=" * 60)
    print("多轮追问闭环验证通过！")


if __name__ == "__main__":
    main()
