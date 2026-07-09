from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.agent.memory_manager import load_context
from app.agent.model_client import AgentModelCallError, AgentModelClient, AgentModelConfigError
from app.agent.response_builder import build_map_commands
from app.agent.state_manager import normalize_conversation_id, resolve_owned_conversation_id
from app.agent.graph.prompts import GRAPH_REPLY_PROMPT, GRAPH_TOOL_PLAN_PROMPT, GRAPH_UNDERSTANDING_PROMPT
from app.agent.graph.schemas import GraphToolPlan, GraphUnderstanding
from app.agent.graph.state import GraphAgentState
from app.agent.graph.tools import get_graph_tool_registry
from app.core.security import CurrentUser
from app.schemas.agent import AgentChatRequest


class GraphAgentUnavailable(RuntimeError):
    pass


class GraphAgentRunner:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = get_graph_tool_registry()

    def run(self, payload: AgentChatRequest, user: CurrentUser | None = None) -> dict[str, Any]:
        conversation_id = normalize_conversation_id(payload.conversation_id)
        if user:
            conversation_id = resolve_owned_conversation_id(self.db, conversation_id=conversation_id, user=user)

        state: GraphAgentState = {
            "conversation_id": conversation_id,
            "user_id": user.id if user else None,
            "message": payload.message,
            "request_context": payload.context or {},
            "warnings": [],
            "tool_trace_summary": [],
        }

        graph = self._build_graph(payload, user)
        final_state = graph.invoke(state)
        return self._to_response(final_state)

    def _build_graph(self, payload: AgentChatRequest, user: CurrentUser | None):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError as exc:
            raise GraphAgentUnavailable("LangGraph is not installed. Run: pip install -r backend/requirements.txt") from exc

        graph = StateGraph(GraphAgentState)
        graph.add_node("load_context", lambda state: self.load_context_node(state, payload, user))
        graph.add_node("understand_user", self.understand_user_node)
        graph.add_node("plan_tool_calls", self.plan_tool_calls_node)
        graph.add_node("execute_tools", self.execute_tools_node)
        graph.add_node("retry_tools_if_needed", self.retry_tools_if_needed_node)
        graph.add_node("reflect_or_continue", self.reflect_or_continue_node)
        graph.add_node("build_trip_state", self.build_trip_state_node)
        graph.add_node("plan_routes_if_needed", self.plan_routes_if_needed_node)
        graph.add_node("compose_reply", self.compose_reply_node)

        graph.set_entry_point("load_context")
        graph.add_edge("load_context", "understand_user")
        graph.add_edge("understand_user", "plan_tool_calls")
        graph.add_edge("plan_tool_calls", "execute_tools")
        graph.add_edge("execute_tools", "retry_tools_if_needed")
        graph.add_edge("retry_tools_if_needed", "reflect_or_continue")
        graph.add_edge("reflect_or_continue", "build_trip_state")
        graph.add_edge("build_trip_state", "plan_routes_if_needed")
        graph.add_edge("plan_routes_if_needed", "compose_reply")
        graph.add_edge("compose_reply", END)
        return graph.compile()

    def load_context_node(
        self,
        state: GraphAgentState,
        payload: AgentChatRequest,
        user: CurrentUser | None,
    ) -> GraphAgentState:
        context = load_context(self.db, conversation_id=state["conversation_id"], payload=payload, user=user)
        return {
            **state,
            "loaded_context": context.model_dump(),
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {"tool": "graph_load_context", "status": "success", "summary": "loaded preferences, messages and trip_state"},
            ],
        }

    def understand_user_node(self, state: GraphAgentState) -> GraphAgentState:
        context = state.get("loaded_context") or {}
        prompt = GRAPH_UNDERSTANDING_PROMPT.format(
            context_summary=context.get("context_summary") or "",
            preferences=json.dumps(context.get("preferences") or [], ensure_ascii=False),
            message=state["message"],
        )
        try:
            result = AgentModelClient().invoke_json(prompt, GraphUnderstanding, model_role="fast")
            understanding = post_process_graph_understanding(GraphUnderstanding.model_validate(result.parsed), state["message"])
            status = f"{result.model} validated"
        except (AgentModelConfigError, AgentModelCallError) as exc:
            understanding = post_process_graph_understanding(heuristic_understanding(state["message"]), state["message"])
            status = f"fallback: {exc}"

        return {
            **state,
            "understanding": understanding.model_dump(),
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {"tool": "graph_understand_user", "status": "success", "summary": status},
            ],
        }

    def plan_tool_calls_node(self, state: GraphAgentState) -> GraphAgentState:
        understanding = GraphUnderstanding.model_validate(state.get("understanding") or {})
        if not understanding.needs_tool:
            return {**state, "tool_plan": []}

        prompt = GRAPH_TOOL_PLAN_PROMPT.format(
            tools=json.dumps(self.registry.list_tools(), ensure_ascii=False),
            understanding=json.dumps(understanding.model_dump(), ensure_ascii=False),
            message=state["message"],
        )
        try:
            result = AgentModelClient().invoke_json(prompt, GraphToolPlan, model_role="fast")
            plan = normalize_graph_tool_plan(GraphToolPlan.model_validate(result.parsed), understanding, state["message"])
            status = f"{result.model} planned {len(plan.tool_calls)} calls"
        except (AgentModelConfigError, AgentModelCallError) as exc:
            plan = normalize_graph_tool_plan(heuristic_tool_plan(understanding), understanding, state["message"])
            status = f"fallback: {exc}"

        return {
            **state,
            "tool_plan": [item.model_dump() for item in plan.tool_calls],
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {"tool": "graph_plan_tool_calls", "status": "success", "summary": status},
            ],
        }

    def execute_tools_node(self, state: GraphAgentState) -> GraphAgentState:
        tool_plan = list(state.get("tool_plan") or [])
        results = self.registry.execute_many(self.db, tool_plan)
        return self.with_tool_results(**{
            **state,
            "tool_results": results,
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                *[
                    {"tool": item.get("tool"), "status": item.get("status"), "summary": item.get("summary") or item.get("error") or ""}
                    for item in results
                ],
            ],
        })

    def retry_tools_if_needed_node(self, state: GraphAgentState) -> GraphAgentState:
        retry_count = int(state.get("retry_count") or 0)
        results = list(state.get("tool_results") or [])
        understanding = GraphUnderstanding.model_validate(state.get("understanding") or {})
        if retry_count >= 1:
            return {
                **state,
                "retry_summary": {"attempted": False, "reason": "retry limit reached"},
            }

        retry_calls = build_retry_tool_calls(
            tool_plan=list(state.get("tool_plan") or []),
            tool_results=results,
            understanding=understanding,
        )
        if not retry_calls:
            return {
                **state,
                "retry_summary": {"attempted": False, "reason": "tool results are sufficient or retry is not useful"},
                "tool_trace_summary": [
                    *state.get("tool_trace_summary", []),
                    {"tool": "graph_retry_tools_if_needed", "status": "skipped", "summary": "no retry needed"},
                ],
            }

        retry_results = self.registry.execute_many(self.db, retry_calls, max_total_calls=4)
        combined_results = merge_tool_results(results, retry_results)
        return self.with_tool_results(**{
            **state,
            "retry_count": retry_count + 1,
            "tool_results": combined_results,
            "retry_summary": {
                "attempted": True,
                "retry_tool_count": len(retry_calls),
                "reason": "initial tool results were empty, blocked, or too narrow",
            },
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {"tool": "graph_retry_tools_if_needed", "status": "success", "summary": f"executed {len(retry_calls)} retry calls"},
                *[
                    {"tool": item.get("tool"), "status": item.get("status"), "summary": item.get("summary") or item.get("error") or ""}
                    for item in retry_results
                ],
            ],
        })

    def reflect_or_continue_node(self, state: GraphAgentState) -> GraphAgentState:
        results = list(state.get("tool_results") or [])
        pois = collect_pois_from_tool_results(results)
        existing_detail_ids = {
            str((item.get("result") or {}).get("poi", {}).get("id"))
            for item in results
            if item.get("tool") == "get_poi_detail" and (item.get("result") or {}).get("poi")
        }

        followup_calls: list[dict[str, Any]] = []
        for poi in pois[:3]:
            poi_id = str(poi.get("id") or "")
            if poi_id and poi_id not in existing_detail_ids:
                followup_calls.append(
                    {
                        "tool": "get_poi_detail",
                        "args": {"poi_id": poi_id},
                        "reason": "补充前几个候选 POI 的简介、图片和游玩信息，便于自然回答。",
                    }
                )

        message = state["message"]
        if pois and any(word in message for word in ["地铁", "交通", "怎么去", "方便"]):
            for poi in pois[:2]:
                poi_id = str(poi.get("id") or "")
                if poi_id:
                    followup_calls.append(
                        {
                            "tool": "get_nearby_metro",
                            "args": {"poi_id": poi_id, "radius_meters": 1500, "limit": 4},
                            "reason": "用户关注交通或地铁，补充候选 POI 周边地铁。",
                        }
                    )

        if pois and any(word in message for word in ["酒店", "住宿", "住哪", "宾馆"]):
            followup_calls.append(
                {
                    "tool": "get_nearby_hotels",
                    "args": {
                        "center_poi_ids": [str(poi.get("id")) for poi in pois[:3] if poi.get("id")],
                        "radius_meters": 2000,
                        "limit": 8,
                    },
                    "reason": "用户关注住宿，补充候选区域附近酒店。",
                }
            )

        if not followup_calls:
            return self.with_tool_results(**{
                **state,
                "reflection": {
                    "continued": False,
                    "reason": "现有工具结果足以进入回复阶段，或没有可补充的安全工具调用。",
                },
                "tool_trace_summary": [
                    *state.get("tool_trace_summary", []),
                    {"tool": "graph_reflect_or_continue", "status": "skipped", "summary": "no follow-up tools needed"},
                ],
            })

        followup_results = self.registry.execute_many(self.db, followup_calls, max_total_calls=8)
        combined_results = [*results, *followup_results]
        return self.with_tool_results(**{
            **state,
            "tool_results": combined_results,
            "reflection": {
                "continued": True,
                "followup_tool_count": len(followup_calls),
                "reason": "对搜索结果补充详情或周边配套数据后再回复。",
            },
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {"tool": "graph_reflect_or_continue", "status": "success", "summary": f"executed {len(followup_calls)} follow-up calls"},
                *[
                    {"tool": item.get("tool"), "status": item.get("status"), "summary": item.get("summary") or item.get("error") or ""}
                    for item in followup_results
                ],
            ],
        })

    def with_tool_results(self, **state: Any) -> GraphAgentState:
        tool_results = list(state.get("tool_results") or [])
        candidate_pois = collect_pois_from_tool_results(tool_results)
        candidate_poi_ids = [str(poi.get("id")) for poi in candidate_pois if poi.get("id")]
        trip_state = {
            **(state.get("loaded_context", {}).get("trip_state") or {}),
            "agent_engine": "graph",
            "graph_stage": "minimal_closed_loop",
            "intent": (state.get("understanding") or {}).get("intent"),
            "candidate_pois": candidate_pois,
            "candidate_poi_ids": list(dict.fromkeys(candidate_poi_ids)),
            "tool_result_summary": summarize_results_for_state(tool_results),
            "planning_stage": "graph_tool_results_ready",
        }
        return {
            **state,
            "trip_state": trip_state,
            "map_commands": build_map_commands(conversation_id=state["conversation_id"], trip_state=trip_state),
            "cards": build_cards(candidate_pois),
        }

    def build_trip_state_node(self, state: GraphAgentState) -> GraphAgentState:
        understanding = GraphUnderstanding.model_validate(state.get("understanding") or {})
        if understanding.intent not in {"plan_trip", "modify_trip"}:
            return state

        candidate_pois = collect_pois_from_tool_results(list(state.get("tool_results") or []))
        day_plans = build_graph_day_plans(
            existing_day_plans=list((state.get("loaded_context", {}).get("trip_state") or {}).get("day_plans") or []),
            candidate_pois=candidate_pois,
            understanding=understanding,
            message=state["message"],
        )
        trip_state = {
            **(state.get("trip_state") or {}),
            "days": len(day_plans) or understanding.days,
            "day_plans": day_plans,
            "planning_stage": "graph_day_plans_ready" if day_plans else "graph_tool_results_ready",
        }
        return {
            **state,
            "trip_state": trip_state,
            "map_commands": build_map_commands(conversation_id=state["conversation_id"], trip_state=trip_state),
            "cards": [*build_cards(candidate_pois), *build_day_cards(day_plans)],
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {
                    "tool": "graph_build_trip_state",
                    "status": "success" if day_plans else "skipped",
                    "summary": f"built {len(day_plans)} day plans",
                },
            ],
        }

    def plan_routes_if_needed_node(self, state: GraphAgentState) -> GraphAgentState:
        understanding = GraphUnderstanding.model_validate(state.get("understanding") or {})
        trip_state = dict(state.get("trip_state") or {})
        day_plans = list(trip_state.get("day_plans") or [])
        if not should_plan_graph_routes(understanding, state["message"], day_plans):
            trip_state.setdefault("route_planning_status", "skipped")
            return {
                **state,
                "trip_state": trip_state,
                "tool_trace_summary": [
                    *state.get("tool_trace_summary", []),
                    {"tool": "graph_plan_routes_if_needed", "status": "skipped", "summary": "route planning not required"},
                ],
            }

        route_calls = []
        mode = choose_graph_route_mode(state["message"])
        for day in day_plans[:3]:
            poi_ids = [str(item) for item in day.get("poi_ids") or [] if item]
            if len(poi_ids) < 2:
                continue
            route_calls.append(
                {
                    "tool": "plan_day_route",
                    "args": {
                        "day_index": int(day.get("day_index") or len(route_calls) + 1),
                        "mode": mode,
                        "poi_ids": poi_ids[:8],
                        "conversation_id": state["conversation_id"],
                        "route_name": f"Graph Agent Day {day.get('day_index')} route",
                    },
                    "reason": "完整行程规划需要生成当天真实路线。",
                }
            )

        if not route_calls:
            trip_state["route_planning_status"] = "skipped_no_enough_pois"
            return {
                **state,
                "trip_state": trip_state,
                "tool_trace_summary": [
                    *state.get("tool_trace_summary", []),
                    {"tool": "graph_plan_routes_if_needed", "status": "skipped", "summary": "not enough POIs for routes"},
                ],
            }

        route_results = self.registry.execute_many(self.db, route_calls, max_total_calls=3)
        route_results = maybe_retry_failed_routes_as_walking(
            db=self.db,
            registry=self.registry,
            original_calls=route_calls,
            route_results=route_results,
            mode=mode,
        )
        route_by_day = {
            int((item.get("result") or {}).get("day_index") or 0): item.get("result") or {}
            for item in route_results
            if item.get("status") == "success"
        }
        for day in day_plans:
            route_result = route_by_day.get(int(day.get("day_index") or 0))
            if not route_result:
                continue
            day["route_id"] = route_result.get("route_id")
            day["route"] = route_result.get("route")
            day["route_mode"] = (route_result.get("route") or {}).get("route_mode") or mode
            day["status"] = "route_ready"

        trip_state["day_plans"] = day_plans
        trip_state["route_planning_status"] = "ready" if route_by_day else "failed"
        combined_results = [*list(state.get("tool_results") or []), *route_results]
        trip_state["tool_result_summary"] = summarize_results_for_state(combined_results)
        return {
            **state,
            "tool_results": combined_results,
            "trip_state": trip_state,
            "map_commands": build_map_commands(conversation_id=state["conversation_id"], trip_state=trip_state),
            "cards": [*build_cards(collect_pois_from_tool_results(combined_results)), *build_day_cards(day_plans)],
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {
                    "tool": "graph_plan_routes_if_needed",
                    "status": "success" if route_by_day else "failed",
                    "summary": f"planned {len(route_by_day)} routes",
                },
                *[
                    {"tool": item.get("tool"), "status": item.get("status"), "summary": item.get("summary") or item.get("error") or ""}
                    for item in route_results
                ],
            ],
        }

    def compose_reply_node(self, state: GraphAgentState) -> GraphAgentState:
        prompt = GRAPH_REPLY_PROMPT.format(
            message=state["message"],
            understanding=json.dumps(state.get("understanding") or {}, ensure_ascii=False),
            tool_results=json.dumps(compact_tool_results(state.get("tool_results") or []), ensure_ascii=False),
        )
        try:
            result = AgentModelClient().invoke(
                [
                    {"role": "system", "content": "你是武汉旅行规划助手，只能基于给定工具结果回答。"},
                    {"role": "user", "content": prompt},
                ],
                model_role="fast",
                temperature=0.35,
            )
            reply = result.content.strip()
            status = f"{result.model} reply"
        except (AgentModelConfigError, AgentModelCallError) as exc:
            reply = heuristic_reply(state)
            status = f"fallback: {exc}"

        return {
            **state,
            "reply": reply or heuristic_reply(state),
            "tool_trace_summary": [
                *state.get("tool_trace_summary", []),
                {"tool": "graph_compose_reply", "status": "success", "summary": status},
            ],
        }

    def _to_response(self, state: GraphAgentState) -> dict[str, Any]:
        return {
            "conversation_id": state["conversation_id"],
            "reply": state.get("reply") or "我已经理解你的需求，但这次没有拿到足够的工具结果。",
            "trip_state": state.get("trip_state") or {"agent_engine": "graph"},
            "cards": state.get("cards") or [],
            "map_commands": state.get("map_commands") or [],
            "clarifying_questions": [],
            "warnings": state.get("warnings") or [],
            "tool_trace_summary": state.get("tool_trace_summary") or [],
        }


