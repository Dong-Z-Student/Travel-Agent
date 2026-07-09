from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ModelRole = Literal["fast", "planner"]


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelCallResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str
    model_role: ModelRole
    content: str
    token_usage: TokenUsage | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredModelResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str
    model_role: ModelRole
    parsed: dict[str, Any]
    content: str
    token_usage: TokenUsage | None = None
    attempts: int = 1
    fallback_used: bool = False


class SimpleAgentReply(BaseModel):
    reply: str
    intent_hint: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AgentLoadedContext(BaseModel):
    conversation_id: str
    user_id: str | None = None
    preferences: list[dict[str, Any]] = Field(default_factory=list)
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    trip_state: dict[str, Any] = Field(default_factory=dict)
    spatial_context: dict[str, Any] = Field(default_factory=dict)
    context_summary: str = ""


class AgentModelStatusResponse(BaseModel):
    configured: bool
    agent_mode: str
    fast_model: str
    planner_model: str
    default_model: str
    complex_model: str
    base_url: str
    timeout_seconds: int
    max_retries: int
    langchain_available: bool


class AgentModelTestRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    message: str = "我想在武汉玩两天，轻松一点。"
    model_role: ModelRole = "fast"
    json_mode: bool = True


class AgentModelTestResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model: str
    model_role: ModelRole
    content: str
    parsed: SimpleAgentReply | None = None
    token_usage: TokenUsage | None = None
    attempts: int = 1
    fallback_used: bool = False
