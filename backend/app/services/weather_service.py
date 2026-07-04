from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.data_pipeline.amap_weather_client import AmapWeatherClient, AmapWeatherClientError


WUHAN_CITY = "武汉市"
WUHAN_ADCODE = "420100"
BASE_CACHE_TTL = timedelta(minutes=30)
FORECAST_CACHE_TTL = timedelta(hours=2)


class WeatherServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_weather(
    db: Session,
    *,
    city: str = WUHAN_CITY,
    district: str | None = None,
    adcode: str | None = None,
    extensions: str = "base",
    target_date: date | None = None,
) -> dict[str, Any]:
    if extensions not in {"base", "all"}:
        raise WeatherServiceError("extensions must be 'base' or 'all'", status_code=422)

    resolved = resolve_adcode(db, city=city, district=district, adcode=adcode)
    cache_forecast_date = target_date if extensions == "all" else None
    cached = get_cached_weather(
        db,
        adcode=resolved["adcode"],
        extensions=extensions,
        forecast_date=cache_forecast_date,
    )
    if cached:
        cached["cache_hit"] = True
        return cached

    try:
        raw = AmapWeatherClient().get_weather(adcode=resolved["adcode"], extensions=extensions)  # type: ignore[arg-type]
    except AmapWeatherClientError as exc:
        raise WeatherServiceError(str(exc), status_code=502) from exc

    normalized = normalize_weather(
        raw,
        city=resolved["city"],
        district=resolved["district"],
        adcode=resolved["adcode"],
        extensions=extensions,
        target_date=target_date,
    )
    insert_weather_cache(
        db,
        city=resolved["city"],
        district=resolved["district"],
        adcode=resolved["adcode"],
        extensions=extensions,
        forecast_date=cache_forecast_date,
        raw=raw,
        normalized=normalized,
        report_time=normalized.get("report_time"),
        expire_at=datetime.now(timezone.utc) + (BASE_CACHE_TTL if extensions == "base" else FORECAST_CACHE_TTL),
    )
    db.commit()
    normalized["cache_hit"] = False
    return normalized


def resolve_adcode(db: Session, *, city: str, district: str | None, adcode: str | None) -> dict[str, str | None]:
    city_name = city or WUHAN_CITY
    if adcode:
        row = db.execute(
            text(
                """
                select city, district, adcode
                from public.district_adcodes
                where adcode = :adcode
                limit 1
                """
            ),
            {"adcode": adcode},
        ).mappings().first()
        if row:
            return {"city": row["city"], "district": row["district"], "adcode": row["adcode"]}
        if city_name == WUHAN_CITY and adcode == WUHAN_ADCODE:
            return {"city": WUHAN_CITY, "district": None, "adcode": WUHAN_ADCODE}
        return {"city": city_name, "district": district, "adcode": adcode}

    if not district:
        raise WeatherServiceError("district or adcode is required", status_code=422)

    row = db.execute(
        text(
            """
            select city, district, adcode
            from public.district_adcodes
            where city = :city and district = :district
            limit 1
            """
        ),
        {"city": city_name, "district": district},
    ).mappings().first()
    if not row:
        raise WeatherServiceError(f"Unknown district for weather query: {district}", status_code=422)
    return {"city": row["city"], "district": row["district"], "adcode": row["adcode"]}


def get_cached_weather(db: Session, *, adcode: str, extensions: str, forecast_date: date | None) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            select normalized_json
            from public.weather_cache
            where adcode = :adcode
              and extensions = :extensions
              and forecast_date is not distinct from :forecast_date
              and expire_at > now()
            order by created_at desc
            limit 1
            """
        ),
        {"adcode": adcode, "extensions": extensions, "forecast_date": forecast_date},
    ).mappings().first()
    return dict(row["normalized_json"]) if row else None


def insert_weather_cache(
    db: Session,
    *,
    city: str,
    district: str | None,
    adcode: str,
    extensions: str,
    forecast_date: date | None,
    raw: dict[str, Any],
    normalized: dict[str, Any],
    report_time: str | None,
    expire_at: datetime,
) -> None:
    db.execute(
        text(
            """
            insert into public.weather_cache (
                city,
                district,
                adcode,
                extensions,
                forecast_date,
                response_json,
                normalized_json,
                report_time,
                expire_at
            )
            values (
                :city,
                :district,
                :adcode,
                :extensions,
                :forecast_date,
                cast(:response_json as jsonb),
                cast(:normalized_json as jsonb),
                :report_time,
                :expire_at
            )
            """
        ),
        {
            "city": city,
            "district": district,
            "adcode": adcode,
            "extensions": extensions,
            "forecast_date": forecast_date,
            "response_json": json.dumps(raw, ensure_ascii=False),
            "normalized_json": json.dumps(normalized, ensure_ascii=False),
            "report_time": report_time,
            "expire_at": expire_at,
        },
    )


def normalize_weather(
    raw: dict[str, Any],
    *,
    city: str,
    district: str | None,
    adcode: str,
    extensions: str,
    target_date: date | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    normalized: dict[str, Any] = {
        "city": city,
        "district": district,
        "adcode": adcode,
        "report_time": None,
        "current": None,
        "forecast": [],
        "forecast_available": True,
        "cache_hit": False,
        "warnings": warnings,
    }

    if extensions == "base":
        live = first_item(raw.get("lives"))
        if not live:
            raise WeatherServiceError("Amap weather response does not contain current weather", status_code=502)
        normalized["report_time"] = live.get("reporttime")
        normalized["current"] = {
            "weather": live.get("weather"),
            "temperature": parse_float(live.get("temperature")),
            "wind_direction": live.get("winddirection"),
            "wind_power": live.get("windpower"),
            "humidity": parse_float(live.get("humidity")),
        }
        return normalized

    forecast = first_item(raw.get("forecasts"))
    if not forecast:
        raise WeatherServiceError("Amap weather response does not contain forecast weather", status_code=502)

    normalized["report_time"] = forecast.get("reporttime")
    casts = forecast.get("casts") or []
    if target_date:
        target = target_date.isoformat()
        casts = [item for item in casts if item.get("date") == target]
        if not casts:
            normalized["forecast_available"] = False
            warnings.append(f"No Amap forecast is available for {target}")

    normalized["forecast"] = [normalize_forecast_item(item) for item in casts]
    return normalized


def normalize_forecast_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": item.get("date"),
        "day_weather": item.get("dayweather"),
        "night_weather": item.get("nightweather"),
        "day_temp": parse_float(item.get("daytemp")),
        "night_temp": parse_float(item.get("nighttemp")),
        "day_wind": item.get("daywind"),
        "night_wind": item.get("nightwind"),
        "day_power": item.get("daypower"),
        "night_power": item.get("nightpower"),
    }


def first_item(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list) and value:
        item = value[0]
        return item if isinstance(item, dict) else None
    return None


def parse_float(value: Any) -> float | None:
    if value in (None, "", "暂无"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
