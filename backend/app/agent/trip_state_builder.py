from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.agent.schemas import AgentDecision, IntentSlots


MAX_DAYS = 7


def build_or_update_day_plans(
    *,
    existing_day_plans: list[dict[str, Any]],
    slots: IntentSlots,
    decision: AgentDecision,
    candidate_poi_ids: list[str],
) -> list[dict[str, Any]]:
    if decision.action != "continue" or slots.intent not in {"plan_trip", "modify_trip", "spatial_query_followup"}:
        return existing_day_plans

    days = slots.days or len(existing_day_plans)
    if not days:
        return existing_day_plans

    days = min(days, MAX_DAYS)
    target_day_index = slots.target_day_index if slots.intent == "modify_trip" else None
    if existing_day_plans and target_day_index:
        return [
            build_day_plan(index=day.get("day_index") or idx + 1, slots=slots, candidate_poi_ids=candidate_poi_ids, existing=day)
            if (day.get("day_index") or idx + 1) == target_day_index
            else day
            for idx, day in enumerate(existing_day_plans)
        ]

    if existing_day_plans and len(existing_day_plans) == days and slots.intent != "plan_trip":
        return existing_day_plans

    distributed = distribute_pois(candidate_poi_ids, days)
    return [
        build_day_plan(index=index, slots=slots, candidate_poi_ids=distributed[index - 1] if index - 1 < len(distributed) else [])
        for index in range(1, days + 1)
    ]


def build_day_plan(
    *,
    index: int,
    slots: IntentSlots,
    candidate_poi_ids: list[str],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = dict(existing or {})
    date_value = get_day_date(slots, index) or existing.get("date")
    poi_ids = candidate_poi_ids or list(existing.get("poi_ids") or [])
    notes = list(existing.get("notes") or [])
    if not poi_ids:
        notes.append("当前阶段已建立 day_plan 结构，但还未在 2.6 阶段虚构 POI；后续规划阶段会用真实工具填充。")
    if slots.intent == "modify_trip" and slots.modification_target:
        notes.append(f"本轮修改目标：{slots.modification_target}")

    return {
        "day_index": index,
        "date": date_value,
        "theme": build_day_theme(index, slots, poi_ids, existing),
        "districts": list(existing.get("districts") or []),
        "poi_ids": poi_ids,
        "hotel_id": existing.get("hotel_id"),
        "route_id": existing.get("route_id"),
        "weather_summary": dict(existing.get("weather_summary") or {}),
        "notes": list(dict.fromkeys(notes)),
        "status": "structured_pending_tools",
    }


def distribute_pois(poi_ids: list[str], days: int) -> list[list[str]]:
    result = [[] for _ in range(days)]
    for index, poi_id in enumerate(poi_ids):
        result[index % days].append(poi_id)
    return result


def get_day_date(slots: IntentSlots, day_index: int) -> str | None:
    if len(slots.travel_dates) >= day_index:
        return slots.travel_dates[day_index - 1]
    if slots.date_range.start:
        try:
            start = date.fromisoformat(slots.date_range.start)
        except ValueError:
            return None
        return (start + timedelta(days=day_index - 1)).isoformat()
    return None


def build_day_theme(index: int, slots: IntentSlots, poi_ids: list[str], existing: dict[str, Any]) -> str:
    if existing.get("theme") and existing.get("status") != "structured_pending_tools":
        return existing["theme"]
    if slots.themes:
        return f"Day {index}：" + "、".join(slots.themes[:2])
    if poi_ids:
        return f"Day {index}：围绕候选 POI 的武汉行程"
    return f"Day {index}：武汉行程待规划"
