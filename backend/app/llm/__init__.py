"""LLM 可插拔层：抽象模型接口，便于切换不同模型。"""

from __future__ import annotations

from app.config import settings


def get_llm():
    """返回一个 LLM 实例（兼容 LangChain ChatOpenAI 协议）。

    本阶段为占位实现，仅保证结构存在；实际调用在核心 Agent 阶段接入。
    """
    # 延迟导入，避免未安装 langchain-openai 时启动失败
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.2,
        )
    except ImportError:
        # 依赖未安装时的兜底占位，保证骨架可运行
        return None
