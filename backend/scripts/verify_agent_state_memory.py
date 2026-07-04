from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import orchestrator as orchestrator_module
from app.agent.model_client import AgentModelConfigError
from app.agent.orchestrator import TravelAgentOrchestrator
from app.schemas.agent import AgentChatRequest


class FallbackModelClient:
    def __init__(self) -> None:
        raise AgentModelConfigError("forced fallback for deterministic state verification")


def main() -> None:
    orchestrator_module.AgentModelClient = FallbackModelClient
    agent = TravelAgentOrchestrator(db=None)
    messages = [
        "我想在武汉玩两天，轻松一点。",
        "我以后规划都希望地铁优先。",
        "这次想打车方便一点。",
    ]
    result = []
    for message in messages:
        response = agent.run(AgentChatRequest(message=message), user=None)
        state = response["trip_state"]
        result.append(
            {
                "message": message,
                "intent": state.get("intent"),
                "preferences": state.get("preferences"),
                "temporary_preferences": state.get("temporary_preferences"),
                "long_term_preferences": state.get("long_term_preferences"),
                "day_plan_count": len(state.get("day_plans") or []),
                "day_plans": state.get("day_plans"),
            }
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
