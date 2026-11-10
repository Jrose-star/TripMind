"""骨架阶段的基础测试：验证图结构可编译、节点可运行。"""

from app.agents import app_graph
from app.agents.state import AgentState


def test_graph_compiles_and_runs():
    """图能编译并跑通完整链路（含占位节点）。"""
    state = AgentState(user_input="武汉出发 3 天 预算 3000 江景")
    result = app_graph.invoke(state.model_dump())
    # 骨架版：intent_parse 会标记缺失字段 → 路由到 clarify → END
    assert result is not None
    assert "messages" in result


def test_state_defaults():
    """状态模型默认值正确。"""
    s = AgentState()
    assert s.pois == []
    assert s.itinerary == []
    assert s.retry_count == 0
