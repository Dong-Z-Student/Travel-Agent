from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.agent.map_command_guard import validate_map_commands


def build_map_commands(*, conversation_id: str, trip_state: dict[str, Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    candidate_poi_ids = list(dict.fromkeys(str(item) for item in trip_state.get("candidate_poi_ids") or [] if item))
    candidate_pois = _dedupe_pois(trip_state.get("candidate_pois") or [])

    if candidate_poi_ids:
        commands.append(
            {
                "type": "HIGHLIGHT_POIS",
                "payload": {
                    "poi_ids": candidate_poi_ids,
                    "pois": [poi for poi in candidate_pois if poi.get("id") in candidate_poi_ids],
                    "layer_id": f"agent-plan-pois-{conversation_id}",
                    "replace_existing": True,
                    "title": "Agent 推荐景点",
                },
            }
        )

    route_commands = []
    animation_commands = []
    for day in trip_state.get("day_plans") or []:
        route = day.get("route")
        route_id = day.get("route_id")
        if not route_id:
            continue
        payload: dict[str, Any] = {
            "route_id": route_id,
            "layer_id": f"agent-route-day-{day.get('day_index') or route_id}",
            "title": day.get("theme") or f"Day {day.get('day_index')} 路线",
        }
        if isinstance(route, dict):
            payload["route"] = _with_slow_animation(route)
        route_commands.append({"type": "ADD_ROUTE", "payload": payload})
        animation_commands.append({"type": "PLAY_ROUTE_ANIMATION", "payload": dict(payload)})

    commands.extend(route_commands)
    commands.extend(animation_commands)

    return validate_map_commands(commands)


def _dedupe_pois(pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for poi in pois:
        poi_id = str(poi.get("id") or "")
        if not poi_id or poi_id in seen:
            continue
        seen.add(poi_id)
        result.append(poi)
    return result


def _with_slow_animation(route: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(route)
    animation = dict(normalized.get("animation") or {})
    animation["speed"] = min(float(animation.get("speed") or 0.0025), 0.0025)
    animation.setdefault("loop", True)
    normalized["animation"] = animation
    return normalized
