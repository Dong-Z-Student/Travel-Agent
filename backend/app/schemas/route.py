from typing import Any, Literal

from pydantic import BaseModel, Field


RouteMode = Literal["walking", "transit", "driving"]


class RoutePoint(BaseModel):
    name: str | None = None
    longitude: float
    latitude: float
    poi_id: str | None = None
    stay_minutes: int | None = None
    note: str | None = None


class RoutePlanRequest(BaseModel):
    city: str = "武汉市"
    route_name: str | None = None
    route_mode: RouteMode = "walking"
    strategy: str | None = None
    origin: RoutePoint
    destination: RoutePoint
    waypoints: list[RoutePoint] = Field(default_factory=list)


class RouteStop(BaseModel):
    id: str | None = None
    poi_id: str | None = None
    stop_order: int
    name: str | None = None
    longitude: float
    latitude: float
    arrival_time: str | None = None
    stay_minutes: int | None = None
    note: str | None = None


class RouteAnimation(BaseModel):
    speed: float = 0.006
    loop: bool = True


class RouteResponse(BaseModel):
    route_id: str
    route_name: str | None = None
    route_mode: str | None = None
    strategy: str | None = None
    cache_hit: bool = False
    distance_m: float | None = None
    duration_minutes: float | None = None
    geometry: dict[str, Any]
    stops: list[RouteStop] = Field(default_factory=list)
    animation: RouteAnimation = Field(default_factory=RouteAnimation)
