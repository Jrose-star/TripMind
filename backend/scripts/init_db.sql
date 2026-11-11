-- 旅行规划 Agent 数据库表结构
-- 数据库：travel_agent
-- 执行方式：psql -h 127.0.0.1 -U travel_agent -d travel_agent -f scripts/init_db.sql

-- ============ 历史会话表 ============
-- 记录每一次「规划会话」的元信息：谁、什么时候、什么需求、最终状态
CREATE TABLE IF NOT EXISTS planning_sessions (
    id              BIGSERIAL PRIMARY KEY,
    thread_id       TEXT NOT NULL UNIQUE,          -- LangGraph 会话线程 ID（多轮追问共用）
    user_input      TEXT NOT NULL,                 -- 用户原始需求文本
    destination     TEXT,                          -- 解析出的目的地（冗余，便于列表展示）
    days            INTEGER,                       -- 行程天数
    budget          DOUBLE PRECISION,              -- 目标预算
    status          TEXT NOT NULL DEFAULT 'completed',  -- completed / need_clarify
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON planning_sessions (created_at DESC);

-- ============ 行程结果表 ============
-- 记录一次会话产出的完整结果：结构化行程 + 预算 + 天气 + 攻略正文
CREATE TABLE IF NOT EXISTS plan_results (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL REFERENCES planning_sessions(id) ON DELETE CASCADE,
    thread_id       TEXT NOT NULL,                 -- 冗余，便于按 thread_id 查询
    destination     TEXT,
    itinerary       JSONB NOT NULL DEFAULT '[]'::jsonb,  -- 分天行程（DayPlan 列表）
    budget          JSONB,                         -- 预算结果（BudgetResult）
    weather         JSONB,                         -- 天气预报（WeatherInfo）
    guide_markdown  TEXT,                          -- 攻略正文（Markdown）
    guide_json      JSONB,                         -- 结构化攻略
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_results_thread_id ON plan_results (thread_id);
CREATE INDEX IF NOT EXISTS idx_results_session_id ON plan_results (session_id);

-- 更新时间触发器：planning_sessions.updated_at 自动刷新
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sessions_updated_at ON planning_sessions;
CREATE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON planning_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
