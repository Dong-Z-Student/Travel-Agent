from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.tools import (
    GetNearbyHotelsArgs,
    GetNearbyMetroArgs,
    GetPoiDetailArgs,
    GetPopulationHeatmapSummaryArgs,
    GetWeatherArgs,
    PlanDayRouteArgs,
    SearchPoisArgs,
    get_nearby_hotels_tool,
    get_nearby_metro_tool,
    get_poi_detail_tool,
    get_population_heatmap_summary_tool,
    get_weather_tool,
    plan_day_route_tool,
    search_pois_tool,
)
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Agent tool wrappers.")
    parser.add_argument("--plan-route", action="store_true", help="Also call Amap-backed route planning.")
    parser.add_argument("--district", default="洪山区", help="Weather district to verify.")
    args = parser.parse_args()

    with SessionLocal() as db:
        pois = search_pois_tool(db, SearchPoisArgs(category_codes=["scenic_spot"], limit=3))
        poi_ids = [poi["id"] for poi in pois["pois"]]
        result = {
            "search_pois_count": pois["result_count"],
            "sample_poi_ids": poi_ids,
            "poi_detail_found": False,
            "nearby_metro_count": 0,
            "nearby_hotels_count": 0,
            "weather_cache_hit": None,
            "heatmap_summary": None,
            "route_id": None,
        }

        if poi_ids:
            detail = get_poi_detail_tool(db, GetPoiDetailArgs(poi_id=poi_ids[0]))
            result["poi_detail_found"] = detail["found"]
            result["nearby_metro_count"] = len(
                get_nearby_metro_tool(db, GetNearbyMetroArgs(poi_id=poi_ids[0], radius_meters=1200, limit=5))["nearby_metro"]
            )
            result["nearby_hotels_count"] = len(
                get_nearby_hotels_tool(db, GetNearbyHotelsArgs(center_poi_ids=[poi_ids[0]], radius_meters=2000, limit=5))["nearby_hotels"]
            )
            result["heatmap_summary"] = get_population_heatmap_summary_tool(db, GetPopulationHeatmapSummaryArgs(poi_ids=[poi_ids[0]]))

        weather = get_weather_tool(db, GetWeatherArgs(district=args.district, extensions="base"))
        result["weather_cache_hit"] = weather.get("cache_hit")

        if args.plan_route and len(poi_ids) >= 2:
            route = plan_day_route_tool(db, PlanDayRouteArgs(day_index=1, mode="walking", poi_ids=poi_ids[:2]))
            result["route_id"] = route["route_id"]

        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
