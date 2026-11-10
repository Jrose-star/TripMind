"""POI 检索节点：根据结构化需求获取候选兴趣点。

数据来源设计（可替换的数据源）：
- 主方案：高德地图（经 MCP 协议调用 mcp/server.py 的 search_poi 工具），返回真实 POI。
- 降级方案：LLM 生成候选 POI（真实存在、知名度高），MCP/高德不可用时兜底。
上层编排逻辑不关心数据从哪来，只消费标准化的 POI 列表。
"""

import json
import re

from app.agents.nodes.prompts import POI_SEARCH_SYSTEM_PROMPT, build_poi_user_prompt
from app.agents.state import AgentState, POI
from app.llm import get_llm
from app.tools.mcp_client import call_mcp_tool


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


def _search_poi_via_mcp(requirement) -> list[POI]:
    """通过 MCP 协议调用高德 POI 检索。

    后端作为 MCP 客户端，经 stdio 协议连 mcp/server.py，
    调用其 search_poi 工具，返回标准化的 POI 列表。
    """
    destination = requirement.destination or ""
    if not destination:
        return []

    # 偏好 → 高德检索关键字：景点为主，美食作为补充
    keywords = "景点"
    if requirement.preferences:
        # 把偏好映射成高德能理解的关键词，最多取前两个
        keywords = " ".join(requirement.preferences[:2])

    # call_mcp_tool 内部失败会返回空列表（不抛异常）
    raw_pois = call_mcp_tool("search_poi", city=destination, keywords=keywords)

    pois = []
    for i, raw in enumerate(raw_pois):
        pois.append(
            POI(
                id=str(raw.get("id") or f"amap-{i}"),
                name=raw.get("name", ""),
                category=raw.get("category", "景点"),
                location=raw.get("location", ""),
                estimated_cost=float(raw.get("estimated_cost", 0)),
                estimated_duration=float(raw.get("estimated_duration", 1.0)),
            )
        )
    return pois


def _search_poi_via_llm(requirement) -> list[POI]:
    """用 LLM 生成候选 POI（降级方案）。"""
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

    优先走 MCP 协议调高德真实数据源；MCP/高德未配置或失败时降级为 LLM 生成，
    保证主链路不中断。
    """
    requirement = state.requirement
    if requirement is None:
        return {"pois": []}

    # 优先真实数据源（经 MCP 协议）
    pois = _search_poi_via_mcp(requirement)
    if pois:
        return {"pois": pois}

    # 降级：LLM 生成
    return {"pois": _search_poi_via_llm(requirement)}
