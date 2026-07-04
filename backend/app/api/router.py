from fastapi import APIRouter

from app.api.v1 import agent, analysis, health, pois, routes, spatial_query, users, weather

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(pois.router, prefix="/pois", tags=["pois"])
api_router.include_router(spatial_query.router, prefix="/spatial-query", tags=["spatial-query"])
api_router.include_router(routes.router, prefix="/routes", tags=["routes"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
