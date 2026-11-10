"""骨架阶段的基础测试：验证图结构可编译、节点可运行。"""

from app.agents import app_graph
from app.agents.state import AgentState


def test_graph_compiles_and_runs():
    """图能编译并跑通完整链路。

    由于 app_graph 挂了 checkpointer（支持多轮追问），invoke 必须传 thread_id。
    链路结果：intent_parse → (信息不足) → clarify → 回到 intent_parse，
    最多追问 MAX_CLARIFY_ROUNDS 次后强制进入 poi_search。
    """
    state = AgentState(user_input="武汉出发 3 天 预算 3000 江景")
    result = app_graph.invoke(
        state.model_dump(),
        config={"configurable": {"thread_id": "test-thread"}},
    )
    assert result is not None
    assert "messages" in result


def test_state_defaults():
    """状态模型默认值正确。"""
    s = AgentState()
    assert s.pois == []
    assert s.itinerary == []
    assert s.retry_count == 0