def heuristic_understanding(message: str) -> GraphUnderstanding:
    keywords = extract_keywords(message)
    intent = "search_poi"
    if any(word in message for word in ["天气", "下雨", "气温", "热不热", "冷不冷"]):
        intent = "weather_question"
    elif any(word in message for word in ["酒店", "住宿", "地铁", "交通", "附近"]):
        intent = "nearby_support" if any(word in message for word in ["酒店", "地铁", "交通"]) else "search_poi"
    elif any(word in message for word in ["规划", "行程", "路线", "玩两天", "玩一天", "玩三天"]):
        intent = "plan_trip"
    elif len(message.strip()) < 4:
        intent = "smalltalk"

    return GraphUnderstanding(
        intent=intent,  # type: ignore[arg-type]
        keywords=keywords,
        days=extract_graph_days(message),
        needs_tool=intent != "smalltalk",
        should_plan_route=intent == "plan_trip" and any(word in message for word in ["路线", "完整", "行程", "规划"]),
    )


def post_process_graph_understanding(understanding: GraphUnderstanding, message: str) -> GraphUnderstanding:
    days = understanding.days or extract_graph_days(message)
    travel_dates = understanding.travel_dates or extract_graph_travel_dates(message)
    intent = understanding.intent
    planning_words = ["规划", "行程", "路线", "玩两天", "玩一天", "玩三天", "游玩", "旅游"]
    if days and any(word in message for word in planning_words):
        intent = "plan_trip"
    should_plan_route = understanding.should_plan_route or intent == "plan_trip"
    return understanding.model_copy(
        update={"intent": intent, "days": days, "travel_dates": travel_dates, "should_plan_route": should_plan_route}
    )


