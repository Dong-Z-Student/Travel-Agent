from __future__ import annotations

import json
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.services.poi_service import map_poi_base
from app.services.user_service import ensure_user_profile


DEFAULT_RANGE_METERS = 2000
DEFAULT_LIMIT = 80
MAX_LIMIT = 200

QUERY_LABELS = {
    "point_radius": "点附近查询",
    "line_buffer": "线附近查询",
    "bezier_buffer": "贝塞尔曲线附近查询",
    "polygon_contains": "面内查询",
}

EXPECTED_GEOMETRY_TYPES = {
    "point_radius": {"Point"},
    "line_buffer": {"LineString"},
    "bezier_buffer": {"LineString"},
    "polygon_contains": {"Polygon", "MultiPolygon"},
}


class SpatialQueryError(ValueError):
    pass


def query_pois_by_geometry(
    db: Session,
    *,
    query_id: str,
    query_type: str,
    geometry: dict[str, Any],
    city: str | None = None,
    category_codes: list[str] | None = None,
    limit: int | None = None,
    radius_meters: float | None = None,
    buffer_meters: float | None = None,
    user: CurrentUser | None = None,
) -> dict[str, Any]:
    validate_geometry(query_type, geometry)

    safe_limit = min(max(limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    geometry_json = json.dumps(geometry, ensure_ascii=False)
    rows = execute_spatial_query(
        db,
        query_type=query_type,
        geometry_json=geometry_json,
        city=city,
        category_codes=category_codes or [],
        limit=safe_limit,
    )

    pois = [map_spatial_poi(row) for row in rows]
    poi_ids = [poi["id"] for poi in pois]
    label = QUERY_LABELS.get(query_type, "空间查询")
    if user:
        save_spatial_query_record(
            db,
            user=user,
            query_id=query_id,
            query_type=query_type,
            geometry_json=geometry_json,
            radius_meters=radius_meters,
            buffer_meters=buffer_meters,
            city=city,
            category_codes=category_codes or [],
            rows=rows,
        )

    return {
        "query_id": query_id,
        "pois": pois,
        "map_commands": [
            {
                "type": "HIGHLIGHT_POIS",
                "payload": {
                    "poi_ids": poi_ids,
                    "pois": pois,
                    "layer_id": f"spatial-query-result-{query_id}",
                    "title": f"{label}结果",
                },
            }
        ],
        "agent_context": {
            "text": f"用户通过{label}选中了 {len(pois)} 个 POI，可作为当前规划候选目标。",
            "poi_ids": poi_ids,
        },
    }


def validate_geometry(query_type: str, geometry: dict[str, Any]) -> None:
    geometry_type = geometry.get("type")
    if not geometry_type or "coordinates" not in geometry:
        raise SpatialQueryError("geometry must be a valid GeoJSON geometry")
    expected_types = EXPECTED_GEOMETRY_TYPES.get(query_type)
    if expected_types and geometry_type not in expected_types:
        expected = ", ".join(sorted(expected_types))
        raise SpatialQueryError(f"{query_type} requires geometry type: {expected}")


def execute_spatial_query(
    db: Session,
    *,
    query_type: str,
    geometry_json: str,
    city: str | None,
    category_codes: list[str],
    limit: int,
) -> list[Any]:
    filters = ["p.is_active = true"]
    params: dict[str, Any] = {
        "geometry_json": geometry_json,
        "range_meters": DEFAULT_RANGE_METERS,
        "limit": limit,
    }

    if city:
        filters.append("p.city = :city")
        params["city"] = city

    if category_codes:
        filters.append("p.category_code in :category_codes")
        params["category_codes"] = tuple(category_codes)

    if query_type in {"point_radius", "line_buffer", "bezier_buffer"}:
        spatial_filter = "ST_DWithin(p.geom::geography, q.geom::geography, :range_meters)"
        distance_expr = "ST_Distance(p.geom::geography, q.geom::geography)"
        order_expr = "distance_m asc"
    elif query_type == "polygon_contains":
        spatial_filter = "ST_Intersects(p.geom, q.geom)"
        distance_expr = "null::numeric"
        order_expr = "p.popularity_score desc nulls last, p.name_zh"
    else:
        raise SpatialQueryError("unsupported query_type")

    stmt = text(
        f"""
        with q as (
            select ST_SetSRID(ST_GeomFromGeoJSON(:geometry_json), 4326) as geom
        )
        select
            p.id::text,
            p.category_code,
            p.name_zh,
            coalesce(sp.name_en, p.name_en) as name_en,
            p.longitude,
            p.latitude,
            p.address,
            p.tags,
            p.popularity_score,
            {distance_expr} as distance_m
        from public.pois p
        left join public.scenic_spot_profiles sp on sp.poi_id = p.id
        cross join q
        where {' and '.join(filters)}
          and {spatial_filter}
        order by {order_expr}
        limit :limit
        """
    )
    if category_codes:
        stmt = stmt.bindparams(bindparam("category_codes", expanding=True))

    return db.execute(stmt, params).mappings().all()


def map_spatial_poi(row: Any) -> dict[str, Any]:
    poi = map_poi_base(row)
    distance_m = row.get("distance_m")
    poi["distance_m"] = round(float(distance_m), 2) if distance_m is not None else None
    return poi


def save_spatial_query_record(
    db: Session,
    *,
    user: CurrentUser,
    query_id: str,
    query_type: str,
    geometry_json: str,
    radius_meters: float | None,
    buffer_meters: float | None,
    city: str | None,
    category_codes: list[str],
    rows: list[Any],
) -> None:
    ensure_user_profile(db, user)
    draw_row = db.execute(
        text(
            """
            insert into public.user_draw_features (
                user_id,
                query_type,
                geom,
                radius_meters,
                buffer_meters,
                properties
            )
            values (
                cast(:user_id as uuid),
                :query_type,
                ST_SetSRID(ST_GeomFromGeoJSON(:geometry_json), 4326),
                :radius_meters,
                :buffer_meters,
                cast(:properties as jsonb)
            )
            returning id::text
            """
        ),
        {
            "user_id": user.id,
            "query_type": query_type,
            "geometry_json": geometry_json,
            "radius_meters": radius_meters or DEFAULT_RANGE_METERS if query_type == "point_radius" else radius_meters,
            "buffer_meters": buffer_meters or DEFAULT_RANGE_METERS if query_type in {"line_buffer", "bezier_buffer"} else buffer_meters,
            "properties": json.dumps(
                {
                    "query_id": query_id,
                    "city": city,
                    "category_codes": category_codes,
                    "result_count": len(rows),
                },
                ensure_ascii=False,
            ),
        },
    ).mappings().first()
    draw_feature_id = draw_row["id"]

    for row in rows:
        db.execute(
            text(
                """
                insert into public.spatial_poi_query_results (
                    draw_feature_id,
                    poi_id,
                    distance_m,
                    relation_type
                )
                values (
                    cast(:draw_feature_id as uuid),
                    cast(:poi_id as uuid),
                    :distance_m,
                    :relation_type
                )
                on conflict (draw_feature_id, poi_id) do nothing
                """
            ),
            {
                "draw_feature_id": draw_feature_id,
                "poi_id": row["id"],
                "distance_m": row.get("distance_m"),
                "relation_type": query_type,
            },
        )
    db.commit()
