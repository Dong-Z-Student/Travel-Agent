from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.schemas.user import PreferenceCreate


def ensure_user_profile(db: Session, user: CurrentUser) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            insert into public.user_profiles (id, nickname, home_city)
            values (cast(:user_id as uuid), :nickname, '武汉市')
            on conflict (id) do update
            set updated_at = now()
            returning id::text, nickname, avatar_url, home_city
            """
        ),
        {
            "user_id": user.id,
            "nickname": user.email.split("@", 1)[0] if user.email else None,
        },
    ).mappings().first()
    db.commit()
    return {
        "id": row["id"],
        "email": user.email,
        "nickname": row.get("nickname"),
        "avatar_url": row.get("avatar_url"),
        "home_city": row.get("home_city"),
    }


def list_preferences(db: Session, user: CurrentUser) -> list[dict[str, Any]]:
    ensure_user_profile(db, user)
    rows = db.execute(
        text(
            """
            select
                id::text,
                preference_type,
                preference_value,
                confidence,
                source,
                is_active
            from public.user_preferences
            where user_id = cast(:user_id as uuid)
              and is_active = true
            order by preference_type, preference_value
            """
        ),
        {"user_id": user.id},
    ).mappings().all()
    return [map_preference(row) for row in rows]


def create_preference(db: Session, user: CurrentUser, payload: PreferenceCreate) -> dict[str, Any]:
    ensure_user_profile(db, user)
    row = db.execute(
        text(
            """
            insert into public.user_preferences (
                user_id,
                preference_type,
                preference_value,
                confidence,
                source,
                is_active
            )
            values (
                cast(:user_id as uuid),
                :preference_type,
                :preference_value,
                :confidence,
                :source,
                true
            )
            on conflict (user_id, preference_type, preference_value) do update
            set
                confidence = excluded.confidence,
                source = excluded.source,
                is_active = true,
                updated_at = now()
            returning
                id::text,
                preference_type,
                preference_value,
                confidence,
                source,
                is_active
            """
        ),
        {
            "user_id": user.id,
            "preference_type": payload.preference_type,
            "preference_value": payload.preference_value,
            "confidence": payload.confidence,
            "source": payload.source,
        },
    ).mappings().first()
    db.commit()
    return map_preference(row)


def delete_preference(db: Session, user: CurrentUser, preference_id: str) -> bool:
    ensure_user_profile(db, user)
    row = db.execute(
        text(
            """
            update public.user_preferences
            set is_active = false, updated_at = now()
            where id = cast(:preference_id as uuid)
              and user_id = cast(:user_id as uuid)
              and is_active = true
            returning id
            """
        ),
        {"preference_id": preference_id, "user_id": user.id},
    ).first()
    db.commit()
    return row is not None


def map_preference(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "preference_type": row["preference_type"],
        "preference_value": row["preference_value"],
        "confidence": float(row["confidence"]),
        "source": row["source"],
        "is_active": row["is_active"],
    }
