from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.route import RoutePlanRequest, RoutePoint
from app.services.amap_route_client import AmapRouteClient, AmapRouteError, parse_polyline


class RouteServiceError(RuntimeError):
    pass


def plan_route(db: Session, payload: RoutePlanRequest) -> dict[str, Any]:
    signature = build_route_signature(payload)
    cached = get_route_by_signature(db, signature)
    if cached:
        if payload.route_name:
            cached["route_name"] = payload.route_name
        cached["cache_hit"] = True
        return cached

    stops = [payload.origin, *payload.waypoints, payload.destination]
    if len(stops) < 2:
        raise RouteServiceError("route requires at least origin and destination")

    client = AmapRouteClient()
    segment_results = []
    all_coordinates: list[list[float]] = []
    total_distance = 0.0
    total_duration_seconds = 0.0

    for index in range(len(stops) - 1):
        start = stops[index]
        end = stops[index + 1]
        raw = client.plan_segment(
            origin=(start.longitude, start.latitude),
            destination=(end.longitude, end.latitude),
            mode=payload.route_mode,
            city=payload.city,
            strategy=payload.strategy,
        )
        segment = extract_segment(raw, payload.route_mode)
        segment_results.append({
            "index": index,
            "origin": point_to_dict(start),
            "destination": point_to_dict(end),
            "distance_m": segment["distance_m"],
            "duration_seconds": segment["duration_seconds"],
            "raw": raw,
        })
        total_distance += segment["distance_m"] or 0
        total_duration_seconds += segment["duration_seconds"] or 0
        all_coordinates = append_coordinates(all_coordinates, segment["coordinates"])

    if len(all_coordinates) < 2:
        raise RouteServiceError("Amap route result did not contain a valid polyline")

    geometry = {
        "type": "LineString",
        "coordinates": all_coordinates,
    }
    route_name = payload.route_name or build_route_name(stops)
    route_json = {
        "route_signature": signature,
        "city": payload.city,
        "request": payload.model_dump(),
        "segments": segment_results,
    }

    route_id = insert_route(
        db,
        route_name=route_name,
        route_mode=payload.route_mode,
        strategy=payload.strategy,
        route_signature=signature,
        geometry=geometry,
        distance_m=total_distance,
        duration_minutes=total_duration_seconds / 60 if total_duration_seconds else None,
        route_json=route_json,
        amap_route_raw={"segments": [segment["raw"] for segment in segment_results]},
    )
    insert_route_stops(db, route_id=route_id, stops=stops)
    db.commit()

    route = get_route_by_id(db, route_id)
    if not route:
        raise RouteServiceError("route was created but could not be loaded")
    route["cache_hit"] = False
    return route


def get_route_by_id(db: Session, route_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            select
                id::text,
                route_name,
                route_mode,
                strategy,
                distance_m,
                duration_minutes,
                ST_AsGeoJSON(geom) as geometry_json
            from public.routes
            where id = cast(:route_id as uuid)
            limit 1
            """
        ),
        {"route_id": route_id},
    ).mappings().first()
    if not row:
        return None

    stops = db.execute(
        text(
            """
            select
                id::text,
                poi_id::text,
                stop_order,
                name,
                longitude,
                latitude,
                arrival_time,
                stay_minutes,
                note
            from public.route_stops
            where route_id = cast(:route_id as uuid)
            order by stop_order
            """
        ),
        {"route_id": route_id},
    ).mappings().all()
    return map_route(row, stops)


def get_route_by_signature(db: Session, route_signature: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            select id::text
            from public.routes
            where route_signature = :route_signature
            order by created_at desc
            limit 1
            """
        ),
        {"route_signature": route_signature},
    ).mappings().first()
    return get_route_by_id(db, row["id"]) if row else None


def insert_route(
    db: Session,
    *,
    route_name: str,
    route_mode: str,
    strategy: str | None,
    route_signature: str,
    geometry: dict[str, Any],
    distance_m: float | None,
    duration_minutes: float | None,
    route_json: dict[str, Any],
    amap_route_raw: dict[str, Any],
) -> str:
    row = db.execute(
        text(
            """
            insert into public.routes (
                route_name,
                route_mode,
                strategy,
                route_signature,
                geom,
                distance_m,
                duration_minutes,
                route_json,
                amap_route_raw
            )
            values (
                :route_name,
                :route_mode,
                :strategy,
                :route_signature,
                ST_SetSRID(ST_GeomFromGeoJSON(:geometry_json), 4326),
                :distance_m,
                :duration_minutes,
                cast(:route_json as jsonb),
                cast(:amap_route_raw as jsonb)
            )
            returning id::text
            """
        ),
        {
            "route_name": route_name,
            "route_mode": route_mode,
            "strategy": strategy,
            "route_signature": route_signature,
            "geometry_json": json.dumps(geometry, ensure_ascii=False),
            "distance_m": distance_m,
            "duration_minutes": duration_minutes,
            "route_json": json.dumps(route_json, ensure_ascii=False),
            "amap_route_raw": json.dumps(amap_route_raw, ensure_ascii=False),
        },
    ).mappings().first()
    return row["id"]


