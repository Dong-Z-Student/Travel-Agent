from pydantic import BaseModel, Field


class PoiBase(BaseModel):
    id: str
    category_code: str
    name_zh: str
    name_en: str | None = None
    longitude: float
    latitude: float
    district: str | None = None
    address: str | None = None
    tags: list[str] = Field(default_factory=list)
    popularity_score: float | None = None


class PoiListResponse(BaseModel):
    pois: list[PoiBase]


class PoiProfile(BaseModel):
    short_intro_zh: str = ""
    short_intro_en: str | None = None
    full_description_zh: str | None = None
    full_description_en: str | None = None
    recommended_duration_minutes: int | None = None
    opening_hours: str | None = None
    ticket_info: str | None = None
    suitable_time: str | None = None
    suitable_for: list[str] = Field(default_factory=list)
    manual_tags: list[str] = Field(default_factory=list)


class PoiImage(BaseModel):
    url: str
    image_url: str
    caption: str | None = None
    caption_zh: str | None = None


class PoiDetail(PoiBase):
    profile: PoiProfile
    images: list[PoiImage] = Field(default_factory=list)
