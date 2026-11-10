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
    """把 LLM 返回的 dict 转成 TravelRequirement（不含缺失字段计算）。"""
    destination = data.get("destination")
    departure = data.get("departure")
    # 规则：只说了出发地、没说目的地时，默认"在出发地本地游玩"（如"武汉出发"→在武汉玩）
    if not destination and departure:
        destination = departure

    return TravelRequirement(
        destination=destination,
        departure=departure,
        days=data.get("days"),
        budget=data.get("budget"),
        preferences=data.get("preferences") or [],
        travelers=data.get("travelers"),
    )


def intent_parse(state: AgentState) -> dict:
    """解析用户输入，返回结构化需求。

    - 首次：解析 state.user_input
    - 追问恢复：把 state.follow_up_answer 与已知需求合并后重新解析
    若 LLM 不可用或解析失败，降级为空需求（所有字段缺失），
    交由 clarify 节点追问，保证链路不中断。
    """
    llm = get_llm()
    if llm is None:
        requirement = _merge_existing(state.requirement, None)
        requirement.missing_fields = _calc_missing(requirement)
        return {"requirement": requirement}

    # 构造解析输入：追问恢复时，合并已有需求 + 补充答案
    text = state.user_input
    if state.follow_up_answer:
        existing = _format_existing(state.requirement)
        text = f"{state.user_input}\n已知信息：{existing}\n用户补充：{state.follow_up_answer}"

    try:
        resp = llm.invoke(
            [
                ("system", INTENT_PARSE_SYSTEM_PROMPT),
                ("human", build_intent_user_prompt(text)),
            ]
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        data = _extract_json(content)
        # 追问恢复时，把新解析结果与已有需求合并
        requirement = _merge_existing(state.requirement, data) if state.follow_up_answer else _build_requirement(data)
        requirement.missing_fields = _calc_missing(requirement)
        return {"requirement": requirement}
    except Exception:
        # 容错降级：任何异常都返回已有需求，不中断链路
        requirement = _merge_existing(state.requirement, None)
        requirement.missing_fields = _calc_missing(requirement)
        return {"requirement": requirement}


def _format_existing(requirement) -> str:
    """把已有需求格式化为文本，供 LLM 参考。"""
    if not requirement:
        return "无"
    parts = []
    if requirement.destination:
        parts.append(f"目的地={requirement.destination}")
    if requirement.departure:
        parts.append(f"出发地={requirement.departure}")
    if requirement.days:
        parts.append(f"天数={requirement.days}")
    if requirement.budget:
        parts.append(f"预算={requirement.budget}")
    if requirement.preferences:
        parts.append(f"偏好={','.join(requirement.preferences)}")
    return "；".join(parts) if parts else "无"


def _merge_existing(old, new_data) -> TravelRequirement:
    """把新解析结果合并到已有需求上（新值优先，空值回退到旧值）。"""
    if old is None:
        old = TravelRequirement()
    new = new_data or {}
    return TravelRequirement(
        destination=new.get("destination") or old.destination,
        departure=new.get("departure") or old.departure,
        days=new.get("days") or old.days,
        budget=new.get("budget") or old.budget,
        preferences=new.get("preferences") or old.preferences,
        travelers=new.get("travelers") or old.travelers,
    )


def _calc_missing(requirement: TravelRequirement) -> list[str]:
    """计算缺失字段。"""
    missing = []
    if not requirement.destination:
        missing.append("destination")
    if not requirement.days:
        missing.append("days")
    if not requirement.budget:
        missing.append("budget")
    return missing
