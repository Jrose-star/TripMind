"""API 请求/响应模型。"""

from typing import Any

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """发起规划请求。"""

    user_input: str = Field(..., description="用户自然语言需求")
    thread_id: str | None = Field(default=None, description="会话线程 ID，用于多轮续跑")


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
