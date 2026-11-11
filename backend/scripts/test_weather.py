"""天气接入验证脚本。

验证 weather 节点通过 MCP 协议调用高德天气，获取目的地真实天气预报。

用法：
    cd backend
    uv run python -m scripts.test_weather
"""

from app.agents.nodes.weather import weather_search
from app.agents.state import AgentState, TravelRequirement


def main():
    req = TravelRequirement(destination="武汉", days=3, preferences=["江景"])
    state = AgentState(user_input="武汉 3 天", requirement=req)

    print("通过 weather 节点（MCP 协议）检索武汉天气…")
    result = weather_search(state)
    weather = result.get("weather")

    if weather is None:
        print("未获取到天气（可能未配置 Key 或调用失败，主链路会跳过天气建议）。")
        return

    print(f"\n城市：{weather.city}（{weather.province}）")
    print(f"发布时间：{weather.report_time}")
    print("未来预报：")
    for c in weather.casts:
        print(
            f"  {c.date}：白天{c.day_weather} {c.day_temp}°C，"
            f"夜间{c.night_weather} {c.night_temp}°C"
        )


if __name__ == "__main__":
    main()
