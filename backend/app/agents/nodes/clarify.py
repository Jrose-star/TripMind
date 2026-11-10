"""多轮追问节点：信息不足时暂停，向用户提问补全。

使用 LangGraph 的 interrupt 机制：
1. clarify 节点检测到缺失字段，调用 interrupt() 暂停图执行，
   把"追问问题"抛给上层（API）。
2. 用户回答后，API 用 Command(resume=答案) 恢复执行，
   答案被注入到 state.follow_up_answer。
3. 恢复后路由到 intent_parse 重新解析（合并新信息）。
"""

from langgraph.types import interrupt

from app.agents.state import AgentState


def clarify(state: AgentState) -> dict:
    """信息不足时，生成自然语言追问并暂停。"""
    missing = []
    if state.requirement:
        missing = state.requirement.missing_fields

    # 把缺失字段翻译成自然语言问题
    question = _build_question(missing)

    # 暂停图执行，把问题抛给用户；用户回答会作为 resume 值返回
    answer = interrupt(question)

    # 恢复后，把用户回答存进状态，供重新解析使用
    return {"follow_up_answer": answer}


def _build_question(missing: list[str]) -> str:
    """把缺失字段翻译成友好的追问。"""
    field_labels = {
        "destination": "想去哪个城市/目的地",
        "days": "计划玩几天",
        "budget": "预算大概多少",
        "departure": "从哪里出发",
    }
    parts = [field_labels.get(f, f) for f in missing if f in field_labels]
    if not parts:
        return "请补充一下你的旅行需求。"
    return "还需要补充几个信息：" + "、".join(parts) + "？"
