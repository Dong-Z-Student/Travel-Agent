from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session


class GetUserPreferencesArgs(BaseModel):
    user_id: str


class UserPreferenceItem(BaseModel):
    id: str
    preference_type: str
    preference_value: str
    confidence: float
    source: str | None = None


class GetUserPreferencesResult(BaseModel):
    user_id: str
    preferences: list[UserPreferenceItem] = Field(default_factory=list)


def get_user_preferences_tool(db: Session, args: GetUserPreferencesArgs) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            select
                id::text,
                preference_type,
                preference_value,
                confidence,
                source
            from public.user_preferences
            where user_id = cast(:user_id as uuid)
              and is_active = true
            order by preference_type, preference_value
            """
        ),
        {"user_id": args.user_id},
    ).mappings().all()
    result = GetUserPreferencesResult(
        user_id=args.user_id,
        preferences=[
            UserPreferenceItem(
                id=row["id"],
                preference_type=row["preference_type"],
                preference_value=row["preference_value"],
                confidence=float(row["confidence"]),
                source=row.get("source"),
            )
            for row in rows
        ],
    )
    return result.model_dump()
