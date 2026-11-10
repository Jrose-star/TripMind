"""规划相关路由。

当前实现：同步调用 LangGraph，返回完整攻略（Markdown + JSON）。
后续阶段：升级为 SSE 流式，边生成边推送。
"""

import uuid

from fastapi import APIRouter

from app.agents import app_graph
from app.agents.state import AgentState
from app.schemas import PlanRequest, PlanResponse

router = APIRouter()


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    """发起一次旅行规划，同步返回完整攻略。"""
    thread_id = req.thread_id or uuid.uuid4().hex

    # 初始状态
    initial_state = AgentState(user_input=req.user_input)

    # 调用 LangGraph，跑完 5 个节点，拿到最终状态
    result = app_graph.invoke(initial_state.model_dump())

    # 从最终状态中取回攻略
    final_state = AgentState(**result)

    return PlanResponse(
        thread_id=thread_id,
        status="completed",
        guide_markdown=final_state.guide_markdown,
        guide_json=final_state.guide_json,
    )
