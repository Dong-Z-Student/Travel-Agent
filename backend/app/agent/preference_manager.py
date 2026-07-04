from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.schemas.user import PreferenceCreate
from app.services.user_service import create_preference


LONG_TERM_MARKERS = ("以后", "今后", "一般", "通常", "都希望", "每次", "一直", "长期")
TEMPORARY_MARKERS = ("这次", "今天", "明天", "后天", "临时", "本次", "这趟")

PREFERENCE_RULES = (
    ("transport", "地铁优先", ("地铁优先", "地铁方便", "坐地铁", "轨道交通")),
    ("transport", "打车方便", ("打车方便", "打车优先", "打车", "出租车")),
    ("transport", "少走路", ("不想走太多", "少走路", "走路少", "不喜欢走太多")),
    ("pace", "轻松", ("轻松", "不累", "慢一点", "悠闲")),
    ("crowd", "避开人多", ("不喜欢人多", "避开人多", "人少", "清净")),
    ("theme", "历史文化", ("历史文化", "历史", "博物馆", "人文")),
    ("weather", "雨天少户外", ("下雨少户外", "雨天少户外", "下雨就少安排户外")),
)


@dataclass(frozen=True)
class ExtractedPreference:
    preference_type: str
    preference_value: str
    confidence: float = 1.0
    source: str = "agent_extracted_explicit"


def extract_explicit_long_term_preferences(message: str, model_values: Iterable[str] | None = None) -> list[ExtractedPreference]:
    if is_temporary_preference(message):
        return []

    values: list[ExtractedPreference] = []
    explicit = is_long_term_preference(message)
    for preference_type, preference_value, keywords in PREFERENCE_RULES:
        if any(keyword in message for keyword in keywords) and explicit:
            values.append(ExtractedPreference(preference_type=preference_type, preference_value=preference_value))

    for raw_value in model_values or []:
        normalized = normalize_model_preference(raw_value)
        if normalized and explicit:
            values.append(normalized)

    return dedupe_preferences(values)


def extract_temporary_preferences(message: str, model_values: Iterable[str] | None = None) -> list[str]:
    values: list[str] = []
    for _, preference_value, keywords in PREFERENCE_RULES:
        if any(keyword in message for keyword in keywords):
            values.append(preference_value)
    values.extend(str(item) for item in model_values or [] if item)
    return list(dict.fromkeys(values))


def save_explicit_preferences(db: Session, user: CurrentUser | None, preferences: list[ExtractedPreference]) -> list[dict]:
    if not user or not preferences:
        return []
    saved: list[dict] = []
    for item in preferences:
        saved.append(
            create_preference(
                db,
                user,
                PreferenceCreate(
                    preference_type=item.preference_type,
                    preference_value=item.preference_value,
                    confidence=item.confidence,
                    source=item.source,
                ),
            )
        )
    return saved


def is_long_term_preference(message: str) -> bool:
    return any(marker in message for marker in LONG_TERM_MARKERS)


def is_temporary_preference(message: str) -> bool:
    return any(marker in message for marker in TEMPORARY_MARKERS)


def normalize_model_preference(value: str) -> ExtractedPreference | None:
    text = str(value).strip()
    if not text:
        return None
    for preference_type, preference_value, keywords in PREFERENCE_RULES:
        if text == preference_value or any(keyword in text for keyword in keywords):
            return ExtractedPreference(preference_type=preference_type, preference_value=preference_value)
    return ExtractedPreference(preference_type="general", preference_value=text, confidence=0.8)


def dedupe_preferences(values: list[ExtractedPreference]) -> list[ExtractedPreference]:
    deduped: dict[tuple[str, str], ExtractedPreference] = {}
    for item in values:
        deduped[(item.preference_type, item.preference_value)] = item
    return list(deduped.values())
