from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


DEFAULT_LIMIT = 500
MAX_LIMIT = 1000


def list_pois(
    db: Session,
    category_codes: list[str] | None = None,
    city: str | None = None,
    district: str | None = None,
    bbox: list[float] | None = None,
    keyword: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    filters = ["p.is_active = true"]
    params: dict[str, Any] = {}

    if category_codes:
        filters.append("p.category_code in :category_codes")
        params["category_codes"] = tuple(category_codes)

    if city:
        filters.append("p.city = :city")
        params["city"] = city

    if district:
        filters.append("p.district = :district")
        params["district"] = district

    if bbox:
        filters.append("p.longitude between :min_lon and :max_lon")
        filters.append("p.latitude between :min_lat and :max_lat")
        params.update({
            "min_lon": bbox[0],
            "min_lat": bbox[1],
            "max_lon": bbox[2],
            "max_lat": bbox[3],
        })

    if keyword:
        filters.append("(p.name_zh ilike :keyword or p.address ilike :keyword)")
        params["keyword"] = f"%{keyword}%"

    safe_limit = min(max(limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    params["limit"] = safe_limit

    stmt = text(
        f"""
        select
            p.id::text,
            p.category_code,
            p.name_zh,
            coalesce(sp.name_en, p.name_en) as name_en,
            p.longitude,
            p.latitude,
            p.district,
            p.address,
            p.tags,
            p.popularity_score
        from public.pois p
        left join public.scenic_spot_profiles sp on sp.poi_id = p.id
        where {' and '.join(filters)}
        order by p.category_code, p.popularity_score desc nulls last, p.name_zh
        limit :limit
        """
    )
    if category_codes:
        stmt = stmt.bindparams(bindparam("category_codes", expanding=True))

    rows = db.execute(stmt, params).mappings().all()
    return [map_poi_base(row) for row in rows]


def get_poi_detail(db: Session, poi_id: str) -> dict[str, Any] | None:
    base_row = db.execute(
        text(
            """
            select
                p.id::text,
                p.category_code,
                p.name_zh,
                coalesce(sp.name_en, p.name_en) as name_en,
                p.longitude,
                p.latitude,
                p.district,
                p.address,
                p.tags,
                p.popularity_score,
                sp.short_intro_zh,
                sp.short_intro_en,
                sp.full_description_zh,
                sp.full_description_en,
                sp.recommended_duration_minutes,
                sp.opening_hours,
                sp.ticket_info,
                sp.suitable_time,
                sp.suitable_for,
                sp.manual_tags
            from public.pois p
            left join public.scenic_spot_profiles sp on sp.poi_id = p.id
            where p.id = cast(:poi_id as uuid)
              and p.is_active = true
            limit 1
            """
        ),
        {"poi_id": poi_id},
    ).mappings().first()

    if not base_row:
        return None

    images = db.execute(
        text(
            """
            select image_url, caption_zh
            from public.poi_images
            where poi_id = cast(:poi_id as uuid)
            order by sort_order, created_at
            """
        ),
        {"poi_id": poi_id},
    ).mappings().all()

    detail = map_poi_base(base_row)
    detail["profile"] = {
        "short_intro_zh": base_row.get("short_intro_zh") or "",
        "short_intro_en": base_row.get("short_intro_en"),
        "full_description_zh": base_row.get("full_description_zh"),
        "full_description_en": base_row.get("full_description_en"),
        "recommended_duration_minutes": base_row.get("recommended_duration_minutes"),
        "opening_hours": base_row.get("opening_hours"),
        "ticket_info": base_row.get("ticket_info"),
        "suitable_time": base_row.get("suitable_time"),
        "suitable_for": list(base_row.get("suitable_for") or []),
        "manual_tags": list(base_row.get("manual_tags") or []),
    }
    detail["images"] = [
        {
            "url": row["image_url"],
            "image_url": row["image_url"],
            "caption": row.get("caption_zh"),
            "caption_zh": row.get("caption_zh"),
        }
        for row in images
    ]
    return detail


def map_poi_base(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "category_code": row["category_code"],
        "name_zh": row["name_zh"],
        "name_en": row.get("name_en"),
        "longitude": float(row["longitude"]),
        "latitude": float(row["latitude"]),
        "district": row.get("district"),
        "address": row.get("address"),
        "tags": list(row.get("tags") or []),
        "popularity_score": decimal_to_float(row.get("popularity_score")),
    }


def decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value
