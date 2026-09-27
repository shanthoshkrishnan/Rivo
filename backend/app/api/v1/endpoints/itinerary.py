"""
RIVO Backend — Live Itinerary API Endpoint
===========================================
POST /api/v1/routes/itinerary

Returns the full door-to-door transit itinerary for a selected
home × workplace × departure time combination.

This is the "selected listing" endpoint — it is NOT called for
every search result. Only called when the user selects a specific
home to view the full trip plan.

Response:
  - Full RouteResult with steps
  - Each step: walk / transit (agency, line, headsign, stop names,
    departure time, arrival time, vehicle type)
  - Fare where available from provider
  - Data provenance (provider, freshness, observed_at)

Fallback:
  Google Routes → GTFS → OTP → Mock

Never calls this endpoint for batch-routing of search results.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.schemas.routing import RouteComparison, RouteRequest, RouteResult
from app.services.providers.registry import get_route_provider

router = APIRouter(prefix="/routes", tags=["routes"])


class ItineraryRequest(BaseModel):
    """
    Request a full door-to-door itinerary for a selected home × workplace pair.

    home_lat / home_lon  — the selected rental listing coordinates
    workplace_lat / workplace_lon — the target workplace coordinates
    departure_time       — desired departure time (ISO-8601); defaults to now
    mode                 — single mode to compute: TRANSIT | DRIVE | TWO_WHEELER | WALK
    """
    home_lat: float = Field(..., ge=-90, le=90)
    home_lon: float = Field(..., ge=-180, le=180)
    workplace_lat: float = Field(..., ge=-90, le=90)
    workplace_lon: float = Field(..., ge=-180, le=180)
    departure_time: datetime | None = None
    mode: str = "TRANSIT"


@router.post(
    "/itinerary",
    response_model=RouteResult,
    summary="Full door-to-door itinerary for a selected home",
    description=(
        "Computes the full step-by-step transit itinerary for one home × workplace pair. "
        "This endpoint is for the selected listing detail view ONLY — "
        "do NOT call it for every search result. "
        "Uses Google Routes API if configured; falls back to GTFS → OTP → Mock. "
        "Response includes all transit steps: walk, board, transfer, alight, walk. "
        "Freshness label indicates whether result is LIVE or a fallback."
    ),
)
async def get_itinerary(request: ItineraryRequest) -> RouteResult:
    dep_time = request.departure_time
    if dep_time is None:
        dep_time = datetime.now(timezone.utc)

    route_request = RouteRequest(
        origin_lat=request.home_lat,
        origin_lon=request.home_lon,
        dest_lat=request.workplace_lat,
        dest_lon=request.workplace_lon,
        departure_time=dep_time,
        modes=[request.mode.upper()],
    )

    provider = get_route_provider()
    results = await provider.compute_route(route_request)

    if not results:
        # Return a minimal mock result to keep the UI responsive
        from app.services.providers.route_mock import MockRouteProvider
        mock = MockRouteProvider()
        results = await mock.compute_route(route_request)

    if not results:
        from app.schemas.routing import RouteResult as RR
        from app.core.config import DataFreshness
        return RR(
            mode=request.mode.upper(),
            provider="mock",
            data_freshness=DataFreshness.ESTIMATED,
            source_label="No route computed — check origin/destination coordinates",
        )

    best = results[0]
    logger.info(
        "[ROUTE] Itinerary served",
        mode=best.mode,
        provider=best.provider,
        freshness=best.data_freshness,
        duration_sec=best.duration_seconds,
        steps=len(best.steps),
    )
    return best
