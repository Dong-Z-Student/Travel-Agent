from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_optional_current_user
from app.db.session import get_db
from app.schemas.spatial_query import SpatialQueryRequest, SpatialQueryResponse
from app.services.spatial_query_service import SpatialQueryError
from app.services.spatial_query_service import query_pois_by_geometry as query_pois_by_geometry_service

router = APIRouter()


@router.post("/pois", response_model=SpatialQueryResponse)
def query_pois(
    payload: SpatialQueryRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
) -> SpatialQueryResponse:
    query_id = payload.query_id or f"query_{uuid4().hex}"
    try:
        result = query_pois_by_geometry_service(
            db,
            query_id=query_id,
            query_type=payload.query_type,
            geometry=payload.geometry,
            city=payload.city,
            category_codes=payload.category_codes,
            limit=payload.limit,
            radius_meters=payload.radius_meters,
            buffer_meters=payload.buffer_meters,
            user=current_user,
        )
    except SpatialQueryError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return SpatialQueryResponse(**result)
