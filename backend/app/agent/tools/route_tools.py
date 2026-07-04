from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.schemas.route import RouteMode, RoutePlanRequest, RoutePoint, RouteResponse
from app.services.route_service import get_route_by_id, plan_route


class PlanDayRouteArgs(BaseModel):
    day_index: int = Field(ge=1, le=7)
    mode: RouteMode = "walking"
    poi_ids: list[str] = Field(min_length=2, max_length=8)
    conversation_id: str | None = None
    route_name: str | None = None
    strategy: str | None = None


class PlanDayRouteResult(BaseModel):
    day_index: int
    route: RouteResponse
    route_id: str
    poi_ids: list[str]


class GetRouteArgs(BaseModel):
    route_id: str


class GetRouteResult(BaseModel):
    route: RouteResponse | None = None
    found: bool


def plan_day_route_tool(db: Session, args: PlanDayRouteArgs) -> dict[str, Any]:
    points = load_route_points(db, args.poi_ids)
    if len(points) < 2:
        raise ValueError("plan_day_route requires at least two valid POIs")

    payload = RoutePlanRequest(
        city="武汉市",
        route_name=args.route_name or f"Day {args.day_index} 行程路线",
        route_mode=args.mode,
        strategy=args.strategy,
        origin=points[0],
        destination=points[-1],
        waypoints=points[1:-1],
    )
    route = RouteResponse(**plan_route(db, payload))
    result = PlanDayRouteResult(
        day_index=args.day_index,
        route=route,
        route_id=route.route_id,
        poi_ids=args.poi_ids,
    )
    return result.model_dump()


def get_route_tool(db: Session, args: GetRouteArgs) -> dict[str, Any]:
    route = get_route_by_id(db, args.route_id)
    result = GetRouteResult(route=RouteResponse(**route) if route else None, found=route is not None)
    return result.model_dump()


def load_route_points(db: Session, poi_ids: list[str]) -> list[RoutePoint]:
    stmt = text(
        """
        select id::text, name_zh, longitude, latitude
        from public.pois
        where id in :poi_ids
          and is_active = true
        """
    ).bindparams(bindparam("poi_ids", expanding=True))
    rows = db.execute(stmt, {"poi_ids": tuple(poi_ids)}).mappings().all()
    by_id = {row["id"]: row for row in rows}
    points: list[RoutePoint] = []
    for poi_id in poi_ids:
        row = by_id.get(poi_id)
        if not row:
            continue
        points.append(
            RoutePoint(
                poi_id=row["id"],
                name=row["name_zh"],
                longitude=float(row["longitude"]),
                latitude=float(row["latitude"]),
            )
        )
    return points
