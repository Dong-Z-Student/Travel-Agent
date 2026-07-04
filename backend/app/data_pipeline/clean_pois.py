from dataclasses import dataclass
from typing import Any

from app.utils.coord_transform import gcj02_to_wgs84, parse_amap_location


@dataclass(frozen=True)
class CategoryConfig:
    code: str
    keywords: tuple[str, ...]
    amap_types: str | None = None


@dataclass(frozen=True)
class CleanPoi:
    category_code: str
    name_zh: str
    name_en: str | None
    amap_poi_id: str | None
    amap_type: str | None
    amap_type_code: str | None
    address: str | None
    district: str | None
    city: str
    province: str
    longitude: float
    latitude: float
    amap_longitude: float
    amap_latitude: float
    rating: float | None
    popularity_score: float | None
    tags: list[str]
    source_raw: dict[str, Any]


CATEGORY_CONFIGS: dict[str, CategoryConfig] = {
    "scenic_spot": CategoryConfig(code="scenic_spot", keywords=("景点",), amap_types="110000|110100|110200|110300|110400|110500"),
    "hotel": CategoryConfig(code="hotel", keywords=("酒店",), amap_types="100000|100100|100101|100102|100103|100104|100105"),
    "metro_station": CategoryConfig(code="metro_station", keywords=("地铁站",), amap_types="150500"),
}


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if item)
    value = str(value).strip()
    return value or None


def parse_rating(raw: dict[str, Any]) -> float | None:
    biz_ext = raw.get("biz_ext") or {}
    rating = biz_ext.get("rating") if isinstance(biz_ext, dict) else None
    if rating in (None, "", "[]"):
        return None
    try:
        return float(rating)
    except (TypeError, ValueError):
        return None


def popularity_from_rating(rating: float | None) -> float | None:
    if rating is None:
        return None
    return round(max(0.0, min(rating / 5.0, 1.0)), 3)


def tags_from_raw(raw: dict[str, Any], category_code: str) -> list[str]:
    tags = [category_code]
    amap_type = normalize_text(raw.get("type"))
    if amap_type:
        tags.extend(part.strip() for part in amap_type.split(";") if part.strip())
    return list(dict.fromkeys(tags))


def clean_amap_poi(raw: dict[str, Any], category_code: str, fallback_city: str = "武汉市") -> CleanPoi | None:
    location = parse_amap_location(normalize_text(raw.get("location")))
    if location is None:
        return None

    amap_lon, amap_lat = location
    lon, lat = gcj02_to_wgs84(amap_lon, amap_lat)
    rating = parse_rating(raw)

    return CleanPoi(
        category_code=category_code,
        name_zh=normalize_text(raw.get("name")) or "未命名POI",
        name_en=None,
        amap_poi_id=normalize_text(raw.get("id")),
        amap_type=normalize_text(raw.get("type")),
        amap_type_code=normalize_text(raw.get("typecode")),
        address=normalize_text(raw.get("address")),
        district=normalize_text(raw.get("adname")),
        city=normalize_text(raw.get("cityname")) or fallback_city,
        province=normalize_text(raw.get("pname")) or "湖北省",
        longitude=lon,
        latitude=lat,
        amap_longitude=amap_lon,
        amap_latitude=amap_lat,
        rating=rating,
        popularity_score=popularity_from_rating(rating),
        tags=tags_from_raw(raw, category_code),
        source_raw=raw,
    )


def dedupe_clean_pois(pois: list[CleanPoi]) -> list[CleanPoi]:
    seen: set[str] = set()
    result: list[CleanPoi] = []

    for poi in pois:
        key = poi.amap_poi_id or f"{poi.category_code}:{poi.name_zh}:{poi.amap_longitude:.6f},{poi.amap_latitude:.6f}"
        if key in seen:
            continue
        seen.add(key)
        result.append(poi)

    return result
