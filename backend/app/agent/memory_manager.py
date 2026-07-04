from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.schemas import AgentLoadedContext
from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest


def load_context(
    db: Session,
    *,
    conversation_id: str,
    payload: AgentChatRequest,
    user: CurrentUser | None,
) -> AgentLoadedContext:
    preferences = load_user_preferences(db, user) if user else []
    recent_messages = load_recent_messages(db, conversation_id=conversation_id) if user else []
    spatial_context = normalize_spatial_context(payload.context)
    trip_state = load_trip_state(db, conversation_id=conversation_id) if user else {}
    if not trip_state and isinstance(spatial_context.get("trip_state"), dict):
        trip_state = spatial_context["trip_state"]
    return AgentLoadedContext(
        conversation_id=conversation_id,
        user_id=user.id if user else None,
        preferences=preferences,
        recent_messages=recent_messages,
        trip_state=trip_state,
        spatial_context=spatial_context,
        context_summary=build_context_summary(recent_messages=recent_messages, trip_state=trip_state),
    )


def load_user_preferences(db: Session, user: CurrentUser | None) -> list[dict[str, Any]]:
    if not user:
        return []
    rows = db.execute(
        text(
            """
            select preference_type, preference_value, confidence, source
            from public.user_preferences
            where user_id = cast(:user_id as uuid)
              and is_active = true
            order by preference_type, preference_value
            limit 20
            """
        ),
        {"user_id": user.id},
    ).mappings().all()
    return [
        {
            "preference_type": row["preference_type"],
            "preference_value": row["preference_value"],
            "confidence": float(row["confidence"]),
            "source": row["source"],
        }
        for row in rows
    ]


def load_recent_messages(db: Session, *, conversation_id: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            select role, content, payload, created_at
            from public.messages
            where conversation_id = cast(:conversation_id as uuid)
            order by created_at desc
            limit :limit
            """
        ),
        {"conversation_id": conversation_id, "limit": limit},
    ).mappings().all()
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "payload": row["payload"] or {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in reversed(rows)
    ]


def load_trip_state(db: Session, *, conversation_id: str) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            select state_json, preferences, candidate_poi_ids
            from public.trip_states
            where conversation_id = cast(:conversation_id as uuid)
            limit 1
            """
        ),
        {"conversation_id": conversation_id},
    ).mappings().first()
    if not row:
        return {}
    state = dict(row["state_json"] or {})
    state.setdefault("preferences", row["preferences"] or [])
    state.setdefault("candidate_poi_ids", row["candidate_poi_ids"] or [])
    return state


def normalize_spatial_context(context: dict[str, Any] | None) -> dict[str, Any]:
    if not context:
        return {}
    poi_ids = context.get("poi_ids") or []
    return {
        "text": context.get("text") or "",
        "poi_ids": [str(poi_id) for poi_id in poi_ids if poi_id],
        "trip_state": context.get("trip_state") if isinstance(context.get("trip_state"), dict) else {},
        "raw": context,
    }


def build_context_summary(*, recent_messages: list[dict[str, Any]], trip_state: dict[str, Any]) -> str:
    parts: list[str] = []
    if trip_state:
        city = trip_state.get("city")
        days = trip_state.get("days")
        planning_stage = trip_state.get("planning_stage")
        parts.append(f"已有 trip_state: city={city}, days={days}, planning_stage={planning_stage}")
    if recent_messages:
        last_messages = recent_messages[-4:]
        compact = " | ".join(f"{item['role']}: {item['content'][:80]}" for item in last_messages)
        parts.append(f"最近对话: {compact}")
    return "\n".join(parts) if parts else "暂无历史上下文。"
