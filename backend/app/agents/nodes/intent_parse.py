"""意图解析节点：从自然语言提取结构化需求。

本阶段为占位实现，仅返回空需求；实际解析逻辑在核心 Agent 阶段接入 LLM。
"""

from app.agents.state import AgentState, TravelRequirement


def intent_parse(state: AgentState) -> dict:
    """解析用户输入，返回结构化需求。

    TODO(核心阶段): 接入 LLM，从 state.user_input 提取
    目的地/出发地/天数/预算/偏好/人数，并填充 missing_fields。
    """
    requirement = TravelRequirement()
    # 占位：不做真实解析，标记所有字段缺失，后续由 clarify 节点追问
    requirement.missing_fields = ["destination", "days", "budget"]
    return {"requirement": requirement}
