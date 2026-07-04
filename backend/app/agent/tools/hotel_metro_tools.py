from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.agent.tools.common import MAX_NEARBY_RADIUS_METERS


class NearbyPoi(BaseModel):
    id: str
    name_zh: str
    longitude: float
    latitude: float
    address: str | None = None
    distance_m: float
    popularity_score: float | None = None


class GetNearbyMetroArgs(BaseModel):
    poi_id: str
    radius_meters: int = Field(default=1200, ge=100, le=MAX_NEARBY_RADIUS_METERS)
    limit: int = Field(default=5, ge=1, le=20)


class GetNearbyMetroResult(BaseModel):
    poi_id: str
    nearby_metro: list[NearbyPoi] = Field(default_factory=list)


class GetNearbyHotelsArgs(BaseModel):
    center_poi_ids: list[str] = Field(min_length=1, max_length=10)
    radius_meters: int = Field(default=2000, ge=100, le=MAX_NEARBY_RADIUS_METERS)
    limit: int = Field(default=10, ge=1, le=30)


class GetNearbyHotelsResult(BaseModel):
    center_poi_ids: list[str]
    nearby_hotels: list[NearbyPoi] = Field(default_factory=list)


def get_nearby_metro_tool(db: Session, args: GetNearbyMetroArgs) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            with target as (
                select geom
                from public.pois
                where id = cast(:poi_id as uuid)
                  and is_active = true
                limit 1
            )
            select
                p.id::text,
                p.name_zh,
                p.longitude,
                p.latitude,
                p.address,
                p.popularity_score,
                ST_Distance(p.geom::geography, target.geom::geography) as distance_m
            from public.pois p
            cross join target
            where p.category_code = 'metro_station'
              and p.is_active = true
              and ST_DWithin(p.geom::geography, target.geom::geography, :radius_meters)
            order by distance_m asc, p.name_zh
            limit :limit
            """
        ),
        {
            "poi_id": args.poi_id,
            "radius_meters": args.radius_meters,
            "limit": args.limit,
        },
    ).mappings().all()
    result = GetNearbyMetroResult(
        poi_id=args.poi_id,
        nearby_metro=[map_nearby_row(row) for row in rows],
    )
    return result.model_dump()


def get_nearby_hotels_tool(db: Session, args: GetNearbyHotelsArgs) -> dict[str, Any]:
    stmt = text(
        """
        with centers as (
            select geom
            from public.pois
            where id in :poi_ids
              and is_active = true
        ),
        center_geom as (
            select ST_Centroid(ST_Collect(geom)) as geom
            from centers
        )
        select
            p.id::text,
            p.name_zh,
            p.longitude,
            p.latitude,
            p.address,
            p.popularity_score,
            ST_Distance(p.geom::geography, center_geom.geom::geography) as distance_m
        from public.pois p
        cross join center_geom
        where p.category_code = 'hotel'
          and p.is_active = true
          and center_geom.geom is not null
          and ST_DWithin(p.geom::geography, center_geom.geom::geography, :radius_meters)
        order by distance_m asc, p.popularity_score desc nulls last, p.name_zh
        limit :limit
        """
    ).bindparams(bindparam("poi_ids", expanding=True))
    rows = db.execute(
        stmt,
        {
            "poi_ids": tuple(args.center_poi_ids),
            "radius_meters": args.radius_meters,
            "limit": args.limit,
        },
    ).mappings().all()
    result = GetNearbyHotelsResult(
        center_poi_ids=args.center_poi_ids,
        nearby_hotels=[map_nearby_row(row) for row in rows],
    )
    return result.model_dump()


def map_nearby_row(row: Any) -> NearbyPoi:
    popularity = row.get("popularity_score")
    return NearbyPoi(
        id=row["id"],
        name_zh=row["name_zh"],
        longitude=float(row["longitude"]),
        latitude=float(row["latitude"]),
        address=row.get("address"),
        distance_m=round(float(row["distance_m"]), 2),
        popularity_score=float(popularity) if popularity is not None else None,
    )
