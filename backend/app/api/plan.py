"""规划相关路由。

本阶段为骨架版：提供 /plan 发起接口，内部调用编译好的 LangGraph。
SSE 流式接口在核心 Agent 阶段接入。
"""

import uuid

from fastapi import APIRouter

from app.agents import app_graph
from app.agents.state import AgentState
from app.schemas import PlanRequest, PlanResponse

router = APIRouter()


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    """发起一次旅行规划，返回线程 ID。"""
    thread_id = req.thread_id or uuid.uuid4().hex
    initial_state = AgentState(user_input=req.user_input)
    # 骨架版：同步调用一次，验证图可运行；后续改为异步 + SSE
    _ = app_graph.invoke(initial_state.model_dump())
    return PlanResponse(thread_id=thread_id, status="completed")
