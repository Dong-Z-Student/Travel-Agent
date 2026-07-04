from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.tools.common import WUHAN_CITY, ensure_wuhan_city
from app.schemas.poi import PoiBase, PoiDetail
from app.services.poi_service import get_poi_detail, list_pois


class SearchPoisArgs(BaseModel):
    category_codes: list[str] = Field(default_factory=lambda: ["scenic_spot"])
    keyword: str | None = None
    district: str | None = None
    city: str = WUHAN_CITY
    limit: int = Field(default=20, ge=1, le=50)


class SearchPoisResult(BaseModel):
    city: str
    district: str | None = None
    pois: list[PoiBase] = Field(default_factory=list)
    result_count: int


class GetPoiDetailArgs(BaseModel):
    poi_id: str


class GetPoiDetailResult(BaseModel):
    poi: PoiDetail | None = None
    found: bool


def search_pois_tool(db: Session, args: SearchPoisArgs) -> dict[str, Any]:
    city = ensure_wuhan_city(args.city)
    pois = list_pois(
        db,
        category_codes=args.category_codes,
        city=city,
        district=args.district,
        keyword=args.keyword,
        limit=args.limit,
    )
    result = SearchPoisResult(
        city=city,
        district=args.district,
        pois=[PoiBase(**poi) for poi in pois],
        result_count=len(pois),
    )
    return result.model_dump()


def get_poi_detail_tool(db: Session, args: GetPoiDetailArgs) -> dict[str, Any]:
    detail = get_poi_detail(db, args.poi_id)
    result = GetPoiDetailResult(
        poi=PoiDetail(**detail) if detail else None,
        found=detail is not None,
    )
    return result.model_dump()
