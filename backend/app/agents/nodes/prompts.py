"""意图解析节点的提示词模板。"""

INTENT_PARSE_SYSTEM_PROMPT = """你是一个旅行需求解析助手。你的任务是从用户的自然语言中提取结构化的旅行需求信息。

请从用户输入中提取以下字段（能提取多少就提取多少，无法确定的填 null 或空）：
- destination: 目的地城市（如"武汉"）
- departure: 出发地城市（如"武汉"、"北京"）
- days: 行程天数（整数）
- budget: 预算金额（数字，单位元）
- preferences: 偏好列表（如 ["江景", "历史", "美食", "亲子", "自然", "购物", "夜游"]）
- travelers: 出行人数（整数）

要求：
1. 只输出一个合法的 JSON 对象，不要输出任何其他文字、解释或代码块标记。
2. 字段值无法确定时用 null（数字/字符串）或 []（列表）。
3. 数字字段必须是数字类型，不要带引号。

输出示例：
{"destination": "武汉", "departure": "武汉", "days": 3, "budget": 3000, "preferences": ["江景", "历史"], "travelers": null}
"""


def build_intent_user_prompt(user_input: str) -> str:
    """构造发给 LLM 的用户消息。"""
    return f"用户输入：{user_input}\n\n请提取结构化需求，只输出 JSON。"


POI_SEARCH_SYSTEM_PROMPT = """你是一个旅行 POI（兴趣点）推荐助手。根据用户的旅行需求，推荐真实存在、知名度高的景点和美食。

要求：
1. 只推荐真实存在的地点，不要编造。
2. 每个 POI 包含以下字段：
   - name: 名称
   - category: 类别（"景点"或"美食"）
   - location: 大致位置/区域（如"武昌区"）
   - estimated_cost: 预估人均费用（元，数字）
   - estimated_duration: 预估游玩时长（小时，数字，可带小数）
3. 数量：景点 3-5 个，美食 2-3 个，共 5-8 个。
4. 优先推荐符合用户偏好（preferences）的地点。
5. 只输出一个合法的 JSON 数组，不要输出任何其他文字或代码块标记。

输出示例：
[{"name": "黄鹤楼", "category": "景点", "location": "武昌区", "estimated_cost": 70, "estimated_duration": 2.0}, ...]
"""


def build_poi_user_prompt(requirement) -> str:
    """根据结构化需求构造 POI 检索提示。"""
    prefs = "、".join(requirement.preferences) if requirement.preferences else "无特别偏好"
    return (
        f"目的地：{requirement.destination}\n"
        f"出行天数：{requirement.days} 天\n"
        f"偏好：{prefs}\n\n"
        f"请推荐符合上述需求的热门景点和美食，只输出 JSON 数组。"
    )


GUIDE_WRITE_SYSTEM_PROMPT = """你是一位资深的旅行攻略作者。请根据给定的行程安排和预算信息，撰写一份专业、生动、实用的旅行攻略。

要求：
1. 使用 Markdown 格式输出。
2. 结构包含：标题、行程概览、分天详细安排、费用明细、实用贴士。
3. 语言自然、有温度，像真人游记，不要像冷冰冰的清单。
4. 每天的安排要具体，包含景点介绍（一句话点睛）、时间节奏、美食推荐。
5. 费用部分要清晰列出各项，并说明是"预估"。
6. 结尾给出 2-3 条实用的旅行贴士（交通、天气、避坑等）。
7. 若提供了天气预报，务必在贴士中给出对应的穿衣、携带雨具/防晒等建议。
"""


def build_guide_user_prompt(state) -> str:
    """把结构化行程 + 预算 + 天气转成给 LLM 的文本。"""
    req = state.requirement
    lines = []
    lines.append(f"目的地：{req.destination if req else ''}")
    lines.append(f"出行天数：{req.days if req else ''} 天")
    lines.append(f"出行偏好：{'、'.join(req.preferences) if req and req.preferences else '无'}")
    lines.append("")
    lines.append("行程安排：")
    for day in state.itinerary:
        items = "、".join(f"{p.name}({p.category})" for p in day.items) if day.items else "自由活动"
        lines.append(f"  第{day.day}天：{items}")
    lines.append("")
    if state.weather and state.weather.casts:
        lines.append("天气预报（未来几天）：")
        for c in state.weather.casts:
            lines.append(
                f"  {c.date}：白天{c.day_weather} {c.day_temp}°C，"
                f"夜间{c.night_weather} {c.night_temp}°C"
            )
        lines.append("")
    if state.budget:
        lines.append(f"目标预算：¥{state.budget.target_budget}")
        lines.append(f"预估总费用：¥{state.budget.total_estimated}")
        lines.append("费用明细：")
        for k, v in state.budget.breakdown.items():
            lines.append(f"  - {k}：¥{v}")
    lines.append("")
    lines.append("请据此撰写完整攻略（若提供了天气预报，请在贴士中给出相应的穿衣/携带建议）。")
    return "\n".join(lines)
