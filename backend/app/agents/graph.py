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

MAX_RETRY = 3


def route_after_intent(state: AgentState) -> str:
    """意图解析后的路由：信息不足则追问，否则进入检索。"""
    if state.requirement and state.requirement.missing_fields:
        return "clarify"
    return "poi_search"


def route_after_budget(state: AgentState) -> str:
    """预算校验后的路由：超支且未超重排次数则回环重排，否则输出。"""
    if state.budget and state.budget.over_budget and state.retry_count < MAX_RETRY:
        return "itinerary_plan"
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
        {"itinerary_plan": "itinerary_plan", "guide_write": "guide_write"},
    )
    graph.add_edge("guide_write", END)

    # 用内存 checkpointer 支持中断/恢复（多轮追问）
    # 传入自定义 serde，让自定义 Pydantic 类型能被安全序列化，消除警告
    checkpointer = MemorySaver(serde=_CUSTOM_SERDE)
    return graph.compile(checkpointer=checkpointer)


# 供 API 层使用的编译实例
app_graph = build_graph()
