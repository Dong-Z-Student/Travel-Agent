from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest


def normalize_conversation_id(conversation_id: str | None) -> str:
    if conversation_id:
        try:
            uuid.UUID(conversation_id)
            return conversation_id
        except ValueError:
            pass
    return str(uuid.uuid4())


def resolve_owned_conversation_id(db: Session, *, conversation_id: str, user: CurrentUser) -> str:
    row = db.execute(
        text(
            """
            select user_id::text
            from public.conversations
            where id = cast(:conversation_id as uuid)
            limit 1
            """
        ),
        {"conversation_id": conversation_id},
    ).mappings().first()
    if row and row["user_id"] != user.id:
        return str(uuid.uuid4())
    return conversation_id


def upsert_conversation(db: Session, *, conversation_id: str, user: CurrentUser, message: str) -> str:
    row = db.execute(
        text(
            """
            insert into public.conversations (id, user_id, title, city)
            values (cast(:conversation_id as uuid), cast(:user_id as uuid), :title, '武汉市')
            on conflict (id) do update
            set updated_at = now()
            where conversations.user_id = cast(:user_id as uuid)
            returning id::text
            """
        ),
        {
            "conversation_id": conversation_id,
            "user_id": user.id,
            "title": message[:40] if message else "武汉出行规划",
        },
    ).mappings().first()
    if not row:
        return upsert_conversation(db, conversation_id=str(uuid.uuid4()), user=user, message=message)
    return row["id"]


def save_message(
    db: Session,
    *,
    conversation_id: str,
    role: str,
    content: str,
    payload: dict[str, Any] | None = None,
) -> str:
    row = db.execute(
        text(
            """
            insert into public.messages (conversation_id, role, content, payload)
            values (cast(:conversation_id as uuid), :role, :content, cast(:payload as jsonb))
            returning id::text
            """
        ),
        {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "payload": json_dumps(payload or {}),
        },
    ).mappings().first()
    return row["id"]


def upsert_trip_state(db: Session, *, conversation_id: str, response: dict[str, Any], payload: AgentChatRequest) -> None:
    trip_state = response.get("trip_state") or {}
    db.execute(
        text(
            """
            insert into public.trip_states (
                conversation_id,
                city,
                preferences,
                candidate_poi_ids,
                state_json
            )
            values (
                cast(:conversation_id as uuid),
                :city,
                cast(:preferences as jsonb),
                cast(:candidate_poi_ids as jsonb),
                cast(:state_json as jsonb)
            )
            on conflict (conversation_id) do update
            set
                city = excluded.city,
                preferences = excluded.preferences,
                candidate_poi_ids = excluded.candidate_poi_ids,
                state_json = excluded.state_json,
                updated_at = now()
            """
        ),
        {
            "conversation_id": conversation_id,
            "city": trip_state.get("city") or "武汉市",
            "preferences": json_dumps(trip_state.get("preferences", [])),
            "candidate_poi_ids": json_dumps(trip_state.get("candidate_poi_ids", [])),
            "state_json": json_dumps(trip_state),
        },
    )


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
