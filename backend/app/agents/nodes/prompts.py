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
