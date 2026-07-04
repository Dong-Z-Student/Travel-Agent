from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_population_heatmap(db: Session, bbox: list[float] | None = None) -> list[dict[str, Any]]:
    filters = []
    params: dict[str, Any] = {}
    if bbox:
        filters.extend([
            "longitude between :min_lon and :max_lon",
            "latitude between :min_lat and :max_lat",
        ])
        params.update({
            "min_lon": bbox[0],
            "min_lat": bbox[1],
            "max_lon": bbox[2],
            "max_lat": bbox[3],
        })

    where_sql = f"where {' and '.join(filters)}" if filters else ""
    rows = db.execute(
        text(
            f"""
            select longitude, latitude, weight
            from public.population_heat_points
            {where_sql}
            order by weight desc
            """
        ),
        params,
    ).mappings().all()
    return [
        {
            "longitude": float(row["longitude"]),
            "latitude": float(row["latitude"]),
            "weight": float(row["weight"]),
        }
        for row in rows
    ]
