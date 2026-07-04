from __future__ import annotations

from typing import Any


WUHAN_CITY = "武汉市"
MAX_NEARBY_RADIUS_METERS = 3000


class AgentToolError(RuntimeError):
    pass


def ensure_wuhan_city(city: str | None) -> str:
    city_name = city or WUHAN_CITY
    if city_name != WUHAN_CITY:
        raise AgentToolError("Agent tools are limited to Wuhan city")
    return city_name


def summarize_list(items: list[Any], max_items: int = 5) -> list[Any]:
    return items[:max_items]
