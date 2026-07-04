from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


WeatherExtensions = Literal["base", "all"]


class CurrentWeather(BaseModel):
    weather: str | None = None
    temperature: float | None = None
    wind_direction: str | None = None
    wind_power: str | None = None
    humidity: float | None = None


class ForecastWeather(BaseModel):
    date: date
    day_weather: str | None = None
    night_weather: str | None = None
    day_temp: float | None = None
    night_temp: float | None = None
    day_wind: str | None = None
    night_wind: str | None = None
    day_power: str | None = None
    night_power: str | None = None


class WeatherResponse(BaseModel):
    city: str = "武汉市"
    district: str | None = None
    adcode: str
    report_time: str | None = None
    current: CurrentWeather | None = None
    forecast: list[ForecastWeather] = Field(default_factory=list)
    forecast_available: bool = True
    cache_hit: bool = False
    warnings: list[str] = Field(default_factory=list)
