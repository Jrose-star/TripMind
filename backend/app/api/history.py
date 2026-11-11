"""历史会话相关路由。

接口：
- GET /history            历史会话列表
- GET /plan/{thread_id}   查询某次会话完整结果（含攻略）
"""

from fastapi import APIRouter, HTTPException

from app.db import storage
from app.schemas import HistoryListResponse, PlanResultResponse

router = APIRouter()


@router.get("/history", response_model=HistoryListResponse)
async def list_history():
    """历史会话列表（按时间倒序）。"""
    items = await storage.list_sessions(limit=50)
    return HistoryListResponse(items=items)


@router.get("/plan/{thread_id}", response_model=PlanResultResponse)
async def get_plan_result(thread_id: str):
    """查询某次会话的完整结果（含攻略正文）。"""
    result = await storage.get_result(thread_id)
    if result is None:
        raise HTTPException(status_code=404, detail="未找到该会话的规划结果")
    return PlanResultResponse(**result)
