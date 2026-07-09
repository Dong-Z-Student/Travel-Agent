from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent.state_manager import (
    normalize_conversation_id,
    resolve_owned_conversation_id,
    save_message,
    upsert_conversation,
    upsert_trip_state,
)
from app.agent.graph.runner import GraphAgentRunner
from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest
from app.services.user_service import ensure_user_profile


def chat(db: Session, payload: AgentChatRequest, user: CurrentUser | None = None) -> dict:
    if user:
        ensure_user_profile(db, user)
        conversation_id = normalize_conversation_id(payload.conversation_id)
        conversation_id = resolve_owned_conversation_id(db, conversation_id=conversation_id, user=user)
        conversation_id = upsert_conversation(db, conversation_id=conversation_id, user=user, message=payload.message)
        save_message(db, conversation_id=conversation_id, role="user", content=payload.message, payload={"context": payload.context})
        payload = payload.model_copy(update={"conversation_id": conversation_id})

    response = GraphAgentRunner(db).run(payload, user)

    if user:
        save_message(db, conversation_id=conversation_id, role="assistant", content=response["reply"], payload=response)
        upsert_trip_state(db, conversation_id=conversation_id, response=response, payload=payload)
        db.commit()

    return response
