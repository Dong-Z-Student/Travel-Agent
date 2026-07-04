from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.poi import PoiBase


SpatialQueryType = Literal["point_radius", "line_buffer", "bezier_buffer", "polygon_contains"]


class SpatialQueryRequest(BaseModel):
    query_id: str | None = None
    query_type: SpatialQueryType
    geometry: dict[str, Any]
    radius_meters: float | None = Field(default=None, gt=0)
    buffer_meters: float | None = Field(default=None, gt=0)
    limit: int | None = Field(default=None, ge=1, le=200)
    city: str | None = None
    category_codes: list[str] = Field(default_factory=list)


class SpatialMapCommand(BaseModel):
    type: str
    payload: dict[str, Any]


class SpatialAgentContext(BaseModel):
    text: str
    poi_ids: list[str] = Field(default_factory=list)


class SpatialPoi(PoiBase):
    distance_m: float | None = None


class SpatialQueryResponse(BaseModel):
    query_id: str
    pois: list[SpatialPoi] = Field(default_factory=list)
    map_commands: list[SpatialMapCommand] = Field(default_factory=list)
    agent_context: SpatialAgentContext
