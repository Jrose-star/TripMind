"""规划相关路由。

接口：
- POST /plan                     首次发起（同步），可能返回攻略或追问
- POST /plan/stream              首次发起（SSE 流式），可能推送攻略或追问
- POST /plan/{thread_id}/resume  用户回答追问后，恢复执行（同步）

多轮追问基于 LangGraph 的 interrupt + checkpointer：
1. clarify 节点信息不足时 interrupt 暂停，问题通过 __interrupt__ 抛回。
2. 用户回答后，用 Command(resume=答案) + 同一 thread_id 恢复。
"""

import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.agents import app_graph, planning_graph
from app.agents.nodes.guide_write import astream_guide
from app.agents.state import AgentState
from app.db import storage
from app.schemas import PlanRequest, PlanResponse, ResumeRequest

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


def _extract_final(result: dict) -> tuple[str, dict]:
    """从最终结果里提取攻略。

    astream 的 chunk 结构是 {节点名: 更新内容}，例如
    {"guide_write": {"guide_markdown": "...", "guide_json": {...}}}，
    所以需要先从嵌套里取出 guide_write 的更新，再取字段。
    同步 invoke 的最终结果则是平铺的完整状态，两种情况都要兼容。
    """
    guide_markdown = result.get("guide_markdown", "")
    guide_json = result.get("guide_json", {})
    if not guide_markdown:
        # 兼容 astream 的 chunk 嵌套结构
        node_update = result.get("guide_write") or {}
        if isinstance(node_update, dict):
            guide_markdown = node_update.get("guide_markdown", "")
            guide_json = node_update.get("guide_json", {})
    return guide_markdown, guide_json


def _extract_interrupt(result) -> str | None:
    """从结果里提取 interrupt 抛出的追问问题（若有）。"""
    interrupts = result.get("__interrupt__")
    if interrupts:
        first = interrupts[0]
        # interrupt 的 value 就是我们传入的问题字符串
        return first.value if hasattr(first, "value") else str(first)
    return None


async def _persist_result(thread_id: str, user_input: str, result: dict) -> None:
    """把一次完成的规划结果落库（数据库不可用时静默跳过）。"""
    guide_markdown, guide_json = _extract_final(result)
    req = result.get("requirement")
    destination = req.destination if req else None
    days = req.days if req else None
    budget = req.budget if req else None

    itinerary = [d.model_dump() for d in result.get("itinerary", [])]
    budget_result = result.get("budget")
    weather = result.get("weather")

    session_id = await storage.save_session(
        thread_id=thread_id,
        user_input=user_input,
        destination=destination,
        days=days,
        budget=budget,
        status="completed",
    )
    if session_id is not None:
        await storage.save_result(
            session_id=session_id,
            thread_id=thread_id,
            destination=destination,
            itinerary=itinerary,
            budget=budget_result.model_dump() if budget_result else None,
            weather=weather.model_dump() if weather else None,
            guide_markdown=guide_markdown,
            guide_json=guide_json,
        )


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    """首次发起规划（同步）。可能返回攻略，也可能返回追问。"""
    thread_id = req.thread_id or uuid.uuid4().hex
    initial_state = AgentState(user_input=req.user_input)

    result = app_graph.invoke(
        initial_state.model_dump(),
        config={"configurable": {"thread_id": thread_id}},
    )

    # 检查是否被 interrupt 暂停（信息不足）
    question = _extract_interrupt(result)
    if question:
        return PlanResponse(
            thread_id=thread_id,
            status="need_clarify",
            guide_markdown="",
            guide_json={"question": question},
        )

    guide_markdown, guide_json = _extract_final(result)
    await _persist_result(thread_id, req.user_input, result)
    return PlanResponse(
        thread_id=thread_id,
        status="completed",
        guide_markdown=guide_markdown,
        guide_json=guide_json,
    )


