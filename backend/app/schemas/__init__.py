"""API 请求/响应模型。"""

from typing import Any

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """发起规划请求。"""

    user_input: str = Field(..., description="用户自然语言需求")
    thread_id: str | None = Field(default=None, description="会话线程 ID，用于多轮续跑")


class ResumeRequest(BaseModel):
    """追问恢复请求。"""

    answer: str = Field(..., description="用户对追问的回答")


class PlanResponse(BaseModel):
    """规划发起响应（包含完整攻略）。"""

    thread_id: str
    status: str
    guide_markdown: str = ""
    guide_json: dict = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    version: str


class HistoryItem(BaseModel):
    """历史会话列表项。"""

    thread_id: str
    user_input: str
    destination: str | None = None
    days: int | None = None
    budget: float | None = None
    status: str = "completed"
    created_at: str = ""
    has_result: bool = False


class HistoryListResponse(BaseModel):
    """历史会话列表响应。"""

    items: list[HistoryItem] = Field(default_factory=list)


class PlanResultResponse(BaseModel):
    """某次会话完整结果响应。"""

    thread_id: str
    user_input: str = ""
    destination: str | None = None
    itinerary: list = Field(default_factory=list)
    budget: dict | None = None
    weather: dict | None = None
    guide_markdown: str = ""
    guide_json: dict | None = None
