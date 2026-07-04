from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analysis import PopulationHeatmapResponse
from app.services.analysis_service import get_population_heatmap as get_population_heatmap_service

router = APIRouter()


@router.get("/population-heatmap", response_model=PopulationHeatmapResponse)
def get_population_heatmap(request: Request, db: Session = Depends(get_db)) -> PopulationHeatmapResponse:
    points = get_population_heatmap_service(db, bbox=parse_float_list_query(request, "bbox", expected_length=4))
    return PopulationHeatmapResponse(points=points)


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
