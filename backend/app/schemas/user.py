from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: str
    email: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    home_city: str | None = None


class PreferenceCreate(BaseModel):
    preference_type: str = Field(min_length=1, max_length=80)
    preference_value: str = Field(min_length=1, max_length=160)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: str = Field(default="user_explicit", min_length=1, max_length=80)


class PreferenceResponse(BaseModel):
    id: str
    preference_type: str
    preference_value: str
    confidence: float
    source: str
    is_active: bool


class PreferenceListResponse(BaseModel):
    preferences: list[PreferenceResponse]


class DeletePreferenceResponse(BaseModel):
    success: bool
