"""
RIVO Backend — Mock Route Provider
=====================================
Provides deterministic route estimates for all four modes
without any external API calls.  Used in:
  - development / CI environments
  - demo mode when Google Routes API key is not configured
  - fallback when both Google and OTP are unavailable

Estimation method:
  - Straight-line (Haversine) distance between origin and destination
  - Mode-specific speed and cost multipliers calibrated for Chennai
  - NOT suitable for precise directions or real-time traffic

Every RouteResult is tagged:
  provider   = "mock"
  freshness  = ESTIMATED

The UI must display:
  "Estimated route — not a live navigation result"
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List

from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.schemas.routing import RouteRequest, RouteResult
from app.services.providers.base import RouteProvider

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Chennai-calibrated mode parameters
# ─────────────────────────────────────────────────────────────────────────────
_MODE_PARAMS: dict[str, dict] = {
    "WALK": {
        "speed_kmh": 4.5,
        "route_factor": 1.4,    # actual path ≈ 1.4× straight line
        "fare_inr": 0.0,
        "transfer_count": 0,
        "walk_fraction": 1.0,
    },
    "TRANSIT": {
        "speed_kmh": 22.0,
        "route_factor": 1.5,
        "fare_inr_per_km": 1.5,    # ~MTC ordinary bus
        "min_fare": 7.0,
        "transfer_count": 1,
        "walk_fraction": 0.2,
        "wait_fraction": 0.15,
    },
    "TWO_WHEELER": {
        "speed_kmh": 28.0,
        "route_factor": 1.3,
        "efficiency_kmpl": None,   # read from settings
        "transfer_count": 0,
        "walk_fraction": 0.0,
    },
    "DRIVE": {
        "speed_kmh": 22.0,
        "route_factor": 1.35,
        "efficiency_kmpl": None,
        "transfer_count": 0,
        "walk_fraction": 0.0,
    },
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class MockRouteProvider(RouteProvider):
    """
    Deterministic route estimator for all modes.
    Suitable for demos, tests and environments without routing APIs.

    IMPORTANT: Results are coarse estimates, not real routes.
    Always tag returned RouteResults with freshness=ESTIMATED.
    """

    PROVIDER_NAME = "mock"
    SUPPORTED_MODES = {"WALK", "TRANSIT", "TWO_WHEELER", "DRIVE"}

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        return True

    def supports_mode(self, mode: str) -> bool:
        return mode.upper() in self.SUPPORTED_MODES

    async def compute_route(self, request: RouteRequest) -> List[RouteResult]:
        distance_km = _haversine_km(
            request.origin_lat, request.origin_lon,
            request.dest_lat, request.dest_lon,
        )
        results: List[RouteResult] = []

        for mode in request.modes:
            mode_upper = mode.upper()
            if mode_upper not in self.SUPPORTED_MODES:
                continue

            params = _MODE_PARAMS[mode_upper]
            route_distance_km = distance_km * params["route_factor"]
            speed = params["speed_kmh"]
            duration_sec = int((route_distance_km / speed) * 3600)

            # Fare estimation
            if mode_upper == "WALK":
                fare = 0.0
                walk_sec = duration_sec
                wait_sec = 0
                in_vehicle_sec = 0
                transfers = 0
            elif mode_upper == "TRANSIT":
                fare = max(
                    params["min_fare"],
                    round(route_distance_km * params["fare_inr_per_km"], 0),
                )
                walk_sec = int(duration_sec * params["walk_fraction"])
                wait_sec = int(duration_sec * params["wait_fraction"])
                in_vehicle_sec = duration_sec - walk_sec - wait_sec
                transfers = params["transfer_count"]
            elif mode_upper == "TWO_WHEELER":
                eff = settings.TWO_WHEELER_EFFICIENCY_KMPL
                petrol_price = settings.DEFAULT_PETROL_PRICE_INR
                fare = round((route_distance_km / eff) * petrol_price, 2)
                walk_sec = 0
                wait_sec = 0
                in_vehicle_sec = duration_sec
                transfers = 0
            else:  # DRIVE
                eff = settings.CAR_EFFICIENCY_KMPL
                petrol_price = settings.DEFAULT_PETROL_PRICE_INR
                fare = round((route_distance_km / eff) * petrol_price, 2)
                walk_sec = 0
                wait_sec = 0
                in_vehicle_sec = duration_sec
                transfers = 0

            results.append(RouteResult(
                mode=mode_upper,
                provider=self.PROVIDER_NAME,
                distance_m=round(route_distance_km * 1000, 0),
                duration_seconds=duration_sec,
                walk_seconds=walk_sec,
                wait_seconds=wait_sec,
                in_vehicle_seconds=in_vehicle_sec,
                transfer_count=transfers,
                fare_amount=fare,
                route_geometry=None,    # no polyline for mock
                observed_at=datetime.now(timezone.utc),
                data_freshness=DataFreshness.ESTIMATED,
            ))

        # Apply UI badges
        if results:
            by_duration = sorted([r for r in results if r.duration_seconds is not None], key=lambda r: r.duration_seconds)
            by_fare = sorted([r for r in results if r.fare_amount is not None], key=lambda r: r.fare_amount)
            by_transfers = sorted([r for r in results if r.transfer_count is not None], key=lambda r: r.transfer_count)
            if by_duration:
                by_duration[0].is_fastest = True
            if by_fare:
                by_fare[0].is_cheapest = True
            if by_transfers:
                by_transfers[0].is_fewest_transfers = True

        logger.debug(
            "MockRouteProvider computed routes",
            modes=[r.mode for r in results],
            distance_km=round(distance_km, 2),
        )
        return results
