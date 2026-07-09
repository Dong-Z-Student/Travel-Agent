from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent.orchestrator import TravelAgentOrchestrator
from app.agent_graph.runner import GraphAgentRunner, GraphAgentUnavailable
from app.core.config import settings
from app.agent.state_manager import (
    normalize_conversation_id,
    resolve_owned_conversation_id,
    save_message,
    upsert_conversation,
    upsert_trip_state,
)
from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest
from app.services.user_service import ensure_user_profile


def chat(db: Session, payload: AgentChatRequest, user: CurrentUser | None = None) -> dict[str, Any]:
    if user:
        ensure_user_profile(db, user)
        conversation_id = normalize_conversation_id(payload.conversation_id)
        conversation_id = resolve_owned_conversation_id(db, conversation_id=conversation_id, user=user)
        conversation_id = upsert_conversation(db, conversation_id=conversation_id, user=user, message=payload.message)
        save_message(db, conversation_id=conversation_id, role="user", content=payload.message, payload={"context": payload.context})
        payload = payload.model_copy(update={"conversation_id": conversation_id})

    if settings.agent_engine.lower() == "graph":
        try:
            response = GraphAgentRunner(db).run(payload, user)
        except GraphAgentUnavailable:
            response = TravelAgentOrchestrator(db).run(payload, user)
    else:
        response = TravelAgentOrchestrator(db).run(payload, user)

    if user:
        save_message(db, conversation_id=conversation_id, role="assistant", content=response["reply"], payload=response)
        upsert_trip_state(db, conversation_id=conversation_id, response=response, payload=payload)
        db.commit()

    return response


def build_rule_based_response(payload: AgentChatRequest, conversation_id: str) -> dict[str, Any]:
    message = payload.message or ""
    context_poi_ids = payload.context.get("poi_ids", []) if payload.context else []
    preferences = payload.preferences or []

    if context_poi_ids:
        reply = f"我已经收到你刚才空间查询选中的 {len(context_poi_ids)} 个候选 POI，会优先围绕这些点继续规划。"
    elif "地铁" in message or "交通" in message:
        reply = "我会优先考虑地铁可达性，减少换乘和步行压力。"
    elif "路线" in message or "规划" in message or "两天" in message:
        reply = "我已经记录你的路线规划需求。真实路线规划接口已准备好，后续 Agent 阶段会把候选 POI 组织成路线请求。"
    else:
        reply = "我已经收到你的需求，会结合武汉真实 POI、空间查询结果和长期偏好进行规划。"

    return {
        "conversation_id": conversation_id,
        "reply": reply,
        "trip_state": {
            "city": "武汉市",
            "preferences": preferences,
            "candidate_poi_ids": context_poi_ids,
        },
        "cards": [
            {
                "id": "card_stage1_agent_stub",
                "type": "trip_hint",
                "title": "第一阶段 Agent Stub",
                "summary": "当前已接入真实数据接口，完整智能规划将在第二大阶段实现。",
            }
        ],
        "map_commands": [
            {
                "type": "HIGHLIGHT_POIS",
                "payload": {
                    "poi_ids": context_poi_ids,
                    "layer_id": f"agent-context-{conversation_id}",
                    "title": "Agent 当前候选 POI",
                },
            }
        ] if context_poi_ids else [],
    }


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)
