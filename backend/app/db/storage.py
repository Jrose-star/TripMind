"""存储层：历史会话与行程结果的持久化操作。

所有方法在数据库不可用时安全降级（返回空/None），不抛异常阻塞主链路。
"""

from __future__ import annotations

import json
from typing import Any

from app.db import get_pool


async def save_session(
    thread_id: str,
    user_input: str,
    destination: str | None = None,
    days: int | None = None,
    budget: float | None = None,
    status: str = "completed",
) -> int | None:
    """保存一次规划会话，返回会话自增 id（数据库不可用返回 None）。"""
    pool = get_pool()
    if pool is None:
        return None
    try:
        return await pool.fetchval(
            """
            INSERT INTO planning_sessions (thread_id, user_input, destination, days, budget, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (thread_id) DO UPDATE SET
                user_input = EXCLUDED.user_input,
                destination = EXCLUDED.destination,
                days = EXCLUDED.days,
                budget = EXCLUDED.budget,
                status = EXCLUDED.status
            RETURNING id
            """,
            thread_id,
            user_input,
            destination,
            days,
            budget,
            status,
        )
    except Exception:
        return None


async def save_result(
    session_id: int,
    thread_id: str,
    destination: str | None,
    itinerary: list[dict[str, Any]],
    budget: dict[str, Any] | None,
    weather: dict[str, Any] | None,
    guide_markdown: str,
    guide_json: dict[str, Any],
) -> int | None:
    """保存一次会话产出的行程结果。"""
    pool = get_pool()
    if pool is None:
        return None
    try:
        return await pool.fetchval(
            """
            INSERT INTO plan_results
                (session_id, thread_id, destination, itinerary, budget, weather, guide_markdown, guide_json)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            session_id,
            thread_id,
            destination,
            json.dumps(itinerary, ensure_ascii=False),
            json.dumps(budget, ensure_ascii=False) if budget else None,
            json.dumps(weather, ensure_ascii=False) if weather else None,
            guide_markdown,
            json.dumps(guide_json, ensure_ascii=False),
        )
    except Exception:
        return None


async def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    """列出历史会话（按时间倒序），附带是否已产出攻略。"""
    pool = get_pool()
    if pool is None:
        return []
    try:
        rows = await pool.fetch(
            """
            SELECT
                s.thread_id,
                s.user_input,
                s.destination,
                s.days,
                s.budget,
                s.status,
                s.created_at,
                r.guide_markdown IS NOT NULL AS has_result
            FROM planning_sessions s
            LEFT JOIN LATERAL (
                SELECT guide_markdown FROM plan_results
                WHERE session_id = s.id
                ORDER BY id DESC LIMIT 1
            ) r ON TRUE
            ORDER BY s.created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [
            {
                "thread_id": row["thread_id"],
                "user_input": row["user_input"],
                "destination": row["destination"],
                "days": row["days"],
                "budget": row["budget"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat(),
                "has_result": row["has_result"],
            }
            for row in rows
        ]
    except Exception:
        return []


async def get_result(thread_id: str) -> dict[str, Any] | None:
    """按 thread_id 查询某次会话的完整结果。"""
    pool = get_pool()
    if pool is None:
        return None
    try:
        row = await pool.fetchrow(
            """
            SELECT
                r.thread_id,
                r.destination,
                r.itinerary,
                r.budget,
                r.weather,
                r.guide_markdown,
                r.guide_json,
                s.user_input
            FROM plan_results r
            JOIN planning_sessions s ON s.id = r.session_id
            WHERE r.thread_id = $1
            ORDER BY r.id DESC
            LIMIT 1
            """,
            thread_id,
        )
        if row is None:
            return None
        return {
            "thread_id": row["thread_id"],
            "user_input": row["user_input"],
            "destination": row["destination"],
            "itinerary": json.loads(row["itinerary"] or "[]"),
            "budget": json.loads(row["budget"]) if row["budget"] else None,
            "weather": json.loads(row["weather"]) if row["weather"] else None,
            "guide_markdown": row["guide_markdown"],
            "guide_json": json.loads(row["guide_json"]) if row["guide_json"] else None,
        }
    except Exception:
        return None