def normalize_graph_tool_plan(plan: GraphToolPlan, understanding: GraphUnderstanding, message: str) -> GraphToolPlan:
    normalized = []
    requested_dates = understanding.travel_dates or extract_graph_travel_dates(message)
    for call in plan.tool_calls:
        if call.tool != "get_weather":
            normalized.append(call)
            continue
        args = dict(call.args or {})
        args.setdefault("city", "武汉市")
        if not args.get("district") and not args.get("adcode"):
            args["adcode"] = "420100"
        args["extensions"] = "all"
        if len(requested_dates) == 1 and not args.get("date"):
            args["date"] = requested_dates[0]
        normalized.append(call.model_copy(update={"args": args}))
    return GraphToolPlan(tool_calls=normalized)


def extract_graph_travel_dates(message: str) -> list[str]:
    today = date.today()
    found: list[date] = []
    for year_text, month_text, day_text in re.findall(r"(?:(20\d{2})[./年-])?(\d{1,2})[./月-](\d{1,2})\s*[日号]?", message):
        year = int(year_text) if year_text else today.year
        try:
            found.append(date(year, int(month_text), int(day_text)))
        except ValueError:
            continue
    relative_offsets = {
        "今天": 0,
        "今日": 0,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
    }
    for word, offset in relative_offsets.items():
        if word in message:
            found.append(today + timedelta(days=offset))
    unique: list[str] = []
    seen: set[str] = set()
    for item in found:
        value = item.isoformat()
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique[:7]


