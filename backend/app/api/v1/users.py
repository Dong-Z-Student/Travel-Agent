from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.user import DeletePreferenceResponse, PreferenceCreate, PreferenceListResponse, PreferenceResponse, UserProfileResponse
from app.services.user_service import create_preference as create_preference_service
from app.services.user_service import delete_preference as delete_preference_service
from app.services.user_service import ensure_user_profile
from app.services.user_service import list_preferences as list_preferences_service

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    profile = ensure_user_profile(db, current_user)
    return UserProfileResponse(**profile)


@router.get("/me/preferences", response_model=PreferenceListResponse)
def list_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreferenceListResponse:
    preferences = list_preferences_service(db, current_user)
    return PreferenceListResponse(preferences=preferences)


@router.post("/me/preferences", response_model=PreferenceResponse)
def create_preference(
    payload: PreferenceCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreferenceResponse:
    preference = create_preference_service(db, current_user, payload)
    return PreferenceResponse(**preference)


@router.delete("/me/preferences/{preference_id}", response_model=DeletePreferenceResponse)
def delete_preference(
    preference_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeletePreferenceResponse:
    deleted = delete_preference_service(db, current_user, preference_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")
    return DeletePreferenceResponse(success=True)
