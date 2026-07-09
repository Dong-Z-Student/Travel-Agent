from __future__ import annotations

from typing import Any, TypedDict


class GraphAgentState(TypedDict, total=False):
    conversation_id: str
    user_id: str | None
    message: str
    request_context: dict[str, Any]
    loaded_context: dict[str, Any]
    understanding: dict[str, Any]
    tool_plan: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    reflection: dict[str, Any]
    retry_count: int
    retry_summary: dict[str, Any]
    trip_state: dict[str, Any]
    cards: list[dict[str, Any]]
    map_commands: list[dict[str, Any]]
    reply: str
    warnings: list[str]
    tool_trace_summary: list[dict[str, Any]]
