from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services.analysis_service import get_population_heatmap


class GetPopulationHeatmapSummaryArgs(BaseModel):
    districts: list[str] = Field(default_factory=list, max_length=6)
    poi_ids: list[str] = Field(default_factory=list, max_length=20)


class PopulationHeatmapSummary(BaseModel):
    point_count: int
    max_weight: float | None = None
    avg_weight: float | None = None
    risk_level: str
    reference_points: list[dict[str, float]] = Field(default_factory=list)


def get_population_heatmap_summary_tool(db: Session, args: GetPopulationHeatmapSummaryArgs) -> dict:
    bbox = load_bbox_for_scope(db, districts=args.districts, poi_ids=args.poi_ids)
    points = get_population_heatmap(db, bbox=bbox)
    if not points:
        return PopulationHeatmapSummary(point_count=0, risk_level="unknown").model_dump()

    weights = [float(point["weight"]) for point in points]
    avg_weight = sum(weights) / len(weights)
    max_weight = max(weights)
    risk_level = "high" if max_weight >= 0.75 or avg_weight >= 0.55 else "medium" if max_weight >= 0.45 else "low"
    result = PopulationHeatmapSummary(
        point_count=len(points),
        max_weight=max_weight,
        avg_weight=round(avg_weight, 3),
        risk_level=risk_level,
        reference_points=[
            {
                "longitude": point["longitude"],
                "latitude": point["latitude"],
                "weight": point["weight"],
            }
            for point in points[:10]
        ],
    )
    return result.model_dump()


def load_bbox_for_scope(db: Session, *, districts: list[str], poi_ids: list[str]) -> list[float] | None:
    if poi_ids:
        stmt = text(
            """
            select
                ST_XMin(ST_Expand(ST_Extent(geom)::geometry, 0.03)) as min_lon,
                ST_YMin(ST_Expand(ST_Extent(geom)::geometry, 0.03)) as min_lat,
                ST_XMax(ST_Expand(ST_Extent(geom)::geometry, 0.03)) as max_lon,
                ST_YMax(ST_Expand(ST_Extent(geom)::geometry, 0.03)) as max_lat
            from public.pois
            where id in :poi_ids
              and is_active = true
            """
        ).bindparams(bindparam("poi_ids", expanding=True))
        row = db.execute(stmt, {"poi_ids": tuple(poi_ids)}).mappings().first()
    elif districts:
        stmt = text(
            """
            select
                min(longitude) as min_lon,
                min(latitude) as min_lat,
                max(longitude) as max_lon,
                max(latitude) as max_lat
            from public.pois
            where district in :districts
              and city = '武汉市'
              and is_active = true
            """
        ).bindparams(bindparam("districts", expanding=True))
        row = db.execute(stmt, {"districts": tuple(districts)}).mappings().first()
    else:
        return None

    if not row or row.get("min_lon") is None:
        return None
    return [float(row["min_lon"]), float(row["min_lat"]), float(row["max_lon"]), float(row["max_lat"])]
