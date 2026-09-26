"""
RIVO Backend — Route Comparison API Endpoint
=============================================
POST /api/v1/routes/compare

Computes routes for all requested modes between origin and destination.
Uses the CompositeRouteProvider (Google → OTP → Mock fallback chain).

Response includes:
  - Duration, distance, fare, transfers for each mode
  - UI badges: fastest / cheapest / fewest transfers / preferred
  - data_freshness per mode (LIVE / RECENT / ESTIMATED)
  - Provider identity (never hidden)

Cost limit: Caller must not use this endpoint to batch-route
hundreds of listings — use the recommendations endpoint instead.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.schemas.routing import RouteComparison, RouteRequest
from app.services.providers.registry import get_route_provider

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post(
    "/compare",
    response_model=RouteComparison,
    summary="Compare routes for all modes",
    description=(
        "Computes point-to-point routes for the requested travel modes. "
        "Uses Google Routes API if configured, falls back to OTP then mock. "
        "Route results include freshness label. "
        "DO NOT use this endpoint to bulk-route listings — use /recommendations/search."
    ),
)
async def compare_routes(request: RouteRequest) -> RouteComparison:
    provider = get_route_provider()
    results = await provider.compute_route(request)

    return RouteComparison(
        origin_lat=request.origin_lat,
        origin_lon=request.origin_lon,
        dest_lat=request.dest_lat,
        dest_lon=request.dest_lon,
        routes=results,
        computed_at=datetime.utcnow(),
    )
