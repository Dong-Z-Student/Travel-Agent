from __future__ import annotations

import json
import random
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.agent.memory_manager import load_context
from app.agent.model_client import AgentModelCallError, AgentModelClient, AgentModelConfigError
from app.agent.preference_manager import (
    extract_explicit_long_term_preferences,
    extract_temporary_preferences,
    is_long_term_preference,
    save_explicit_preferences,
)
from app.agent.prompts import FINAL_REPLY_PROMPT, INTENT_EXTRACTION_PROMPT
from app.agent.response_builder import build_map_commands
from app.agent.schemas import AgentDecision, AgentLoadedContext, IntentSlots, ToolTraceItem
from app.agent.state_manager import normalize_conversation_id, resolve_owned_conversation_id
from app.agent.tools.hotel_metro_tools import (
    GetNearbyHotelsArgs,
    GetNearbyMetroArgs,
    get_nearby_hotels_tool,
    get_nearby_metro_tool,
)
from app.agent.tools.poi_tools import GetPoiDetailArgs, SearchPoisArgs, get_poi_detail_tool, search_pois_tool
from app.agent.tools.route_tools import PlanDayRouteArgs, plan_day_route_tool
from app.agent.tools.weather_tools import GetWeatherArgs, get_weather_tool
from app.agent.trip_state_builder import build_or_update_day_plans
from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest
from app.schemas.route import RouteMode


PLAN_INTENTS = {"plan_trip", "modify_trip", "spatial_query_followup"}


class TravelAgentOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, payload: AgentChatRequest, user: CurrentUser | None = None) -> dict[str, Any]:
        conversation_id = normalize_conversation_id(payload.conversation_id)
        if user:
            conversation_id = resolve_owned_conversation_id(self.db, conversation_id=conversation_id, user=user)

        context = load_context(self.db, conversation_id=conversation_id, payload=payload, user=user)
        intent_slots, model_trace = self.extract_intent_and_slots(payload, context)
        decision = self.decide_clarify_or_plan(intent_slots, context)
        tool_data, tool_trace = self.collect_tool_data(payload, intent_slots, decision, context)
        ranked_candidates = self.rank_candidates(context, tool_data)
        saved_preferences, preference_trace = self.save_explicit_long_term_preferences(payload, intent_slots, user)
        trip_state = self.build_trip_state(
            payload=payload,
            context=context,
            intent_slots=intent_slots,
            decision=decision,
            ranked_candidates=ranked_candidates,
            saved_preferences=saved_preferences,
            tool_data=tool_data,
        )
        self.build_day_plans(trip_state, intent_slots, decision)
        route_trace = self.plan_day_routes(trip_state, intent_slots, decision, conversation_id)
        return self.build_response(
            conversation_id=conversation_id,
            payload=payload,
            context=context,
            intent_slots=intent_slots,
            decision=decision,
            trip_state=trip_state,
            tool_trace=[model_trace, preference_trace, *tool_trace, *route_trace],
        )

    def extract_intent_and_slots(self, payload: AgentChatRequest, context: AgentLoadedContext) -> tuple[IntentSlots, dict[str, Any]]:
        prompt_body = INTENT_EXTRACTION_PROMPT.format(
            context_summary=context.context_summary,
            user_preferences=context.preferences,
            spatial_context=context.spatial_context,
            message=payload.message,
        )
        prompt = (
            f"系统当前日期（Asia/Shanghai）：{current_local_date().isoformat()}\n"
            "解析今天、明天、后天、大后天、下周等相对日期时，必须以这个系统当前日期为准。\n\n"
            f"{prompt_body}"
        )
        try:
            result = AgentModelClient().invoke_json(prompt, IntentSlots, model_role="fast")
            slots = post_process_intent(IntentSlots.model_validate(result.parsed), payload)
            return slots, ToolTraceItem(
                tool="extract_intent_and_slots",
                status="success",
                summary=f"{result.model} 输出已通过 Pydantic 校验，attempts={result.attempts}",
            ).model_dump()
        except (AgentModelConfigError, AgentModelCallError) as exc:
            return fallback_intent(payload), ToolTraceItem(
                tool="extract_intent_and_slots",
                status="fallback",
                summary=f"模型抽取失败，已使用规则降级：{exc}",
            ).model_dump()

    def decide_clarify_or_plan(self, slots: IntentSlots, context: AgentLoadedContext) -> AgentDecision:
        if slots.intent == "smalltalk":
            return AgentDecision(action="smalltalk", reason="用户是普通闲聊或问候。")

        if slots.intent == "plan_trip" and not slots.days and not context.trip_state.get("days"):
            return AgentDecision(
                action="clarify",
                reason="完整行程规划缺少游玩天数。",
                clarifying_questions=["你计划在武汉玩几天？"],
            )

        warnings: list[str] = []
        if slots.intent in PLAN_INTENTS and not slots.travel_dates and not slots.date_range.start:
            warnings.append("你还没有提供明确出行日期，本轮先按无日期行程规划；天气只作为近期参考。")

        if context.spatial_context.get("poi_ids"):
            warnings.append("已收到前端空间查询候选 POI，本轮会优先围绕这些地点继续规划。")

        return AgentDecision(action="continue", reason="信息足够进入当前阶段 Orchestrator 主流程。", warnings=warnings)

    def collect_tool_data(
        self,
        payload: AgentChatRequest,
        slots: IntentSlots,
        decision: AgentDecision,
        context: AgentLoadedContext,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if decision.action in {"clarify", "smalltalk"}:
            return {}, [ToolTraceItem(tool="collect_tool_data", status="skipped", summary="澄清或闲聊轮次不调用业务工具。").model_dump()]

        if is_nearby_support_query(payload.message):
            return self.collect_nearby_support_data(slots, context)

        if slots.intent not in PLAN_INTENTS:
            if slots.intent == "weather_question":
                return self.collect_weather_data(slots)
            return {}, [ToolTraceItem(tool="collect_tool_data", status="skipped", summary="当前意图不需要生成候选 POI。").model_dump()]

        if context.trip_state.get("candidate_pois") and not slots.days and slots.travel_dates:
            pois = list(context.trip_state.get("candidate_pois") or [])
            return {"candidate_pois": pois}, [
                ToolTraceItem(
                    tool="reuse_trip_state_pois",
                    status="success",
                    summary=f"本轮是日期补充，复用上一轮 {len(pois)} 个候选 POI。",
                ).model_dump()
            ]

        poi_ids = list(dict.fromkeys(str(item) for item in context.spatial_context.get("poi_ids") or [] if item))
        if poi_ids:
            pois = self.load_pois_by_ids(poi_ids)
            return {"candidate_pois": pois}, [
                ToolTraceItem(
                    tool="get_poi_detail_tool",
                    status="success" if pois else "empty",
                    summary=f"从空间查询上下文读取 {len(pois)} 个候选 POI。",
                ).model_dump()
            ]

        days = slots.days or context.trip_state.get("days") or 1
        pool_limit = min(max(days * 5, 12), 35)
        selected_limit = min(max(days * 3, 4), 28)
        try:
            result = search_pois_tool(
                self.db,
                SearchPoisArgs(category_codes=["scenic_spot"], city="武汉市", limit=pool_limit),
            )
            base_pois = list(result.get("pois") or [])
            sampled = sample_candidate_pois(base_pois, limit=selected_limit)
            pois = self.load_pois_by_ids([str(poi.get("id")) for poi in sampled if poi.get("id")]) or sampled
            pois = diversify_candidate_pois(pois, days=days)
            return {"candidate_pois": pois}, [
                ToolTraceItem(
                    tool="search_pois_tool",
                    status="success",
                    summary=f"已从数据库检索 {len(pois)} 个武汉景点作为 Agent 候选点。",
                ).model_dump()
            ]
        except Exception as exc:  # noqa: BLE001
            return {}, [ToolTraceItem(tool="search_pois_tool", status="failed", summary=str(exc)).model_dump()]

    def save_explicit_long_term_preferences(
        self,
        payload: AgentChatRequest,
        slots: IntentSlots,
        user: CurrentUser | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        extracted = extract_explicit_long_term_preferences(payload.message, slots.explicit_long_term_preferences)
        saved = save_explicit_preferences(self.db, user, extracted)
        status = "success" if saved else "skipped"
        reason = f"已保存 {len(saved)} 条显式长期偏好。" if saved else "本轮没有可自动保存的显式长期偏好，或用户未登录。"
        return saved, ToolTraceItem(tool="save_explicit_long_term_preferences", status=status, summary=reason).model_dump()

    def collect_weather_data(self, slots: IntentSlots) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        try:
            result = get_weather_tool(
                self.db,
                GetWeatherArgs(
                    city="武汉市",
                    adcode="420100",
                    extensions="all",
                    date=None,
                ),
            )
            result = filter_weather_by_requested_dates(result, slots.travel_dates)
            return {"weather": result}, [
                ToolTraceItem(tool="get_weather_tool", status="success", summary="已获取武汉天气数据。").model_dump()
            ]
        except Exception as exc:  # noqa: BLE001
            return {}, [ToolTraceItem(tool="get_weather_tool", status="failed", summary=str(exc)).model_dump()]

    def collect_nearby_support_data(
        self,
        slots: IntentSlots,
        context: AgentLoadedContext,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        center_ids = select_support_center_poi_ids(context.trip_state)
        traces: list[dict[str, Any]] = []
        if not center_ids:
            result = search_pois_tool(
                self.db,
                SearchPoisArgs(category_codes=["scenic_spot"], city="武汉市", limit=6),
            )
            center_ids = [str(poi.get("id")) for poi in result.get("pois") or [] if poi.get("id")][:3]
            traces.append(
                ToolTraceItem(
                    tool="search_pois_tool",
                    status="success" if center_ids else "empty",
                    summary=f"为附近配套查询临时选取 {len(center_ids)} 个景点中心。",
                ).model_dump()
            )

        support: dict[str, Any] = {"center_poi_ids": center_ids}
        if center_ids:
            try:
                hotel_result = get_nearby_hotels_tool(
                    self.db,
                    GetNearbyHotelsArgs(center_poi_ids=center_ids[:10], radius_meters=2000, limit=10),
                )
                support["nearby_hotels"] = hotel_result.get("nearby_hotels") or []
                traces.append(
                    ToolTraceItem(
                        tool="get_nearby_hotels_tool",
                        status="success",
                        summary=f"找到 {len(support['nearby_hotels'])} 个附近酒店。",
                    ).model_dump()
                )
            except Exception as exc:  # noqa: BLE001
                traces.append(ToolTraceItem(tool="get_nearby_hotels_tool", status="failed", summary=str(exc)).model_dump())

            metro_results = []
            for poi_id in center_ids[:3]:
                try:
                    metro_result = get_nearby_metro_tool(
                        self.db,
                        GetNearbyMetroArgs(poi_id=poi_id, radius_meters=1500, limit=4),
                    )
                    metro_results.append(metro_result)
                except Exception as exc:  # noqa: BLE001
                    traces.append(ToolTraceItem(tool="get_nearby_metro_tool", status="failed", summary=str(exc)).model_dump())
            support["nearby_metro_by_poi"] = metro_results
            traces.append(
                ToolTraceItem(
                    tool="get_nearby_metro_tool",
                    status="success" if metro_results else "empty",
                    summary=f"围绕 {len(metro_results)} 个景点查询附近地铁。",
                ).model_dump()
            )

        return {"support_query": support}, traces

    def rank_candidates(self, context: AgentLoadedContext, tool_data: dict[str, Any]) -> list[str]:
        from_context = [str(item) for item in context.spatial_context.get("poi_ids") or [] if item]
        from_tools = [str(poi.get("id")) for poi in tool_data.get("candidate_pois") or [] if poi.get("id")]
        return list(dict.fromkeys([*from_context, *from_tools]))

    def build_trip_state(
        self,
        *,
        payload: AgentChatRequest,
        context: AgentLoadedContext,
        intent_slots: IntentSlots,
        decision: AgentDecision,
        ranked_candidates: list[str],
        saved_preferences: list[dict[str, Any]],
        tool_data: dict[str, Any],
    ) -> dict[str, Any]:
        existing = dict(context.trip_state or {})
        long_term_preferences = list(context.preferences or [])
        for item in saved_preferences:
            long_term_preferences.append(
                {
                    "preference_type": item.get("preference_type"),
                    "preference_value": item.get("preference_value"),
                    "confidence": item.get("confidence"),
                    "source": item.get("source"),
                }
            )
        if not saved_preferences:
            for item in extract_explicit_long_term_preferences(payload.message, intent_slots.explicit_long_term_preferences):
                long_term_preferences.append(
                    {
                        "preference_type": item.preference_type,
                        "preference_value": item.preference_value,
                        "confidence": item.confidence,
                        "source": item.source,
                    }
                )

        temporary_preferences = [] if is_long_term_preference(payload.message) else extract_temporary_preferences(payload.message, intent_slots.temporary_preferences)
        preferences = list(payload.preferences or [])
        preferences.extend(pref["preference_value"] for pref in long_term_preferences if pref.get("preference_value"))
        preferences.extend(temporary_preferences)
        if intent_slots.pace:
            preferences.append(intent_slots.pace)

        deduped_preferences = list(dict.fromkeys(str(item) for item in preferences if item))
        candidate_poi_ids = list(dict.fromkeys([*existing.get("candidate_poi_ids", []), *ranked_candidates]))
        return {
            **existing,
            "city": "武汉市",
            "intent": intent_slots.intent,
            "days": intent_slots.days or existing.get("days"),
            "date_range": intent_slots.date_range.model_dump(),
            "travel_dates": intent_slots.travel_dates,
            "pace": intent_slots.pace,
            "themes": intent_slots.themes,
            "avoid": intent_slots.avoid,
            "transport_preference": intent_slots.transport_preference,
            "mentioned_pois": intent_slots.mentioned_pois,
            "preferences": deduped_preferences,
            "long_term_preferences": long_term_preferences,
            "temporary_preferences": temporary_preferences,
            "saved_long_term_preferences": saved_preferences,
            "weather": tool_data.get("weather") or existing.get("weather"),
            "support_query": tool_data.get("support_query") or existing.get("support_query"),
            "candidate_poi_ids": candidate_poi_ids,
            "candidate_pois": merge_pois(existing.get("candidate_pois") or [], tool_data.get("candidate_pois") or []),
            "missing_slots": intent_slots.missing_slots,
            "planning_stage": "clarifying" if decision.action == "clarify" else "map_commands_ready",
            "orchestrator": {
                "version": "2.7",
                "fixed_nodes": [
                    "load_context",
                    "extract_intent_and_slots",
                    "decide_clarify_or_plan",
                    "collect_tool_data",
                    "rank_candidates",
                    "build_day_plans",
                    "plan_day_routes",
                    "build_map_commands",
                    "persist",
                ],
            },
        }

    def build_day_plans(self, trip_state: dict[str, Any], slots: IntentSlots, decision: AgentDecision) -> None:
        trip_state["day_plans"] = build_or_update_day_plans(
            existing_day_plans=list(trip_state.get("day_plans") or []),
            slots=slots,
            decision=decision,
            candidate_poi_ids=list(trip_state.get("candidate_poi_ids") or []),
        )
        enrich_day_plans_with_pois(trip_state)

    def plan_day_routes(
        self,
        trip_state: dict[str, Any],
        slots: IntentSlots,
        decision: AgentDecision,
        conversation_id: str,
    ) -> list[dict[str, Any]]:
        traces: list[dict[str, Any]] = []
        if decision.action != "continue" or not trip_state.get("day_plans") or not slots.need_route:
            trip_state.setdefault("route_planning_status", "skipped")
            return traces

        mode = choose_route_mode(trip_state.get("transport_preference"))
        planned = 0
        for day in trip_state.get("day_plans") or []:
            poi_ids = [str(item) for item in day.get("poi_ids") or [] if item]
            if len(poi_ids) < 2:
                continue
            try:
                result = plan_day_route_tool(
                    self.db,
                    PlanDayRouteArgs(
                        day_index=int(day.get("day_index") or planned + 1),
                        mode=mode,
                        poi_ids=poi_ids[:8],
                        conversation_id=conversation_id,
                        route_name=f"Agent Day {day.get('day_index')} 路线",
                    ),
                )
                day["route_id"] = result["route_id"]
                day["route"] = result["route"]
                day["route_mode"] = mode
                day["status"] = "planned_with_route"
                planned += 1
                traces.append(
                    ToolTraceItem(
                        tool="plan_day_route_tool",
                        status="success",
                        summary=f"Day {day.get('day_index')} 已生成路线 {result['route_id']}。",
                    ).model_dump()
                )
            except Exception as exc:  # noqa: BLE001
                day["route_error"] = str(exc)
                traces.append(
                    ToolTraceItem(
                        tool="plan_day_route_tool",
                        status="failed",
                        summary=f"Day {day.get('day_index')} 路线生成失败：{exc}",
                    ).model_dump()
                )

        trip_state["route_planning_status"] = "planned" if planned else "failed_or_not_enough_pois"
        return traces

    def build_response(
        self,
        *,
        conversation_id: str,
        payload: AgentChatRequest,
        context: AgentLoadedContext,
        intent_slots: IntentSlots,
        decision: AgentDecision,
        trip_state: dict[str, Any],
        tool_trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        reply = self.generate_reply(
            payload=payload,
            context=context,
            slots=intent_slots,
            decision=decision,
            trip_state=trip_state,
            tool_trace=tool_trace,
        )
        cards = [
            {
                "id": "card_agent_orchestrator_2_7",
                "type": "trip_summary_card",
                "title": "Agent 规划结果",
                "summary": f"已识别意图：{intent_slots.intent}；当前动作：{decision.action}；路线状态：{trip_state.get('route_planning_status', 'pending')}",
            }
        ]
        if trip_state.get("saved_long_term_preferences"):
            cards.append(
                {
                    "id": "card_saved_preferences",
                    "type": "preference_card",
                    "title": "已记录长期偏好",
                    "summary": "、".join(item.get("preference_value", "") for item in trip_state["saved_long_term_preferences"] if item.get("preference_value")),
                }
            )
        for day in trip_state.get("day_plans") or []:
            route_text = "已生成路线" if day.get("route_id") else "路线待生成"
            cards.append(
                {
                    "id": f"day_{day.get('day_index')}",
                    "type": "day_plan_card",
                    "title": day.get("theme") or f"Day {day.get('day_index')}",
                    "summary": f"包含 {len(day.get('poi_ids') or [])} 个候选 POI，{route_text}。",
                }
            )

        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "trip_state": trip_state,
            "cards": cards,
            "map_commands": build_map_commands(conversation_id=conversation_id, trip_state=trip_state),
            "clarifying_questions": decision.clarifying_questions,
            "warnings": decision.warnings,
            "tool_trace_summary": tool_trace,
        }

    def generate_reply(
        self,
        *,
        payload: AgentChatRequest,
        context: AgentLoadedContext,
        slots: IntentSlots,
        decision: AgentDecision,
        trip_state: dict[str, Any],
        tool_trace: list[dict[str, Any]],
    ) -> str:
        fallback = build_reply(slots, decision, trip_state)
        if decision.action == "clarify":
            return fallback
        try:
            current_date = current_local_date().isoformat()
            prompt_body = FINAL_REPLY_PROMPT.format(
                message=payload.message,
                context_summary=context.context_summary,
                intent_slots=json.dumps(slots.model_dump(), ensure_ascii=False),
                trip_state_summary=json.dumps(compact_trip_state_for_reply(trip_state), ensure_ascii=False),
                tool_trace_summary=json.dumps(tool_trace, ensure_ascii=False),
            )
            prompt = (
                f"系统当前日期（Asia/Shanghai）：{current_date}\n"
                "解释今天、明天、后天、大后天等相对日期时，必须以这个系统当前日期为准；"
                "如果工具结果中的 requested_dates 已给出日期，优先使用 requested_dates。\n\n"
                f"{prompt_body}"
            )
            result = AgentModelClient().invoke(
                [
                    {"role": "system", "content": "你是武汉旅游规划助手，只能基于给定真实数据回答，不能编造不存在的景点、天气或路线。"},
                    {"role": "user", "content": prompt},
                ],
                model_role="fast",
                temperature=0.55,
            )
            content = result.content.strip()
            return content or fallback
        except (AgentModelConfigError, AgentModelCallError):
            return fallback

    def load_pois_by_ids(self, poi_ids: list[str]) -> list[dict[str, Any]]:
        pois: list[dict[str, Any]] = []
        for poi_id in poi_ids[:12]:
            try:
                result = get_poi_detail_tool(self.db, GetPoiDetailArgs(poi_id=poi_id))
            except Exception:
                continue
            poi = result.get("poi")
            if poi:
                pois.append(poi)
        return pois


def build_reply(slots: IntentSlots, decision: AgentDecision, trip_state: dict[str, Any]) -> str:
    structured = build_structured_fallback_reply(slots, decision, trip_state)
    if structured:
        return structured

    if decision.action == "clarify":
        return "我可以帮你规划武汉行程，不过还需要先确认：" + "；".join(decision.clarifying_questions)

    if decision.action == "smalltalk":
        return "我在，接下来可以帮你做武汉景点、路线、天气和出行偏好相关规划。"

    if slots.intent == "plan_trip":
        days_text = f"{slots.days} 天" if slots.days else "多天"
        day_count = len(trip_state.get("day_plans") or [])
        route_count = sum(1 for day in trip_state.get("day_plans") or [] if day.get("route_id"))
        warning_text = " ".join(decision.warnings)
        return f"我已经为你的武汉 {days_text} 行程生成了 {day_count} 天计划，并生成了 {route_count} 条可在地图上展示的路线。{warning_text}".strip()

    if slots.intent == "modify_trip":
        target = f"第 {slots.target_day_index} 天" if slots.target_day_index else "指定某一天"
        return f"我已识别到你想修改{target}的行程，并会优先更新该 day 的结构和地图结果。"

    if slots.intent == "spatial_query_followup":
        count = len(trip_state.get("candidate_poi_ids") or [])
        return f"我已收到空间查询上下文，会围绕这 {count} 个候选 POI 继续规划，并把结果同步到地图。"

    if slots.intent == "weather_question":
        return build_weather_reply(trip_state)

    if slots.intent == "preference_update":
        saved = trip_state.get("saved_long_term_preferences") or []
        if saved:
            return "我已将这条明确的长期偏好保存下来，后续规划会默认参考它。"
        return "我已识别到你的偏好。本次临时偏好会写入当前 trip_state，不会覆盖长期偏好。"

    return "我已经理解你的需求，并通过 Orchestrator 写入当前对话状态。"


def fallback_intent(payload: AgentChatRequest) -> IntentSlots:
    message = payload.message or ""
    days = extract_days(message)
    travel_dates = extract_travel_dates(message)
    target_day_index = extract_target_day_index(message)
    context_poi_ids = payload.context.get("poi_ids", []) if payload.context else []
    if target_day_index and any(word in message for word in ["不要", "换", "改", "调整", "替换"]):
        intent = "modify_trip"
    elif context_poi_ids and any(word in message for word in ["这些", "刚才", "围绕", "附近", "这批"]):
        intent = "spatial_query_followup"
    elif is_nearby_support_query(message):
        intent = "search_poi"
    elif any(word in message for word in ["天气", "下雨", "高温", "气温", "热不热", "冷不冷"]):
        intent = "weather_question"
    elif any(word in message for word in ["以后", "今后", "一般", "都希望", "长期", "偏好"]):
        intent = "preference_update"
    elif any(word in message for word in ["规划", "行程", "路线", "游玩", "玩", "旅游"]) or days:
        intent = "plan_trip"
    elif any(word in message for word in ["地铁", "打车", "少走路", "人多", "轻松", "不累"]):
        intent = "preference_update"
    else:
        intent = "smalltalk"

    temporary_preferences = []
    pace = None
    if any(word in message for word in ["轻松", "不累", "慢一点"]):
        pace = "轻松"
        temporary_preferences.append("轻松")
    transport = "地铁优先" if "地铁" in message else None
    return IntentSlots(
        intent=intent,  # type: ignore[arg-type]
        days=days,
        travel_dates=travel_dates,
        target_day_index=target_day_index,
        modification_target=message if intent == "modify_trip" else None,
        pace=pace,
        temporary_preferences=temporary_preferences,
        explicit_long_term_preferences=[transport] if intent == "preference_update" and transport else [],
        transport_preference=transport,
        need_route=intent in PLAN_INTENTS,
        need_weather=any(word in message for word in ["天气", "下雨"]),
    )


def post_process_intent(slots: IntentSlots, payload: AgentChatRequest) -> IntentSlots:
    message = payload.message or ""
    context_poi_ids = payload.context.get("poi_ids", []) if payload.context else []
    days = slots.days or extract_days(message)
    extracted_dates = extract_travel_dates(message)
    travel_dates = list(slots.travel_dates) or extracted_dates
    target_day_index = slots.target_day_index or extract_target_day_index(message)
    intent = slots.intent

    if target_day_index and any(word in message for word in ["不要", "换", "改", "调整", "替换"]):
        intent = "modify_trip"
    elif any(word in message for word in ["以后", "今后", "一般", "都希望", "长期", "偏好"]):
        intent = "preference_update"
    elif context_poi_ids and any(word in message for word in ["这些", "刚才", "围绕", "附近", "这批"]):
        intent = "spatial_query_followup"
    elif is_nearby_support_query(message):
        intent = "search_poi"
    elif any(word in message for word in ["天气", "下雨", "高温", "气温", "热不热", "冷不冷"]):
        intent = "weather_question"
    elif any(word in message for word in ["地铁", "打车", "少走路", "人多", "轻松", "不累"]) and not any(word in message for word in ["规划", "行程", "路线", "游玩", "玩", "旅游"]):
        intent = "preference_update"
    elif any(word in message for word in ["规划", "行程", "路线", "游玩", "玩", "旅游"]) or days:
        intent = "plan_trip"

    pace = slots.pace
    temporary_preferences = list(slots.temporary_preferences)
    if any(word in message for word in ["轻松", "不累", "慢一点"]):
        pace = pace or "轻松"
        temporary_preferences.append("轻松")

    transport = slots.transport_preference
    if "地铁" in message:
        transport = transport or "地铁优先"
        temporary_preferences.append("地铁优先")

    explicit_long_term_preferences = list(slots.explicit_long_term_preferences)
    if intent == "preference_update":
        explicit_long_term_preferences.extend(temporary_preferences)

    return slots.model_copy(
        update={
            "intent": intent,
            "days": days,
            "travel_dates": travel_dates,
            "target_day_index": target_day_index,
            "modification_target": slots.modification_target or (message if intent == "modify_trip" else None),
            "pace": pace,
            "transport_preference": transport,
            "explicit_long_term_preferences": list(dict.fromkeys(explicit_long_term_preferences)),
            "temporary_preferences": list(dict.fromkeys(temporary_preferences)),
            "need_route": slots.need_route or intent in PLAN_INTENTS,
            "need_weather": slots.need_weather or any(word in message for word in ["天气", "下雨", "高温"]),
        }
    )


def extract_days(message: str) -> int | None:
    chinese_days = {"一天": 1, "一日": 1, "两天": 2, "两日": 2, "三天": 3, "三日": 3, "四天": 4, "四日": 4}
    for key, value in chinese_days.items():
        if key in message:
            return value
    match = re.search(r"(\d+)\s*[天日]", message)
    if match:
        return int(match.group(1))
    return None


def extract_target_day_index(message: str) -> int | None:
    chinese_days = {"第一天": 1, "第1天": 1, "第二天": 2, "第2天": 2, "第三天": 3, "第3天": 3, "第四天": 4, "第4天": 4}
    for key, value in chinese_days.items():
        if key in message:
            return value
    match = re.search(r"第\s*(\d+)\s*[天日]", message)
    if match:
        return int(match.group(1))
    return None


def extract_travel_dates(message: str) -> list[str]:
    today = current_local_date()
    current_year = today.year
    result: list[str] = []

    remaining = message or ""
    relative_offsets = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
    }
    chained_pattern = re.compile(r"(?:今天|明天|后天|大后天)(?:的(?:今天|明天|后天|大后天))+")
    for match in chained_pattern.finditer(remaining):
        phrase = match.group(0)
        tokens = re.findall(r"今天|明天|后天|大后天", phrase)
        offset_days = sum(relative_offsets[token] for token in tokens)
        result.append((today + timedelta(days=offset_days)).isoformat())
        remaining = remaining.replace(phrase, " ")

    relative_phrases = [
        ("后天的后天", 4),
        ("大后天", 3),
        ("后天", 2),
        ("明天", 1),
        ("今天", 0),
    ]
    for phrase, offset_days in relative_phrases:
        if phrase in remaining:
            result.append((today + timedelta(days=offset_days)).isoformat())
            remaining = remaining.replace(phrase, " ")

    for month, day in re.findall(r"(\d{1,2})\s*[./月]\s*(\d{1,2})\s*号?", message):
        try:
            result.append(date(current_year, int(month), int(day)).isoformat())
        except ValueError:
            continue
    return list(dict.fromkeys(result))


def current_local_date() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def build_weather_reply(trip_state: dict[str, Any]) -> str:
    weather = trip_state.get("weather") or {}
    forecasts = weather.get("requested_forecast") or weather.get("forecast") or weather.get("forecasts") or []
    current = weather.get("current") or {}
    if forecasts:
        items = []
        for item in forecasts[:3]:
            report_date = item.get("date") or item.get("report_date") or ""
            day_weather = item.get("day_weather") or item.get("weather") or ""
            temp = ""
            if item.get("day_temp") or item.get("night_temp"):
                temp = f"{item.get('night_temp', '')}-{item.get('day_temp', '')}℃"
            items.append(f"{report_date} {day_weather} {temp}".strip())
        unavailable = weather.get("unavailable_dates") or []
        suffix = "。后续可以据此把雨天或高温时段调整为室内景点。"
        if unavailable:
            suffix = f"。其中 {'、'.join(unavailable)} 当前高德没有返回可用预报；其余日期可以用于行程微调。"
        return "我查到了武汉近期天气：" + "；".join(items) + suffix
    if current:
        return f"武汉当前天气：{current.get('weather', '')}，气温 {current.get('temperature', '')}℃，风向 {current.get('wind_direction', '')}。"
    return "我识别到你在问天气，但这次天气工具没有返回可用数据；可以稍后再试或检查高德天气接口配置。"


def filter_weather_by_requested_dates(weather: dict[str, Any], requested_dates: list[str]) -> dict[str, Any]:
    if not requested_dates:
        return weather
    normalized_dates = [item for item in requested_dates if item]
    forecasts = weather.get("forecast") or []
    by_date = {str(item.get("date")): item for item in forecasts if item.get("date")}
    matched = [by_date[day] for day in normalized_dates if day in by_date]
    unavailable = [day for day in normalized_dates if day not in by_date]
    result = dict(weather)
    result["requested_dates"] = normalized_dates
    result["requested_forecast"] = matched
    result["unavailable_dates"] = unavailable
    result["forecast_available"] = bool(matched)
    if unavailable:
        warnings = list(result.get("warnings") or [])
        warnings.append(f"No Amap forecast is available for: {', '.join(unavailable)}")
        result["warnings"] = warnings
    return result


def compact_trip_state_for_reply(trip_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "city": trip_state.get("city"),
        "intent": trip_state.get("intent"),
        "days": trip_state.get("days"),
        "travel_dates": trip_state.get("travel_dates") or [],
        "preferences": trip_state.get("preferences") or [],
        "route_planning_status": trip_state.get("route_planning_status"),
        "weather": compact_weather(trip_state.get("weather") or {}),
        "support_query": compact_support_query(trip_state.get("support_query") or {}),
        "day_plans": [compact_day_for_reply(day) for day in trip_state.get("day_plans") or []],
    }


def build_structured_fallback_reply(slots: IntentSlots, decision: AgentDecision, trip_state: dict[str, Any]) -> str | None:
    if decision.action == "clarify":
        return None

    if slots.intent == "weather_question":
        return build_weather_reply(trip_state)

    if slots.intent not in PLAN_INTENTS:
        return None

    day_plans = trip_state.get("day_plans") or []
    if not day_plans:
        return None

    lines = []
    dates = trip_state.get("travel_dates") or []
    if dates:
        lines.append(f"我记得这次是 {len(day_plans)} 天武汉行程，日期先按 {'、'.join(dates[:len(day_plans)])} 记录。")
    else:
        lines.append(f"我先给你排了一版 {len(day_plans)} 天武汉行程，后续补日期后我可以继续按天气微调。")

    for day in day_plans:
        names = [poi.get("name_zh") for poi in day.get("pois") or [] if poi.get("name_zh")]
        if not names:
            names = [str(poi_id) for poi_id in day.get("poi_ids") or []]
        if not names:
            continue
        date_text = f"（{day.get('date')}）" if day.get("date") else ""
        lines.append(f"第 {day.get('day_index')} 天{date_text}：{' -> '.join(names)}。")
        first_intro = next(((((poi.get("profile") or {}).get("short_intro_zh")) or "") for poi in day.get("pois") or [] if (poi.get("profile") or {}).get("short_intro_zh")), "")
        if first_intro:
            lines.append(f"这一天我会把重点放在 {names[0]} 一带：{first_intro[:70]}。")

    route_count = sum(1 for day in day_plans if day.get("route_id"))
    if route_count:
        lines.append(f"路线我已经同步到地图上了，共 {route_count} 条，可以直接看线条和动画顺序。")

    weather_text = build_weather_reply(trip_state) if trip_state.get("weather") else ""
    if weather_text and "没有返回可用数据" not in weather_text:
        lines.append(weather_text)

    return "\n".join(lines[:7])


def compact_day_for_reply(day: dict[str, Any]) -> dict[str, Any]:
    return {
        "day_index": day.get("day_index"),
        "date": day.get("date"),
        "theme": day.get("theme"),
        "route_id": day.get("route_id"),
        "route_mode": day.get("route_mode"),
        "pois": [compact_poi_for_reply(poi) for poi in day.get("pois") or []],
    }


def compact_poi_for_reply(poi: dict[str, Any]) -> dict[str, Any]:
    profile = poi.get("profile") or {}
    return {
        "name": poi.get("name_zh"),
        "category": poi.get("category_code"),
        "address": poi.get("address"),
        "tags": poi.get("tags") or [],
        "intro": profile.get("short_intro_zh") or "",
        "duration_minutes": profile.get("recommended_duration_minutes"),
        "opening_hours": profile.get("opening_hours"),
        "ticket_info": profile.get("ticket_info"),
    }


def compact_weather(weather: dict[str, Any]) -> dict[str, Any]:
    return {
        "city": weather.get("city"),
        "district": weather.get("district"),
        "current": weather.get("current"),
        "requested_dates": weather.get("requested_dates") or [],
        "requested_forecast": (weather.get("requested_forecast") or [])[:4],
        "unavailable_dates": weather.get("unavailable_dates") or [],
        "forecast": (weather.get("forecast") or [])[:4],
        "warnings": weather.get("warnings") or [],
        "cache_hit": weather.get("cache_hit"),
    }


def compact_support_query(support_query: dict[str, Any]) -> dict[str, Any]:
    return {
        "center_poi_ids": support_query.get("center_poi_ids") or [],
        "nearby_hotels": (support_query.get("nearby_hotels") or [])[:6],
        "nearby_metro_by_poi": (support_query.get("nearby_metro_by_poi") or [])[:3],
    }


def merge_pois(existing: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for poi in [*existing, *current]:
        poi_id = str(poi.get("id") or "")
        if not poi_id or poi_id in seen:
            continue
        seen.add(poi_id)
        result.append(poi)
    return result


def sample_candidate_pois(pois: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if len(pois) <= limit:
        shuffled = list(pois)
        random.SystemRandom().shuffle(shuffled)
        return shuffled

    top_count = min(4, max(1, limit // 4))
    top_pois = pois[:top_count]
    rest = pois[top_count:]
    sampled_rest = random.SystemRandom().sample(rest, k=max(0, limit - len(top_pois)))
    result = [*top_pois, *sampled_rest]
    random.SystemRandom().shuffle(result)
    return result


def diversify_candidate_pois(pois: list[dict[str, Any]], *, days: int) -> list[dict[str, Any]]:
    if days <= 1 or len(pois) <= 2:
        return pois

    groups: dict[str, list[dict[str, Any]]] = {}
    for poi in pois:
        district = str(poi.get("district") or "未知区域")
        groups.setdefault(district, []).append(poi)

    diversified: list[dict[str, Any]] = []
    district_names = list(groups.keys())
    while len(diversified) < len(pois):
        moved = False
        for district in district_names:
            bucket = groups[district]
            if not bucket:
                continue
            diversified.append(bucket.pop(0))
            moved = True
        if not moved:
            break
    return diversified


def is_nearby_support_query(message: str | None) -> bool:
    text = message or ""
    has_support_keyword = any(word in text for word in ["酒店", "住宿", "宾馆", "地铁", "交通", "站"])
    has_nearby_keyword = any(word in text for word in ["附近", "周边", "旁边", "靠近", "近一点", "近的"])
    return has_support_keyword and (has_nearby_keyword or "景点" in text)


def select_support_center_poi_ids(trip_state: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for day in trip_state.get("day_plans") or []:
        ids.extend(str(item) for item in day.get("poi_ids") or [] if item)
    if not ids:
        ids.extend(str(item) for item in trip_state.get("candidate_poi_ids") or [] if item)
    return list(dict.fromkeys(ids))[:10]


def enrich_day_plans_with_pois(trip_state: dict[str, Any]) -> None:
    pois_by_id = {str(poi.get("id")): poi for poi in trip_state.get("candidate_pois") or [] if poi.get("id")}
    for day in trip_state.get("day_plans") or []:
        day_pois = [pois_by_id[poi_id] for poi_id in day.get("poi_ids") or [] if poi_id in pois_by_id]
        if day_pois:
            day["pois"] = day_pois
            districts = [str(poi.get("district")) for poi in day_pois if poi.get("district")]
            day["districts"] = list(dict.fromkeys([*list(day.get("districts") or []), *districts]))


def choose_route_mode(transport_preference: str | None) -> RouteMode:
    if not transport_preference:
        return "walking"
    if "地铁" in transport_preference or "公交" in transport_preference:
        return "transit"
    if "打车" in transport_preference or "自驾" in transport_preference:
        return "driving"
    return "walking"
