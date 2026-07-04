from datetime import date as Date
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.tools.common import WUHAN_CITY, ensure_wuhan_city
from app.schemas.weather import WeatherExtensions
from app.services.weather_service import get_weather


class GetWeatherArgs(BaseModel):
    city: str = Field(default=WUHAN_CITY)
    district: str | None = None
    adcode: str | None = None
    extensions: WeatherExtensions = "all"
    date: Date | None = None


def get_weather_tool(db: Session, args: GetWeatherArgs) -> dict[str, Any]:
    city = ensure_wuhan_city(args.city)
    return get_weather(
        db,
        city=city,
        district=args.district,
        adcode=args.adcode,
        extensions=args.extensions,
        target_date=args.date,
    )