def insert_route_stops(db: Session, *, route_id: str, stops: list[RoutePoint]) -> None:
    for index, stop in enumerate(stops):
        db.execute(
            text(
                """
                insert into public.route_stops (
                    route_id,
                    poi_id,
                    stop_order,
                    name,
                    longitude,
                    latitude,
                    stay_minutes,
                    note
                )
                values (
                    cast(:route_id as uuid),
                    cast(:poi_id as uuid),
                    :stop_order,
                    :name,
                    :longitude,
                    :latitude,
                    :stay_minutes,
                    :note
                )
                """
            ),
            {
                "route_id": route_id,
                "poi_id": stop.poi_id,
                "stop_order": index,
                "name": stop.name,
                "longitude": stop.longitude,
                "latitude": stop.latitude,
                "stay_minutes": stop.stay_minutes,
                "note": stop.note,
            },
        )


def extract_segment(raw: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "transit":
        transits = raw.get("route", {}).get("transits") or []
        if not transits:
            raise AmapRouteError("Amap transit route returned no transits")
        item = transits[0]
        return {
            "distance_m": parse_float(item.get("distance")),
            "duration_seconds": parse_float(item.get("duration")),
            "coordinates": extract_transit_coordinates(item),
        }

    paths = raw.get("route", {}).get("paths") or []
    if not paths:
        raise AmapRouteError("Amap route returned no paths")
    path = paths[0]
    coordinates = []
    for step in path.get("steps") or []:
        coordinates = append_coordinates(coordinates, parse_polyline(step.get("polyline")))
    return {
        "distance_m": parse_float(path.get("distance")),
        "duration_seconds": parse_float(path.get("duration")),
        "coordinates": coordinates,
    }


def extract_transit_coordinates(transit: dict[str, Any]) -> list[list[float]]:
    coordinates: list[list[float]] = []
    for segment in transit.get("segments") or []:
        walking = segment.get("walking") or {}
        for step in walking.get("steps") or []:
            coordinates = append_coordinates(coordinates, parse_polyline(step.get("polyline")))

        bus = segment.get("bus") or {}
        for busline in bus.get("buslines") or []:
            coordinates = append_coordinates(coordinates, parse_polyline(busline.get("polyline")))

        railway = segment.get("railway") or {}
        coordinates = append_coordinates(coordinates, parse_polyline(railway.get("polyline")))
    return coordinates


def append_coordinates(base: list[list[float]], incoming: list[list[float]]) -> list[list[float]]:
    if not incoming:
        return base
    if not base:
        return incoming.copy()
    result = base.copy()
    for coord in incoming:
        if result[-1] != coord:
            result.append(coord)
    return result


def build_route_signature(payload: RoutePlanRequest) -> str:
    stops = [payload.origin, *payload.waypoints, payload.destination]
    signature_payload = {
        "city": payload.city,
        "route_mode": payload.route_mode,
        "strategy": payload.strategy or "",
        "stops": [
            {
                "poi_id": stop.poi_id or "",
                "longitude": round(stop.longitude, 6),
                "latitude": round(stop.latitude, 6),
            }
            for stop in stops
        ],
    }
    raw = json.dumps(signature_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_route_name(stops: list[RoutePoint]) -> str:
    start = stops[0].name or "起点"
    end = stops[-1].name or "终点"
    return f"{start} 到 {end}"


def point_to_dict(point: RoutePoint) -> dict[str, Any]:
    return point.model_dump()


def map_route(row: Any, stops: list[Any]) -> dict[str, Any]:
    return {
        "route_id": row["id"],
        "route_name": row.get("route_name"),
        "route_mode": row.get("route_mode"),
        "strategy": row.get("strategy"),
        "cache_hit": False,
        "distance_m": parse_float(row.get("distance_m")),
        "duration_minutes": parse_float(row.get("duration_minutes")),
        "geometry": json.loads(row["geometry_json"]),
        "stops": [
            {
                "id": stop["id"],
                "poi_id": stop.get("poi_id"),
                "stop_order": stop["stop_order"],
                "name": stop.get("name"),
                "longitude": float(stop["longitude"]),
                "latitude": float(stop["latitude"]),
                "arrival_time": stop.get("arrival_time"),
                "stay_minutes": stop.get("stay_minutes"),
                "note": stop.get("note"),
            }
            for stop in stops
        ],
        "animation": {
            "speed": 0.006,
            "loop": True,
        },
    }


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
