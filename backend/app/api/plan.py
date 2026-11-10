"""规划相关路由。

包含两个接口：
- POST /plan       同步接口：一次性返回完整攻略
- POST /plan/stream 流式接口：SSE 逐节点推送进展 + 最终攻略
"""

import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents import app_graph
from app.agents.state import AgentState
from app.schemas import PlanRequest, PlanResponse

router = APIRouter()

# 节点名称 → 给用户看的友好提示
NODE_STATUS_MAP = {
    "intent_parse": "正在解析你的旅行需求…",
    "clarify": "需求信息不足，正在生成追问…",
    "poi_search": "正在检索符合条件的景点和美食…",
    "itinerary_plan": "正在编排行程…",
    "budget_check": "正在校验预算…",
    "guide_write": "正在撰写攻略…",
}


def _sse(data: dict) -> str:
    """把 dict 封装成 SSE 消息格式。"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    """发起一次旅行规划，同步返回完整攻略。"""
    thread_id = req.thread_id or uuid.uuid4().hex
    initial_state = AgentState(user_input=req.user_input)
    result = app_graph.invoke(initial_state.model_dump())
    final_state = AgentState(**result)

    return PlanResponse(
        thread_id=thread_id,
        status="completed",
        guide_markdown=final_state.guide_markdown,
        guide_json=final_state.guide_json,
    )


@router.post("/plan/stream")
async def create_plan_stream(req: PlanRequest):
    """发起旅行规划，通过 SSE 流式推送进展与最终攻略。"""
    thread_id = req.thread_id or uuid.uuid4().hex
    initial_state = AgentState(user_input=req.user_input)

    async def event_generator():
        # 第一条：开始
        yield _sse({"type": "start", "thread_id": thread_id})

        # 逐节点流式执行
        final_state = None
        try:
            async for chunk in app_graph.astream(initial_state.model_dump()):
                # chunk 形如 {"node_name": {更新字段...}}
                for node_name, _update in chunk.items():
                    status = NODE_STATUS_MAP.get(node_name, f"执行节点 {node_name}")
                    yield _sse({"type": "status", "node": node_name, "message": status})
                # 保存最后一次状态
                final_state = chunk

            # 从最后状态里取攻略
            guide_markdown = ""
            guide_json = {}
            if final_state and "guide_write" in final_state:
                guide_markdown = final_state["guide_write"].get("guide_markdown", "")
                guide_json = final_state["guide_write"].get("guide_json", {})

            yield _sse(
                {
                    "type": "done",
                    "thread_id": thread_id,
                    "guide_markdown": guide_markdown,
                    "guide_json": guide_json,
                }
            )
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
