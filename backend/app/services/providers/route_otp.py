"""
RIVO Backend — OpenTripPlanner 2.10 Route Provider
===================================================
Provides multimodal transit routing via a local or remote OTP instance.
OTP is the open/reproducible fallback when Google Routes is unavailable
or for batch accessibility analysis.

Setup: Run OTP with the CUMTA GTFS feed + OSM road network for Chennai.
Docs: https://docs.opentripplanner.org/en/v2.6.0/

This provider uses the OTP REST API (GraphQL):
  POST {OTP_BASE_URL}/routers/default/index/graphql

Results are cached using the same Redis key scheme as GoogleRouteProvider
so the rest of the application sees a unified cache.

Freshness: LIVE on first call, RECENT from cache, PERIODIC if OTP
           is running from a static GTFS snapshot.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.db.cache import cache_get, cache_set, make_cache_key
from app.schemas.routing import RouteRequest, RouteResult
from app.services.providers.base import RouteProvider
from app.services.providers.route_google import ProviderUnavailableError, _assign_badges

settings = get_settings()

# OTP GraphQL query for a single itinerary
_OTP_GRAPHQL_QUERY = """
query Plan($fromLat: Float!, $fromLon: Float!, $toLat: Float!, $toLon: Float!, $mode: [TransportMode]) {
  plan(
    from: {lat: $fromLat, lon: $fromLon}
    to: {lat: $toLat, lon: $toLon}
    transportModes: $mode
    numItineraries: 1
  ) {
    itineraries {
      duration
      legs {
        mode
        distance
        duration
        generalizedCost
      }
      walkTime
      waitingTime
      transferCount
      fares {
        fare {
          currency { code }
          cents
        }
      }
    }
  }
}
"""

_OTP_MODE_MAP = {
    "TRANSIT": [{"mode": "TRANSIT"}],
    "WALK": [{"mode": "WALK"}],
    "DRIVE": [{"mode": "CAR"}],
    "TWO_WHEELER": [{"mode": "SCOOTER"}],
}


def _bucket_time(dt: Optional[datetime]) -> str:
    if dt is None:
        return "default"
    minute = (dt.minute // 30) * 30
    return f"{dt.hour:02d}:{minute:02d}"


class OTPRouteProvider(RouteProvider):
    """
    Route provider backed by OpenTripPlanner 2.10.
    Requires a running OTP instance with CUMTA GTFS + OSM loaded.
    """

    PROVIDER_NAME = "otp"
    SUPPORTED_MODES = {"TRANSIT", "WALK", "DRIVE", "TWO_WHEELER"}

    def __init__(self) -> None:
        self._base_url = settings.OTP_BASE_URL.rstrip("/")
        self._graphql_url = f"{self._base_url}/routers/default/index/graphql"

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        # Optimistic: we check lazily on first request
        return True

    def supports_mode(self, mode: str) -> bool:
        return mode.upper() in self.SUPPORTED_MODES

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call_otp(self, variables: Dict[str, Any]) -> Dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                self._graphql_url,
                json={"query": _OTP_GRAPHQL_QUERY, "variables": variables},
            )
            resp.raise_for_status()
            return resp.json()

    def _parse_itinerary(
        self, itinerary: Dict, mode: str
    ) -> Optional[RouteResult]:
        if not itinerary:
            return None
        duration_sec = int(itinerary.get("duration", 0))
        walk_sec = int(itinerary.get("walkTime", 0))
        wait_sec = int(itinerary.get("waitingTime", 0))
        in_vehicle_sec = max(0, duration_sec - walk_sec - wait_sec)
        transfers = int(itinerary.get("transferCount", 0))

        # Fare (optional; OTP fare plugins required for accurate fares)
        fare_amount: Optional[float] = None
        fares = itinerary.get("fares", [])
        if fares:
            try:
                cents = fares[0]["fare"]["cents"]
                fare_amount = cents / 100.0
            except (KeyError, IndexError, TypeError):
                pass

        legs = itinerary.get("legs", [])
        total_distance_m = sum(leg.get("distance", 0) for leg in legs)

        return RouteResult(
            mode=mode,
            provider=self.PROVIDER_NAME,
            distance_m=total_distance_m,
            duration_seconds=duration_sec,
            walk_seconds=walk_sec,
            wait_seconds=wait_sec,
            in_vehicle_seconds=in_vehicle_sec,
            transfer_count=transfers,
            fare_amount=fare_amount,
            route_geometry=None,
            observed_at=datetime.now(timezone.utc),
            data_freshness=DataFreshness.LIVE,
        )

    async def compute_route(self, request: RouteRequest) -> List[RouteResult]:
        bucket = _bucket_time(request.departure_time)
        results: List[RouteResult] = []

        for mode in request.modes:
            mode_upper = mode.upper()
            if mode_upper not in self.SUPPORTED_MODES:
                continue

            cache_key = make_cache_key(
                "route",
                origin_lat=round(request.origin_lat, 4),
                origin_lon=round(request.origin_lon, 4),
                dest_lat=round(request.dest_lat, 4),
                dest_lon=round(request.dest_lon, 4),
                mode=mode_upper,
                departure_bucket=bucket,
                provider=self.PROVIDER_NAME,
            )
            cached = await cache_get(cache_key)
            if cached:
                result = RouteResult(**cached)
                result.data_freshness = DataFreshness.RECENT
                results.append(result)
                continue

            try:
                variables = {
                    "fromLat": request.origin_lat,
                    "fromLon": request.origin_lon,
                    "toLat": request.dest_lat,
                    "toLon": request.dest_lon,
                    "mode": _OTP_MODE_MAP.get(mode_upper, [{"mode": mode_upper}]),
                }
                data = await self._call_otp(variables)
                itineraries = (
                    data.get("data", {})
                    .get("plan", {})
                    .get("itineraries", [])
                )
                if itineraries:
                    result = self._parse_itinerary(itineraries[0], mode_upper)
                    if result:
                        await cache_set(
                            cache_key,
                            result.model_dump(mode="json"),
                            settings.ROUTE_CACHE_TTL,
                        )
                        results.append(result)
            except Exception as exc:
                logger.error("OTP routing error", mode=mode_upper, error=str(exc))
                # Don't raise; return partial results and let caller handle fallback

        _assign_badges(results)
        return results
