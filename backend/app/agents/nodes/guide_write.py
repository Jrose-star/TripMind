"""攻略写作节点：把结构化行程 + 预算输出为 Markdown / JSON 双形态攻略。"""

from typing import AsyncIterator

from app.agents.nodes.prompts import GUIDE_WRITE_SYSTEM_PROMPT, build_guide_user_prompt
from app.agents.state import AgentState
from app.llm import get_llm


async def astream_guide(state: AgentState) -> AsyncIterator[str]:
    """流式生成攻略正文（token 级）。

    供 API 层在跑完前序节点后调用，逐 token 产出 Markdown 攻略，
    用于 SSE 流式推送给前端。
    """
    llm = get_llm()
    if llm is None:
        # 降级：LLM 不可用时，一次性产出模板攻略
        yield _fallback_template(state)
        return

    try:
        async for chunk in llm.astream(
            [
                ("system", GUIDE_WRITE_SYSTEM_PROMPT),
                ("human", build_guide_user_prompt(state)),
            ]
        ):
            text = chunk.content if hasattr(chunk, "content") else str(chunk)
            if text:
                yield text
    except Exception:
        # 容错降级：流式失败时，产出模板攻略
        yield _fallback_template(state)


def _build_guide_json(state: AgentState) -> dict:
    """构造结构化攻略（供前端/程序使用）。"""
    return {
        "destination": state.requirement.destination if state.requirement else "",
        "days": state.requirement.days if state.requirement else None,
        "budget": state.budget.model_dump() if state.budget else None,
        "itinerary": [day.model_dump() for day in state.itinerary],
    }


def guide_write(state: AgentState) -> dict:
    """生成攻略：优先 LLM 生成 Markdown，失败则降级为模板拼接。"""
    guide_json = _build_guide_json(state)

    llm = get_llm()
    if llm is None:
        markdown = _fallback_template(state)
        return {"guide_markdown": markdown, "guide_json": guide_json}

    try:
        resp = llm.invoke(
            [
                ("system", GUIDE_WRITE_SYSTEM_PROMPT),
                ("human", build_guide_user_prompt(state)),
            ]
        )
        markdown = resp.content if hasattr(resp, "content") else str(resp)
        # 去掉 LLM 可能包裹的代码块标记
        markdown = markdown.strip()
        if markdown.startswith("```"):
            markdown = markdown.strip("`").strip()
            if markdown.lower().startswith("markdown"):
                markdown = markdown[len("markdown"):].strip()
        return {"guide_markdown": markdown, "guide_json": guide_json}
    except Exception:
        markdown = _fallback_template(state)
        return {"guide_markdown": markdown, "guide_json": guide_json}


def _fallback_template(state: AgentState) -> str:
    """兜底：不调 LLM，用模板直接拼一份攻略，保证链路不中断。"""
    req = state.requirement
    lines = []
    lines.append(f"# {req.destination if req else ''} 旅行攻略")
    lines.append("")
    lines.append("## 行程概览")
    lines.append(f"- 天数：{req.days if req else '-'} 天")
    lines.append(f"- 偏好：{'、'.join(req.preferences) if req and req.preferences else '无'}")
    lines.append("")
    lines.append("## 分天安排")
    for day in state.itinerary:
        lines.append(f"### 第 {day.day} 天")
        if day.items:
            for p in day.items:
                lines.append(f"- {p.name}（{p.category}，约 {p.estimated_duration} 小时）")
        else:
            lines.append("- 自由活动 / 休息调整")
        lines.append("")
    if state.budget:
        lines.append("## 费用预估")
        lines.append(f"- 目标预算：¥{state.budget.target_budget}")
        lines.append(f"- 预估总费用：¥{state.budget.total_estimated}")
        for k, v in state.budget.breakdown.items():
            lines.append(f"  - {k}：¥{v}")
    return "\n".join(lines)
