from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    preferences: list[str] = Field(default_factory=list)
    context: dict[str, Any] | None = None


class AgentCard(BaseModel):
    id: str
    type: str
    title: str
    summary: str


class AgentMapCommand(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(BaseModel):
    conversation_id: str
    reply: str
    trip_state: dict[str, Any] = Field(default_factory=dict)
    cards: list[AgentCard] = Field(default_factory=list)
    map_commands: list[AgentMapCommand] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tool_trace_summary: list[dict[str, Any]] = Field(default_factory=list)
