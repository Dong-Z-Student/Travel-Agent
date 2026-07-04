from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.poi import PoiDetail, PoiListResponse
from app.services.poi_service import get_poi_detail as get_poi_detail_service
from app.services.poi_service import list_pois as list_pois_service

router = APIRouter()


@router.get("", response_model=PoiListResponse)
def list_pois(
    request: Request,
    city: str | None = None,
    keyword: str | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> PoiListResponse:
    pois = list_pois_service(
        db,
        category_codes=parse_multi_query(request, "category_codes"),
        city=city,
        bbox=parse_float_list_query(request, "bbox", expected_length=4),
        keyword=keyword,
        limit=limit,
    )
    return PoiListResponse(pois=pois)


@router.get("/{poi_id}/detail", response_model=PoiDetail)
def get_poi_detail(poi_id: str, db: Session = Depends(get_db)) -> PoiDetail:
    detail = get_poi_detail_service(db, poi_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    return PoiDetail(**detail)


def parse_multi_query(request: Request, key: str) -> list[str] | None:
    values = []
    for query_key in (key, f"{key}[]"):
        values.extend(request.query_params.getlist(query_key))
    result: list[str] = []
    for value in values:
        result.extend(item.strip() for item in value.split(",") if item.strip())
    return result or None


def parse_float_list_query(request: Request, key: str, expected_length: int) -> list[float] | None:
    raw_values = []
    for query_key in (key, f"{key}[]"):
        raw_values.extend(request.query_params.getlist(query_key))
    if not raw_values:
        return None
    values: list[float] = []
    for raw_value in raw_values:
        for item in raw_value.split(","):
            item = item.strip()
            if item:
                try:
                    values.append(float(item))
                except ValueError as exc:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} must contain numbers") from exc
    if len(values) != expected_length:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} must contain {expected_length} numbers")
    return values
