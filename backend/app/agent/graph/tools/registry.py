from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.agent.tools.hotel_metro_tools import (
    GetNearbyHotelsArgs,
    GetNearbyMetroArgs,
    get_nearby_hotels_tool,
    get_nearby_metro_tool,
)
from app.agent.tools.poi_tools import GetPoiDetailArgs, SearchPoisArgs, get_poi_detail_tool, search_pois_tool
from app.agent.tools.route_tools import PlanDayRouteArgs, plan_day_route_tool
from app.agent.tools.weather_tools import GetWeatherArgs, get_weather_tool
from app.agent.graph.schemas import GraphToolResult


class ToolLimitState(BaseModel):
    total_calls: int = 0
    per_tool: dict[str, int] = Field(default_factory=dict)


@dataclass(frozen=True)
class RegisteredGraphTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[[Session, Any], dict[str, Any]]
    max_calls: int = 3


class GraphToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredGraphTool] = {}
        self.register(
            RegisteredGraphTool(
                name="search_pois",
                description="Search real Wuhan POIs by category, keyword, district and limit.",
                args_schema=SearchPoisArgs,
                handler=search_pois_tool,
                max_calls=4,
            )
        )
        self.register(
            RegisteredGraphTool(
                name="get_poi_detail",
                description="Read detailed scenic profile and images for one POI.",
                args_schema=GetPoiDetailArgs,
                handler=get_poi_detail_tool,
                max_calls=8,
            )
        )
        self.register(
            RegisteredGraphTool(
                name="get_weather",
                description="Read cached or live Amap weather for Wuhan district/adcode.",
                args_schema=GetWeatherArgs,
                handler=get_weather_tool,
                max_calls=3,
            )
        )
        self.register(
            RegisteredGraphTool(
                name="get_nearby_metro",
                description="Find metro stations near a POI using PostGIS distance.",
                args_schema=GetNearbyMetroArgs,
                handler=get_nearby_metro_tool,
                max_calls=4,
            )
        )
        self.register(
            RegisteredGraphTool(
                name="get_nearby_hotels",
                description="Find hotels near one or more POIs using PostGIS distance.",
                args_schema=GetNearbyHotelsArgs,
                handler=get_nearby_hotels_tool,
                max_calls=2,
            )
        )
        self.register(
            RegisteredGraphTool(
                name="plan_day_route",
                description="Plan one day route through existing POI ids using route_service.",
                args_schema=PlanDayRouteArgs,
                handler=plan_day_route_tool,
                max_calls=3,
            )
        )

    def register(self, tool: RegisteredGraphTool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "args_schema": tool.args_schema.model_json_schema(),
                "max_calls": tool.max_calls,
            }
            for tool in self._tools.values()
        ]

    def execute_many(
        self,
        db: Session,
        tool_calls: list[dict[str, Any]],
        *,
        max_total_calls: int = 8,
    ) -> list[dict[str, Any]]:
        limits = ToolLimitState()
        results: list[dict[str, Any]] = []
        for raw_call in tool_calls[:max_total_calls]:
            result = self.execute(db, raw_call, limits=limits, max_total_calls=max_total_calls)
            results.append(result.model_dump())
        return results

    def execute(
        self,
        db: Session,
        raw_call: dict[str, Any],
        *,
        limits: ToolLimitState,
        max_total_calls: int,
    ) -> GraphToolResult:
        name = str(raw_call.get("tool") or "")
        args = dict(raw_call.get("args") or {})
        tool = self._tools.get(name)
        if not tool:
            return GraphToolResult(tool=name or "unknown", args=args, status="blocked", error="Tool is not registered")

        if limits.total_calls >= max_total_calls:
            return GraphToolResult(tool=name, args=args, status="blocked", error="Tool call limit exceeded")

        current_count = limits.per_tool.get(name, 0)
        if current_count >= tool.max_calls:
            return GraphToolResult(tool=name, args=args, status="blocked", error=f"{name} call limit exceeded")

        try:
            parsed_args = tool.args_schema.model_validate(args)
        except ValidationError as exc:
            return GraphToolResult(tool=name, args=args, status="blocked", error=str(exc))

        limits.total_calls += 1
        limits.per_tool[name] = current_count + 1

        try:
            result = tool.handler(db, parsed_args)
            if name == "search_pois":
                result = maybe_relax_theme_search(db, tool, parsed_args, result)
            return GraphToolResult(
                tool=name,
                args=parsed_args.model_dump(mode="json"),
                status="success",
                result=result,
                summary=summarize_tool_result(name, result),
            )
        except Exception as exc:  # noqa: BLE001
            return GraphToolResult(
                tool=name,
                args=parsed_args.model_dump(mode="json"),
                status="failed",
                error=str(exc),
            )


def summarize_tool_result(name: str, result: dict[str, Any]) -> str:
    if name == "search_pois":
        return f"found {len(result.get('pois') or [])} POIs"
    if name == "get_poi_detail":
        poi = result.get("poi") or {}
        return f"detail {'found' if result.get('found') else 'missing'}: {poi.get('name_zh') or ''}".strip()
    if name == "get_weather":
        return f"weather cache_hit={result.get('cache_hit')}"
    if name == "get_nearby_metro":
        return f"found {len(result.get('nearby_metro') or [])} metro stations"
    if name == "get_nearby_hotels":
        return f"found {len(result.get('nearby_hotels') or [])} hotels"
    if name == "plan_day_route":
        return f"route_id={result.get('route_id')}"
    return "success"


def maybe_relax_theme_search(
    db: Session,
    tool: RegisteredGraphTool,
    parsed_args: BaseModel,
    result: dict[str, Any],
) -> dict[str, Any]:
    if result.get("pois"):
        return result
    keyword = str(getattr(parsed_args, "keyword", "") or "")
    theme_keywords = {"亲子", "夜景", "下雨", "雨天", "室内", "轻松", "人少"}
    if keyword not in theme_keywords:
        return result
    relaxed_args = parsed_args.model_copy(update={"keyword": None})
    relaxed_result = tool.handler(db, relaxed_args)
    relaxed_result["relaxed_from_keyword"] = keyword
    return relaxed_result


def get_graph_tool_registry() -> GraphToolRegistry:
    return GraphToolRegistry()
