"""多轮追问节点：信息不足时向用户提问补全。

本阶段为占位实现。
"""

from app.agents.state import AgentState


def clarify(state: AgentState) -> dict:
    """当需求信息不足时，生成追问内容。

    TODO(核心阶段): 根据 missing_fields 生成自然语言追问，并通过 SSE 推给用户。
    """
    missing = []
    if state.requirement:
        missing = state.requirement.missing_fields
    question = "请问：" + "、".join(missing) + " 分别是什么？" if missing else ""
    messages = state.messages + [{"role": "assistant", "content": question}]
    return {"messages": messages}
