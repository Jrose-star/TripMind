"""攻略写作节点：将行程与预算输出为 Markdown / JSON。

本阶段为占位实现。
"""

from app.agents.state import AgentState


def guide_write(state: AgentState) -> dict:
    """生成攻略。

    TODO(核心阶段): 接入 LLM，生成自然语言图文攻略；本阶段输出占位内容。
    """
    markdown = "# 旅行攻略（占位）\n\n> 核心编排链路已跑通，攻略写作待接入 LLM。\n"
    guide_json = {"status": "placeholder", "itinerary": [d.model_dump() for d in state.itinerary]}
    return {"guide_markdown": markdown, "guide_json": guide_json}
