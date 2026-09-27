"""
RIVO Backend — API v1 Router
==============================
Assembles all v1 endpoints under /api/v1.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    data_sources,
    facilities,
    itinerary,
    recommendations,
    rentals,
    routes,
    scenarios,
    system,
    workers,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(rentals.router)
api_router.include_router(routes.router)
api_router.include_router(itinerary.router)
api_router.include_router(facilities.router)
api_router.include_router(recommendations.router)
api_router.include_router(workers.router)
api_router.include_router(scenarios.router)
api_router.include_router(data_sources.router)
api_router.include_router(system.router)


@api_router.get(
    "/data-quality/rentals",
    summary="Data Quality Diagnostic (Requirement 33)",
    tags=["admin"],
)
async def data_quality_rentals_alias():
    return await rentals.get_demo_data_quality()
