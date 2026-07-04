from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.spatial_query_service import query_pois_by_geometry


class QueryPoisByGeometryArgs(BaseModel):
    query_type: str
    geometry: dict[str, Any]
    city: str = "武汉市"
    category_codes: list[str] = Field(default_factory=list)
    limit: int = Field(default=30, ge=1, le=80)
    radius_meters: float | None = Field(default=None, ge=100, le=3000)
    buffer_meters: float | None = Field(default=None, ge=100, le=3000)
    query_id: str | None = None


def query_pois_by_geometry_tool(db: Session, args: QueryPoisByGeometryArgs) -> dict[str, Any]:
    if args.city != "武汉市":
        raise ValueError("spatial query tool is limited to Wuhan city")
    return query_pois_by_geometry(
        db,
        query_id=args.query_id or f"agent_spatial_{uuid4().hex[:10]}",
        query_type=args.query_type,
        geometry=args.geometry,
        city=args.city,
        category_codes=args.category_codes,
        limit=args.limit,
        radius_meters=args.radius_meters,
        buffer_meters=args.buffer_meters,
        user=None,
    )