def extract_graph_days(message: str) -> int | None:
    mapping = {
        "一天": 1,
        "一日": 1,
        "半天": 1,
        "两天": 2,
        "两日": 2,
        "二天": 2,
        "二日": 2,
        "三天": 3,
        "三日": 3,
        "四天": 4,
        "四日": 4,
        "五天": 5,
        "五日": 5,
        "六天": 6,
        "六日": 6,
        "七天": 7,
        "七日": 7,
    }
    for key, value in mapping.items():
        if key in message:
            return value
    match = re.search(r"(\d+)\s*[天日]", message)
    if match:
        return max(1, min(int(match.group(1)), 7))
    return None


def heuristic_tool_plan(understanding: GraphUnderstanding) -> GraphToolPlan:
    calls = []
    keyword = understanding.keywords[0] if understanding.keywords else None
    if understanding.intent == "weather_question":
        calls.append({"tool": "get_weather", "args": {"city": "武汉市", "adcode": "420100", "extensions": "all"}})
    else:
        calls.append(
            {
                "tool": "search_pois",
                "args": {
                    "category_codes": understanding.category_codes or ["scenic_spot"],
                    "keyword": keyword,
                    "district": understanding.district,
                    "city": "武汉市",
                    "limit": 12,
                },
            }
        )
    return GraphToolPlan(tool_calls=calls)