@router.post("/plan/{thread_id}/resume", response_model=PlanResponse)
async def resume_plan(thread_id: str, req: ResumeRequest):
    """用户回答追问后，恢复执行。"""
    result = app_graph.invoke(
        Command(resume=req.answer),
        config={"configurable": {"thread_id": thread_id}},
    )

    question = _extract_interrupt(result)
    if question:
        return PlanResponse(
            thread_id=thread_id,
            status="need_clarify",
            guide_markdown="",
            guide_json={"question": question},
        )

    guide_markdown, guide_json = _extract_final(result)
    # 恢复完成后，把用户原始输入也一并落库（从结果里取不到原始输入，用恢复上下文）
    await _persist_result(thread_id, thread_id, result)
    return PlanResponse(
        thread_id=thread_id,
        status="completed",
        guide_markdown=guide_markdown,
        guide_json=guide_json,
    )


@router.post("/plan/stream")
async def create_plan_stream(req: PlanRequest):
    """首次发起规划（SSE 流式）。

    前序节点（意图解析→检索→编排→校验）逐节点推送进度；
    攻略正文用 astream_guide 逐 token 流式推送（token 级流式）。
    """
    thread_id = req.thread_id or uuid.uuid4().hex
    initial_state = AgentState(user_input=req.user_input)

    async def event_generator():
        yield _sse({"type": "start", "thread_id": thread_id})

        try:
            # 第一段：跑规划图（到 budget_check），逐节点推送进度。
            # 注意：astream 的每个 chunk 是「单节点增量更新」，不是完整状态，
            # 所以需要手动累积各节点的更新，最后合并成完整 state。
            accumulated: dict = {}
            async for chunk in planning_graph.astream(
                initial_state.model_dump(),
                config={"configurable": {"thread_id": thread_id}},
            ):
                if "__interrupt__" in chunk:
                    question = _extract_interrupt(chunk)
                    yield _sse(
                        {"type": "clarify", "thread_id": thread_id, "question": question}
                    )
                    return
                for node_name, update in chunk.items():
                    status = NODE_STATUS_MAP.get(node_name, f"执行节点 {node_name}")
                    yield _sse({"type": "status", "node": node_name, "message": status})
                    if isinstance(update, dict):
                        accumulated.update(update)

            state = AgentState(**accumulated)

            # 第二段：流式生成攻略正文
            yield _sse({"type": "status", "node": "guide_write", "message": "正在撰写攻略…"})
            yield _sse({"type": "guide_start"})
            parts = []
            async for token in astream_guide(state):
                parts.append(token)
                yield _sse({"type": "guide_token", "token": token})

            full_markdown = "".join(parts)
            yield _sse(
                {
                    "type": "done",
                    "thread_id": thread_id,
                    "guide_markdown": full_markdown,
                    "guide_json": {},
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


@router.post("/plan/{thread_id}/resume/stream")
async def resume_plan_stream(thread_id: str, req: ResumeRequest):
    """用户回答追问后，恢复执行（SSE 流式）。"""
    async def event_generator():
        yield _sse({"type": "start", "thread_id": thread_id})

        try:
            accumulated: dict = {}
            async for chunk in planning_graph.astream(
                Command(resume=req.answer),
                config={"configurable": {"thread_id": thread_id}},
            ):
                if "__interrupt__" in chunk:
                    question = _extract_interrupt(chunk)
                    yield _sse(
                        {"type": "clarify", "thread_id": thread_id, "question": question}
                    )
                    return
                for node_name, update in chunk.items():
                    status = NODE_STATUS_MAP.get(node_name, f"执行节点 {node_name}")
                    yield _sse({"type": "status", "node": node_name, "message": status})
                    if isinstance(update, dict):
                        accumulated.update(update)

            state = AgentState(**accumulated)

            yield _sse({"type": "status", "node": "guide_write", "message": "正在撰写攻略…"})
            yield _sse({"type": "guide_start"})
            parts = []
            async for token in astream_guide(state):
                parts.append(token)
                yield _sse({"type": "guide_token", "token": token})

            full_markdown = "".join(parts)
            yield _sse(
                {
                    "type": "done",
                    "thread_id": thread_id,
                    "guide_markdown": full_markdown,
                    "guide_json": {},
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
