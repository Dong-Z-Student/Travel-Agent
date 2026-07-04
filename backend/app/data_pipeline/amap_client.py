from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.data_pipeline.clean_pois import CATEGORY_CONFIGS, CategoryConfig


class AmapClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class AmapSearchPage:
    category_code: str
    keyword: str
    page: int
    count: int
    pois: list[dict[str, Any]]


class AmapClient:
    def __init__(
        self,
        key: str | None = None,
        base_url: str = "https://restapi.amap.com/v3/place/text",
        timeout: float = 15.0,
        retries: int = 3,
        retry_interval: float = 1.0,
        delay_seconds: float = 0.25,
    ) -> None:
        self.key = key or settings.amap_web_service_key
        if not self.key:
            raise AmapClientError("AMAP_WEB_SERVICE_KEY is not configured")
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries
        self.retry_interval = retry_interval
        self.delay_seconds = delay_seconds

    def search_page(
        self,
        category: CategoryConfig,
        keyword: str,
        city: str,
        page: int,
        offset: int,
    ) -> AmapSearchPage:
        params = {
            "key": self.key,
            "keywords": keyword,
            "city": city,
            "citylimit": "true",
            "offset": offset,
            "page": page,
            "extensions": "all",
            "output": "JSON",
        }
        if category.amap_types:
            params["types"] = category.amap_types

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(self.base_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                if data.get("status") != "1":
                    info = data.get("info") or data.get("infocode") or "unknown amap error"
                    raise AmapClientError(f"Amap API error: {info}")

                pois = data.get("pois") or []
                count = int(data.get("count") or len(pois))
                time.sleep(self.delay_seconds)
                return AmapSearchPage(category.code, keyword, page, count, pois)
            except (httpx.HTTPError, ValueError, AmapClientError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.retry_interval * attempt)

        raise AmapClientError(f"Failed to fetch Amap page after {self.retries} attempts: {last_error}")

    def fetch_category(
        self,
        category_code: str,
        city: str = "武汉市",
        max_pages: int = 20,
        offset: int = 25,
    ) -> list[dict[str, Any]]:
        category = CATEGORY_CONFIGS[category_code]
        collected: list[dict[str, Any]] = []

        for keyword in category.keywords:
            for page in range(1, max_pages + 1):
                result = self.search_page(category, keyword, city, page, offset)
                if not result.pois:
                    break
                collected.extend(result.pois)
                if len(result.pois) < offset:
                    break

        return collected