def build_retry_tool_calls(
    *,
    tool_plan: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    understanding: GraphUnderstanding,
) -> list[dict[str, Any]]:
    if not understanding.needs_tool:
        return []

    pois = collect_pois_from_tool_results(tool_results)
    has_weather = any(item.get("tool") == "get_weather" and item.get("status") == "success" for item in tool_results)
    has_failures = any(item.get("status") in {"failed", "blocked"} for item in tool_results)
    search_results = [item for item in tool_results if item.get("tool") == "search_pois"]
    search_empty = bool(search_results) and not pois

    retry_calls: list[dict[str, Any]] = []
    if understanding.intent == "weather_question" and not has_weather:
        retry_calls.append({"tool": "get_weather", "args": {"city": "武汉市", "adcode": "420100", "extensions": "all"}})

    if understanding.intent != "weather_question" and (search_empty or (has_failures and not pois) or (not tool_results and tool_plan)):
        retry_calls.append(
            {
                "tool": "search_pois",
                "args": {
                    "category_codes": understanding.category_codes or ["scenic_spot"],
                    "keyword": None,
                    "district": understanding.district,
                    "city": "武汉市",
                    "limit": 18,
                },
                "reason": "Broaden search after empty, blocked, or failed first attempt.",
            }
        )

    if not retry_calls and understanding.intent in {"plan_trip", "search_poi", "nearby_support"} and not pois:
        plan = heuristic_tool_plan(understanding)
        retry_calls.extend(item.model_dump() for item in plan.tool_calls)

    return dedupe_tool_calls(retry_calls)[:3]


