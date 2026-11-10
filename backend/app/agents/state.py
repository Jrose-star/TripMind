"""LangGraph 状态 Schema：定义贯穿整个编排流程的共享状态。"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class TravelRequirement(BaseModel):
    """意图解析后的结构化需求。"""

    destination: Optional[str] = Field(default=None, description="目的地")
    departure: Optional[str] = Field(default=None, description="出发地")
    days: Optional[int] = Field(default=None, description="天数")
    budget: Optional[float] = Field(default=None, description="预算（元）")
    preferences: list[str] = Field(default_factory=list, description="偏好，如江景/历史/美食")
    travelers: Optional[int] = Field(default=None, description="出行人数")
    missing_fields: list[str] = Field(default_factory=list, description="缺失待追问的字段")


class POI(BaseModel):
    """兴趣点（Point of Interest）。"""

    id: str
    name: str
    category: str = ""
    location: str = ""
    estimated_cost: float = 0.0
    estimated_duration: float = 1.0  # 小时


class DayPlan(BaseModel):
    """某一天的行程安排。"""

    day: int
    items: list[POI] = Field(default_factory=list)
    note: str = ""


class BudgetResult(BaseModel):
    """预算校验结果。"""

    total_estimated: float = 0.0
    target_budget: float = 0.0
    over_budget: bool = False
    gap: float = 0.0
    breakdown: dict[str, float] = Field(default_factory=dict)


class AgentState(BaseModel):
    """LangGraph 共享状态（可序列化，支持 checkpointer 持久化）。"""

    user_input: str = ""
    requirement: Optional[TravelRequirement] = None
    pois: list[POI] = Field(default_factory=list)
    itinerary: list[DayPlan] = Field(default_factory=list)
    budget: Optional[BudgetResult] = None
    guide_markdown: str = ""
    guide_json: dict[str, Any] = Field(default_factory=dict)
    # 控制字段
    retry_count: int = 0
    error: Optional[str] = None
    # 元信息
    messages: list[dict[str, Any]] = Field(default_factory=list)
