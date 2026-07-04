from pydantic import BaseModel, Field


class HeatPoint(BaseModel):
    longitude: float
    latitude: float
    weight: float


class PopulationHeatmapResponse(BaseModel):
    points: list[HeatPoint] = Field(default_factory=list)