def dedupe_tool_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for call in calls:
        key = json.dumps({"tool": call.get("tool"), "args": call.get("args") or {}}, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        result.append(call)
    return result


def merge_tool_results(original: list[dict[str, Any]], retry_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [*original, *retry_results]


def maybe_retry_failed_routes_as_walking(
    *,
    db: Session,
    registry: Any,
    original_calls: list[dict[str, Any]],
    route_results: list[dict[str, Any]],
    mode: str,
) -> list[dict[str, Any]]:
    if mode == "walking":
        return route_results
    succeeded_days = {
        int((item.get("result") or {}).get("day_index") or 0)
        for item in route_results
        if item.get("status") == "success"
    }
    retry_calls: list[dict[str, Any]] = []
    for call in original_calls:
        args = dict(call.get("args") or {})
        day_index = int(args.get("day_index") or 0)
        if day_index in succeeded_days:
            continue
        args["mode"] = "walking"
        args["route_name"] = f"{args.get('route_name') or 'Graph route'} walking fallback"
        retry_calls.append({**call, "args": args, "reason": "Fallback to walking after route planning failed."})
    if not retry_calls:
        return route_results
    return [*route_results, *registry.execute_many(db, retry_calls, max_total_calls=3)]


def extract_keywords(message: str) -> list[str]:
    known = ["东湖", "江汉路", "黄鹤楼", "武汉长江大桥", "湖北省博物馆", "光谷", "汉口", "武昌", "汉阳", "亲子", "夜景"]
    found = [item for item in known if item in message]
    if found:
        return found
    match = re.search(r"([\u4e00-\u9fa5]{2,8})(附近|周边|怎么玩|有什么)", message)
    if match:
        return [match.group(1)]
    return []


def collect_pois_from_tool_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in results:
        result = item.get("result") or {}
        for poi in result.get("pois") or []:
            merge_poi(by_id, poi)
        poi = result.get("poi")
        if poi:
            merge_poi(by_id, poi)
    return list(by_id.values())


def merge_poi(by_id: dict[str, dict[str, Any]], poi: dict[str, Any]) -> None:
    poi_id = str(poi.get("id") or "")
    if not poi_id:
        return
    current = by_id.get(poi_id, {})
    merged = {**current, **poi}
    if current.get("profile") and not poi.get("profile"):
        merged["profile"] = current["profile"]
    if current.get("images") and not poi.get("images"):
        merged["images"] = current["images"]
    by_id[poi_id] = merged


def build_cards(pois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for poi in pois[:6]:
        profile = poi.get("profile") or {}
        summary = profile.get("short_intro_zh") or poi.get("address") or poi.get("district") or "武汉 POI"
        cards.append(
            {
                "id": f"graph-poi-{poi.get('id')}",
                "type": "poi_card",
                "title": poi.get("name_zh") or "POI",
                "summary": summary,
            }
        )
    return cards


def build_day_cards(day_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for day in day_plans:
        names = [poi.get("name_zh") for poi in day.get("pois") or [] if poi.get("name_zh")]
        cards.append(
            {
                "id": f"graph-day-{day.get('day_index')}",
                "type": "day_plan_card",
                "title": day.get("theme") or f"Day {day.get('day_index')}",
                "summary": " -> ".join(names) if names else "当天行程已生成，等待更多 POI 数据补充。",
            }
        )
    return cards


def build_graph_day_plans(
    *,
    existing_day_plans: list[dict[str, Any]],
    candidate_pois: list[dict[str, Any]],
    understanding: GraphUnderstanding,
    message: str,
) -> list[dict[str, Any]]:
    days = understanding.days or extract_graph_days(message) or len(existing_day_plans)
    if not days:
        return existing_day_plans
    days = max(1, min(days, 7))
    candidate_ids = [str(poi.get("id")) for poi in candidate_pois if poi.get("id")]
    if not candidate_ids and existing_day_plans:
        return existing_day_plans

    distributed = distribute_graph_pois(candidate_pois, days)
    plans: list[dict[str, Any]] = []
    for index in range(1, days + 1):
        day_pois = distributed[index - 1] if index - 1 < len(distributed) else []
        poi_ids = [str(poi.get("id")) for poi in day_pois if poi.get("id")]
        districts = list(dict.fromkeys(str(poi.get("district")) for poi in day_pois if poi.get("district")))
        plans.append(
            {
                "day_index": index,
                "date": None,
                "theme": build_graph_day_theme(index, day_pois, understanding),
                "districts": districts,
                "poi_ids": poi_ids,
                "pois": day_pois,
                "hotel_id": None,
                "route_id": None,
                "weather_summary": {},
                "notes": [],
                "status": "structured_ready",
            }
        )
    return plans


def distribute_graph_pois(candidate_pois: list[dict[str, Any]], days: int) -> list[list[dict[str, Any]]]:
    result = [[] for _ in range(days)]
    if not candidate_pois:
        return result
    for index, poi in enumerate(candidate_pois[: max(days * 3, days)]):
        result[index % days].append(poi)
    return result


def build_graph_day_theme(index: int, day_pois: list[dict[str, Any]], understanding: GraphUnderstanding) -> str:
    names = [poi.get("name_zh") for poi in day_pois[:2] if poi.get("name_zh")]
    if names:
        return f"Day {index}: " + " / ".join(names)
    if understanding.keywords:
        return f"Day {index}: " + " / ".join(understanding.keywords[:2])
    return f"Day {index}: 武汉轻量游"


def should_plan_graph_routes(understanding: GraphUnderstanding, message: str, day_plans: list[dict[str, Any]]) -> bool:
    if not day_plans:
        return False
    if understanding.intent not in {"plan_trip", "modify_trip"}:
        return False
    if understanding.should_plan_route:
        return True
    return any(word in message for word in ["规划", "行程", "路线", "游玩", "旅游", "玩"])


def choose_graph_route_mode(message: str) -> str:
    if any(word in message for word in ["地铁", "公交", "公共交通"]):
        return "transit"
    if any(word in message for word in ["打车", "开车", "自驾"]):
        return "driving"
    return "walking"


def compact_tool_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for item in results:
        result = item.get("result") or {}
        poi_detail = result.get("poi") if item.get("tool") == "get_poi_detail" else None
        compacted.append(
            {
                "tool": item.get("tool"),
                "status": item.get("status"),
                "summary": item.get("summary"),
                "pois": (result.get("pois") or [])[:10],
                "poi": compact_poi_for_prompt(poi_detail) if poi_detail else None,
                "route": compact_route_for_prompt(result) if item.get("tool") == "plan_day_route" else None,
                "nearby_metro": (result.get("nearby_metro") or [])[:5],
                "nearby_hotels": (result.get("nearby_hotels") or [])[:6],
                "weather": {
                    "current": result.get("current"),
                    "forecast": (result.get("forecast") or [])[:4],
                    "warnings": result.get("warnings") or [],
                } if item.get("tool") == "get_weather" else None,
            }
        )
    return compacted


def compact_route_for_prompt(result: dict[str, Any]) -> dict[str, Any]:
    route = result.get("route") or {}
    return {
        "day_index": result.get("day_index"),
        "route_id": result.get("route_id"),
        "route_name": route.get("route_name"),
        "route_mode": route.get("route_mode"),
        "distance_m": route.get("distance_m"),
        "duration_minutes": route.get("duration_minutes"),
        "poi_ids": result.get("poi_ids") or [],
    }


def compact_poi_for_prompt(poi: dict[str, Any]) -> dict[str, Any]:
    profile = poi.get("profile") or {}
    return {
        "id": poi.get("id"),
        "name_zh": poi.get("name_zh"),
        "district": poi.get("district"),
        "address": poi.get("address"),
        "popularity_score": poi.get("popularity_score"),
        "short_intro_zh": profile.get("short_intro_zh"),
        "recommended_duration_minutes": profile.get("recommended_duration_minutes"),
        "opening_hours": profile.get("opening_hours"),
        "ticket_info": profile.get("ticket_info"),
        "image_count": len(poi.get("images") or []),
    }


def summarize_results_for_state(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for item in results:
        summaries.append(
            {
                "tool": item.get("tool"),
                "status": item.get("status"),
                "summary": item.get("summary") or item.get("error") or "",
            }
        )
    return summaries


def heuristic_reply(state: GraphAgentState) -> str:
    results = state.get("tool_results") or []
    pois = collect_pois_from_tool_results(results)
    if pois:
        names = [poi.get("name_zh") for poi in pois[:6] if poi.get("name_zh")]
        keyword_text = "、".join((state.get("understanding") or {}).get("keywords") or [])
        prefix = f"我先按“{keyword_text}”查了一下数据库，" if keyword_text else "我先查了一下数据库，"
        return (
            f"{prefix}当前能找到这些真实 POI：{'、'.join(names)}。"
            "你可以先围绕这些点做一个轻量玩法：选一两个核心景点慢慢逛，再根据体力补充周边点。"
            "如果你告诉我计划玩几天、是否偏向地铁或亲子/夜景，我可以继续把它整理成按天的路线。"
        )
    weather_result = next((item.get("result") for item in results if item.get("tool") == "get_weather"), None)
    if weather_result:
        forecasts = weather_result.get("forecast") or []
        if forecasts:
            parts = [f"{item.get('date')} {item.get('day_weather')}" for item in forecasts[:3]]
            return "我查到了武汉近期天气：" + "，".join(parts) + "。后续规划时我会把雨天或高温作为约束，减少户外长时间停留。"
    return "我理解你的问题了，但这轮没有查到足够的真实数据。你可以换一个更明确的区域、景点名或偏好，我再继续帮你查。"
