"""
RIVO Backend — API v1 Router
==============================
Assembles all v1 endpoints under /api/v1.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    data_sources,
    facilities,
    recommendations,
    rentals,
    routes,
    scenarios,
    workers,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(rentals.router)
api_router.include_router(routes.router)
api_router.include_router(facilities.router)
api_router.include_router(recommendations.router)
api_router.include_router(workers.router)
api_router.include_router(scenarios.router)
api_router.include_router(data_sources.router)
