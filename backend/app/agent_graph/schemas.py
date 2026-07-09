from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GraphUnderstanding(BaseModel):
    intent: Literal[
        "plan_trip",
        "modify_trip",
        "search_poi",
        "weather_question",
        "nearby_support",
        "preference_update",
        "smalltalk",
    ] = "search_poi"
    keywords: list[str] = Field(default_factory=list)
    category_codes: list[str] = Field(default_factory=lambda: ["scenic_spot"])
    district: str | None = None
    days: int | None = None
    travel_dates: list[str] = Field(default_factory=list)
    needs_tool: bool = True
    should_plan_route: bool = False
    reply_strategy: str = "先基于真实数据回答，再自然追问缺失信息。"


class GraphToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class GraphToolPlan(BaseModel):
    tool_calls: list[GraphToolCall] = Field(default_factory=list)


class GraphToolResult(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "failed", "blocked"] = "success"
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    summary: str = ""
