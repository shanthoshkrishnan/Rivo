"""
RIVO Backend — System Diagnostics API Endpoint (Phase 13)
=========================================================
GET /api/v1/system/integrations

Reports live integration status for:
  - Google Maps (configured / status)
  - Google Places (configured / status)
  - Google Routes (configured / status)
  - Rental Provider (RIVO_DIRECT / open_dataset / licensed)
  - GTFS Transit Engine (AVAILABLE)
  
NEVER returns API keys, secrets, or internal credentials.
"""
from __future__ import annotations

from fastapi import APIRouter
from app.core.config import get_settings
from app.core.circuit_breaker import circuit_breaker

router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()


@router.get(
    "/integrations",
    summary="Get status of system data providers and Google integrations",
    description="Returns public-safe provider configuration status without revealing secrets."
)
async def get_system_integrations() -> dict:
    routes_status = circuit_breaker.get_routes_status()
    places_status = circuit_breaker.get_places_status()

    return {
        "google_maps": "CONFIGURED",
        "google_places": "CONFIGURED" if settings.google_places_enabled else "FALLBACK_ACTIVE",
        "google_routes": "CONFIGURED" if settings.google_routes_enabled else "FALLBACK_ACTIVE",
        "rental_provider": settings.RENTAL_PROVIDER.upper(),
        "gtfs": "AVAILABLE",
        "places_circuit": "HEALTHY" if places_status["available"] else places_status["reason"],
        "routes_circuit": "HEALTHY" if routes_status["available"] else routes_status["reason"],
        "mock_mode": not (settings.google_routes_enabled or settings.google_places_enabled),
    }
