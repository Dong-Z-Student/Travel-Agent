from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.utils.coord_transform import gcj02_to_wgs84, wgs84_to_gcj02


AMAP_DIRECTION_BASE_URL = "https://restapi.amap.com/v3/direction"


class AmapRouteError(RuntimeError):
    pass


class AmapRouteClient:
    def __init__(self, *, timeout: float = 12.0) -> None:
        if not settings.amap_web_service_key:
            raise AmapRouteError("AMAP_WEB_SERVICE_KEY is not configured")
        self.timeout = timeout
        self.key = settings.amap_web_service_key

    def plan_segment(
        self,
        *,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str,
        city: str,
        strategy: str | None = None,
    ) -> dict[str, Any]:
        if mode == "transit":
            return self._request("transit/integrated", origin=origin, destination=destination, city=city, strategy=strategy)
        if mode == "driving":
            return self._request("driving", origin=origin, destination=destination, strategy=strategy)
        return self._request("walking", origin=origin, destination=destination)

    def _request(
        self,
        path: str,
        *,
        origin: tuple[float, float],
        destination: tuple[float, float],
        city: str | None = None,
        strategy: str | None = None,
    ) -> dict[str, Any]:
        origin_gcj = wgs84_to_gcj02(*origin)
        destination_gcj = wgs84_to_gcj02(*destination)
        params = {
            "key": self.key,
            "origin": format_coord(origin_gcj),
            "destination": format_coord(destination_gcj),
            "output": "json",
        }
        if city:
            params["city"] = city
        if strategy is not None and strategy != "":
            params["strategy"] = str(strategy)

        response = httpx.get(f"{AMAP_DIRECTION_BASE_URL}/{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "1":
            message = data.get("info") or data.get("infocode") or "Amap route request failed"
            raise AmapRouteError(str(message))
        return data


def format_coord(coord: tuple[float, float]) -> str:
    return f"{coord[0]:.6f},{coord[1]:.6f}"


def parse_polyline(polyline: str | None) -> list[list[float]]:
    if not polyline:
        return []
    coordinates: list[list[float]] = []
    for item in polyline.split(";"):
        parts = item.split(",")
        if len(parts) != 2:
            continue
        try:
            lon, lat = gcj02_to_wgs84(float(parts[0]), float(parts[1]))
        except ValueError:
            continue
        coordinates.append([lon, lat])
    return coordinates
