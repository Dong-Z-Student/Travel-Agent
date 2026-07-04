from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.route import RoutePlanRequest, RouteResponse
from app.services.amap_route_client import AmapRouteError
from app.services.route_service import RouteServiceError
from app.services.route_service import get_route_by_id as get_route_by_id_service
from app.services.route_service import plan_route as plan_route_service

router = APIRouter()


@router.get("/{route_id}", response_model=RouteResponse)
def get_route(route_id: str, db: Session = Depends(get_db)) -> RouteResponse:
    route = get_route_by_id_service(db, route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return RouteResponse(**route)


@router.post("/plan", response_model=RouteResponse)
def plan_route(payload: RoutePlanRequest, db: Session = Depends(get_db)) -> RouteResponse:
    try:
        route = plan_route_service(db, payload)
    except (AmapRouteError, RouteServiceError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return RouteResponse(**route)
