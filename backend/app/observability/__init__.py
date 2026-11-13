"""可观测层：LangSmith 追踪配置。

LangChain / LangGraph 对 LangSmith 是原生集成——只要进程环境里存在
LANGSMITH_API_KEY / LANGSMITH_PROJECT / LANGSMITH_TRACING 这几个环境变量，
所有 LLM 调用和图的 invoke/astream 都会自动上报 trace，几乎零代码侵入。

本模块的职责：在应用启动时，把 settings 里的 langsmith_* 配置显式注入
os.environ，让 LangChain 的自动追踪生效。集中在这里，未来切 Langfuse 或
关闭追踪，只需改这一个文件。
"""

import os

from app.config import settings


def setup_observability() -> None:
    """根据配置注入可观测性环境变量（幂等，可重复调用）。

    说明：
    - LangSmith 官方变量名：LANGSMITH_API_KEY、LANGSMITH_PROJECT、LANGSMITH_TRACING
    - 只有当配置了 API Key 时才开启追踪；没配 Key 时保持关闭（不影响功能）。
    """
    if not settings.langsmith_api_key:
        return

    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project or "tripmind")
    os.environ.setdefault("LANGSMITH_TRACING", "true")
