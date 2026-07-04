from __future__ import annotations

import time
from typing import Any, Literal

import httpx

from app.core.config import settings


WeatherExtensions = Literal["base", "all"]
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


class AmapWeatherClientError(RuntimeError):
    pass


class AmapWeatherClient:
    def __init__(
        self,
        *,
        key: str | None = None,
        timeout: float = 12.0,
        retries: int = 3,
        retry_interval: float = 1.0,
    ) -> None:
        self.key = key or settings.amap_web_service_key
        if not self.key:
            raise AmapWeatherClientError("AMAP_WEB_SERVICE_KEY is not configured")
        self.timeout = timeout
        self.retries = retries
        self.retry_interval = retry_interval

    def get_weather(self, *, adcode: str, extensions: WeatherExtensions = "base") -> dict[str, Any]:
        params = {
            "key": self.key,
            "city": adcode,
            "extensions": extensions,
            "output": "JSON",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = httpx.get(AMAP_WEATHER_URL, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("status") != "1":
                    info = data.get("info") or data.get("infocode") or "unknown amap weather error"
                    raise AmapWeatherClientError(f"Amap weather API error: {info}")
                return data
            except (httpx.HTTPError, ValueError, AmapWeatherClientError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_interval * attempt)

        raise AmapWeatherClientError(f"Failed to fetch Amap weather after {self.retries} attempts: {last_error}")
