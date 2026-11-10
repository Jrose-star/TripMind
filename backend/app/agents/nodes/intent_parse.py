"""意图解析节点：用 LLM 把自然语言转换为结构化需求。"""

import json
import re

from app.agents.nodes.prompts import INTENT_PARSE_SYSTEM_PROMPT, build_intent_user_prompt
from app.agents.state import AgentState, TravelRequirement
from app.llm import get_llm

# 这些字段是"规划必须知道"的，缺失则加入 missing_fields 触发追问
REQUIRED_FIELDS = ["destination", "days", "budget"]


def _extract_json(text: str) -> dict:
    """从 LLM 输出中稳健地提取 JSON 对象。

    LLM 有时会在 JSON 外包代码块标记（```json ... ```）或额外文字，
    这里做兜底清洗。
    """
    text = text.strip()
    # 去掉 ```json 和 ``` 包裹
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 兜底：截取第一个 { 到最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def _build_requirement(data: dict) -> TravelRequirement:
    """把 LLM 返回的 dict 转成 TravelRequirement，并计算缺失字段。"""
    destination = data.get("destination")
    departure = data.get("departure")
    # 规则：只说了出发地、没说目的地时，默认"在出发地本地游玩"（如"武汉出发"→在武汉玩）
    if not destination and departure:
        destination = departure

    requirement = TravelRequirement(
        destination=destination,
        departure=departure,
        days=data.get("days"),
        budget=data.get("budget"),
        preferences=data.get("preferences") or [],
        travelers=data.get("travelers"),
    )
    # 计算缺失字段
    missing = []
    if not requirement.destination:
        missing.append("destination")
    if not requirement.days:
        missing.append("days")
    if not requirement.budget:
        missing.append("budget")
    requirement.missing_fields = missing
    return requirement


def intent_parse(state: AgentState) -> dict:
    """解析用户输入，返回结构化需求。

    若 LLM 不可用或解析失败，降级为空需求（所有字段缺失），
    交由 clarify 节点追问，保证链路不中断。
    """
    llm = get_llm()
    if llm is None:
        requirement = TravelRequirement(missing_fields=list(REQUIRED_FIELDS))
        return {"requirement": requirement}

    try:
        resp = llm.invoke(
            [
                ("system", INTENT_PARSE_SYSTEM_PROMPT),
                ("human", build_intent_user_prompt(state.user_input)),
            ]
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        data = _extract_json(content)
        requirement = _build_requirement(data)
        return {"requirement": requirement}
    except Exception:
        # 容错降级：任何异常都返回空需求，不中断链路
        requirement = TravelRequirement(missing_fields=list(REQUIRED_FIELDS))
        return {"requirement": requirement}
