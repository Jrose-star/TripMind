"""天气检索节点：通过 MCP 协议调用高德天气，获取目的地未来数天预报。

数据来源：
- 主方案：高德天气 API（经 MCP 协议，复用高德 Key）
- 降级方案：无天气数据时，攻略写作会跳过天气建议（不中断主链路）

本节点不强制要求天气成功，因为天气是"锦上添花"的增强信息，
POI/行程才是主链路。天气失败时置 None，攻略写作自动忽略。
"""

from app.agents.state import AgentState, WeatherInfo, WeatherCast
from app.tools.mcp_client import call_mcp_tool


def _parse_weather(raw: dict) -> WeatherInfo | None:
    """把 MCP 工具返回的天气 dict 转成 WeatherInfo。"""
    if not raw or not raw.get("city"):
        return None

    casts = []
    for c in raw.get("casts", []):
        casts.append(
            WeatherCast(
                date=str(c.get("date", "")),
                week=str(c.get("week", "")),
                day_weather=str(c.get("day_weather", "")),
                night_weather=str(c.get("night_weather", "")),
                day_temp=str(c.get("day_temp", "")),
                night_temp=str(c.get("night_temp", "")),
                day_wind=str(c.get("day_wind", "")),
                night_wind=str(c.get("night_wind", "")),
                day_power=str(c.get("day_power", "")),
                night_power=str(c.get("night_power", "")),
            )
        )

    return WeatherInfo(
        city=raw.get("city", ""),
        province=raw.get("province", ""),
        report_time=raw.get("report_time", ""),
        casts=casts,
    )


def weather_search(state: AgentState) -> dict:
    """检索目的地天气（经 MCP 协议调高德）。

    天气是增强信息，失败时返回 weather=None，不中断主链路。
    """
    requirement = state.requirement
    if requirement is None:
        return {"weather": None}

    destination = requirement.destination or ""
    if not destination:
        return {"weather": None}

    # call_mcp_tool 失败时返回空列表（不抛异常）
    results = call_mcp_tool("get_weather", city=destination)

    if not results:
        return {"weather": None}

    weather = _parse_weather(results[0])
    return {"weather": weather}
