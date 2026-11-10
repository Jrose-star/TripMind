"""LangGraph 状态图定义：串联 5 个核心节点 + 条件路由。

含内存 checkpointer，支持 interrupt 中断/恢复（多轮追问）。
"""

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.agents.nodes.budget_check import budget_check
from app.agents.nodes.clarify import clarify
from app.agents.nodes.guide_write import guide_write
from app.agents.nodes.intent_parse import intent_parse
from app.agents.nodes.itinerary_plan import itinerary_plan
from app.agents.nodes.poi_search import poi_search
from app.agents.state import (
    AgentState,
    TravelRequirement,
    POI,
    DayPlan,
    BudgetResult,
)

# 自定义序列化白名单：让 checkpointer 能安全地序列化/反序列化我们的 Pydantic 类型，
# 消除 "Deserializing unregistered type" 警告。
_CUSTOM_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ("app.agents.state", "TravelRequirement"),
        ("app.agents.state", "POI"),
        ("app.agents.state", "DayPlan"),
        ("app.agents.state", "BudgetResult"),
    ]
)

# 最多追问次数，超过则强制用已有信息继续规划，避免 clarify↔intent_parse 死循环
MAX_CLARIFY_ROUNDS = 3


def route_after_intent(state: AgentState) -> str:
    """意图解析后的路由：信息不足则追问，否则进入检索。

    追问次数达到上限时不再追问，强制进入检索（后续节点对缺失字段有兜底），
    防止信息一直补不齐导致死循环。
    """
    if state.requirement and state.requirement.missing_fields:
        if state.retry_count >= MAX_CLARIFY_ROUNDS:
            return "poi_search"
        return "clarify"
    return "poi_search"


def route_after_budget(state: AgentState) -> str:
    """预算校验后的路由。

    说明：真正的"超支降费重排"是后续优化项（需要真正的降费策略，如删减 POI、
    更换更便宜替代）。本阶段贪心重排不会改变总费用，若在此回环会导致
    itinerary_plan ↔ budget_check 死循环。因此当前超支不重排，直接进攻略写作，
    把"超支"作为攻略里的提示展示。
    """
    return "guide_write"


def build_graph():
    """构建并编译旅行规划 Agent 状态图。"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("intent_parse", intent_parse)
    graph.add_node("clarify", clarify)
    graph.add_node("poi_search", poi_search)
    graph.add_node("itinerary_plan", itinerary_plan)
    graph.add_node("budget_check", budget_check)
    graph.add_node("guide_write", guide_write)

    # 入口
    graph.set_entry_point("intent_parse")

    # 边与条件路由
    graph.add_conditional_edges(
        "intent_parse",
        route_after_intent,
        {"clarify": "clarify", "poi_search": "poi_search"},
    )
    # 追问后回到意图解析，合并用户补充的信息重新解析
    graph.add_edge("clarify", "intent_parse")
    graph.add_edge("poi_search", "itinerary_plan")
    graph.add_edge("itinerary_plan", "budget_check")
    graph.add_conditional_edges(
        "budget_check",
        route_after_budget,
        {"guide_write": "guide_write"},
    )
    graph.add_edge("guide_write", END)

    # 用内存 checkpointer 支持中断/恢复（多轮追问）
    # 传入自定义 serde，让自定义 Pydantic 类型能被安全序列化，消除警告
    checkpointer = MemorySaver(serde=_CUSTOM_SERDE)
    return graph.compile(checkpointer=checkpointer)


def build_planning_graph():
    """构建"规划图"（不含攻略写作节点）。

    供 SSE 流式接口使用：先跑到 budget_check 产出结构化数据，
    再由 API 层用 astream_guide 流式生成攻略正文（token 级流式）。
    """
    graph = StateGraph(AgentState)

    graph.add_node("intent_parse", intent_parse)
    graph.add_node("clarify", clarify)
    graph.add_node("poi_search", poi_search)
    graph.add_node("itinerary_plan", itinerary_plan)
    graph.add_node("budget_check", budget_check)

    graph.set_entry_point("intent_parse")

    graph.add_conditional_edges(
        "intent_parse",
        route_after_intent,
        {"clarify": "clarify", "poi_search": "poi_search"},
    )
    graph.add_edge("clarify", "intent_parse")
    graph.add_edge("poi_search", "itinerary_plan")
    graph.add_edge("itinerary_plan", "budget_check")
    graph.add_edge("budget_check", END)

    checkpointer = MemorySaver(serde=_CUSTOM_SERDE)
    return graph.compile(checkpointer=checkpointer)


# 供 API 层使用的编译实例
app_graph = build_graph()
# 供流式接口使用的"规划图"（不含攻略写作，攻略由 API 层流式生成）
planning_graph = build_planning_graph()
