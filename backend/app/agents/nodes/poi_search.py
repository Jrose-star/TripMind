"""POI 检索节点：根据结构化需求获取候选兴趣点。

数据来源设计：
- 当前实现：用 LLM 生成候选 POI（真实存在、知名度高），快速跑通主链路。
- 预留接口：`_search_poi_via_mcp()` 为未来接入真实高德地图 MCP 预留位置，
  届时只需替换数据来源，上层编排逻辑无需改动。
"""

import json
import re

from app.agents.nodes.prompts import POI_SEARCH_SYSTEM_PROMPT, build_poi_user_prompt
from app.agents.state import AgentState, POI
from app.llm import get_llm


def _extract_json_list(text: str) -> list:
    """从 LLM 输出中稳健提取 JSON 数组。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # 兜底：截取第一个 [ 到最后一个 ] 之间
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def _search_poi_via_mcp(requirement) -> list[dict]:
    """通过 MCP 调用真实地图服务检索 POI（预留，未来阶段接入）。

    TODO(后续阶段): 通过 MCP 客户端调用高德地图 POI 搜索接口，
    替换下方 LLM 生成方案。
    """
    raise NotImplementedError("真实 MCP 检索尚未接入")


def _search_poi_via_llm(requirement) -> list[POI]:
    """用 LLM 生成候选 POI（当前方案）。"""
    llm = get_llm()
    if llm is None:
        return []
    resp = llm.invoke(
        [
            ("system", POI_SEARCH_SYSTEM_PROMPT),
            ("human", build_poi_user_prompt(requirement)),
        ]
    )
    content = resp.content if hasattr(resp, "content") else str(resp)
    items = _extract_json_list(content)
    pois = []
    for i, item in enumerate(items):
        try:
            pois.append(
                POI(
                    id=f"poi-{i}",
                    name=item.get("name", ""),
                    category=item.get("category", "景点"),
                    location=item.get("location", ""),
                    estimated_cost=float(item.get("estimated_cost", 0)),
                    estimated_duration=float(item.get("estimated_duration", 1.0)),
                )
            )
        except (TypeError, ValueError):
            continue
    return pois


def poi_search(state: AgentState) -> dict:
    """检索候选 POI。

    当前走 LLM 生成；未来切换为 MCP 真实检索时，仅需改 `_search_poi_via_llm`
    为 `_search_poi_via_mcp`。
    """
    requirement = state.requirement
    if requirement is None:
        return {"pois": []}
    pois = _search_poi_via_llm(requirement)
    return {"pois": pois}
