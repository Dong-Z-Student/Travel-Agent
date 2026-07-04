from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.weather import WeatherExtensions, WeatherResponse
from app.services.weather_service import WeatherServiceError
from app.services.weather_service import get_weather as get_weather_service

router = APIRouter()


@router.get("", response_model=WeatherResponse)
def get_weather(
    city: str = Query(default="武汉市"),
    district: str | None = Query(default=None),
    adcode: str | None = Query(default=None),
    extensions: WeatherExtensions = Query(default="base"),
    date_: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> WeatherResponse:
    try:
        weather = get_weather_service(
            db,
            city=city,
            district=district,
            adcode=adcode,
            extensions=extensions,
            target_date=date_,
        )
    except WeatherServiceError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return WeatherResponse(**weather)
