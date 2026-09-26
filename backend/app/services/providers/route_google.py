"""
RIVO Backend — Google Routes API Provider
==========================================
Implements RouteProvider using Google Routes API v2.

Key rules enforced here:
  1. API key is required — if absent, raises ProviderUnavailableError.
  2. Results are cached in Redis before returning (route_cache table).
     Caching must comply with Google Maps Platform ToS:
       - Do not persist indefinitely; respect ROUTE_CACHE_TTL.
       - Do not use cached results for offline map rendering.
  3. departure_bucket rounds time to 30-min windows to maximise cache hits.
  4. If the API call fails, raise ProviderUnavailableError so the caller
     can fall back to OTP or mock.
  5. All RouteResults are tagged provider="google", freshness=LIVE
     (or RECENT if from cache).

Reference: https://developers.google.com/maps/documentation/routes/
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.db.cache import cache_get, cache_set, make_cache_key
from app.schemas.routing import RouteRequest, RouteResult
from app.services.providers.base import RouteProvider

settings = get_settings()

GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Map RIVO mode names to Google travel mode enum values
_MODE_MAP = {
    "TRANSIT": "TRANSIT",
    "DRIVE": "DRIVE",
    "TWO_WHEELER": "TWO_WHEELER",
    "WALK": "WALK",
}


class ProviderUnavailableError(Exception):
    """Raised when a routing provider cannot fulfil a request."""


def _bucket_time(dt: Optional[datetime]) -> str:
    """Round to 30-minute bucket for cache key."""
    if dt is None:
        return "default"
    minute = (dt.minute // 30) * 30
    return f"{dt.hour:02d}:{minute:02d}"


class GoogleRouteProvider(RouteProvider):
    """
    Live routing via Google Routes API v2.

    Modes supported: TRANSIT, DRIVE, TWO_WHEELER, WALK.
    Each mode requires a separate API call (Google API limitation).

    Cost control:
      - Use Redis cache first (ROUTE_CACHE_TTL seconds).
      - Only call the API for cache misses.
      - Caller is responsible for not routing more than ~200 listings.
    """

    PROVIDER_NAME = "google"
    SUPPORTED_MODES = {"TRANSIT", "DRIVE", "TWO_WHEELER", "WALK"}

    def __init__(self) -> None:
        self._api_key = settings.GOOGLE_ROUTES_API_KEY

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        return bool(self._api_key)

    def supports_mode(self, mode: str) -> bool:
        return mode.upper() in self.SUPPORTED_MODES

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call_api(self, payload: dict) -> dict:
        """Make a single Google Routes API call with retry."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                GOOGLE_ROUTES_URL,
                json=payload,
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": (
                        "routes.duration,routes.distanceMeters,"
                        "routes.travelAdvisory,routes.legs,"
                        "routes.polyline"
                    ),
                },
            )
            resp.raise_for_status()
            return resp.json()

    def _parse_response(
        self, data: dict, mode: str, bucket: str
    ) -> Optional[RouteResult]:
        routes = data.get("routes", [])
        if not routes:
            return None
        route = routes[0]
        legs = route.get("legs", [{}])
        leg = legs[0] if legs else {}

        # Duration comes as "123s" from Google
        duration_str = route.get("duration", "0s")
        duration_sec = int(duration_str.rstrip("s"))

        # Transit-specific fields
        walk_sec = 0
        wait_sec = 0
        in_vehicle_sec = 0
        transfer_count = 0
        fare_amount: Optional[float] = None

        if mode == "TRANSIT":
            # Parse transit-specific advisory
            advisory = route.get("travelAdvisory", {})
            # Fare (may not always be present)
            fare_info = advisory.get("transitFare", {})
            if fare_info:
                fare_amount = float(fare_info.get("units", 0))

        geometry = None
        polyline = route.get("polyline", {})
        if polyline.get("encodedPolyline"):
            geometry = polyline["encodedPolyline"]

        return RouteResult(
            mode=mode,
            provider=self.PROVIDER_NAME,
            distance_m=float(route.get("distanceMeters", 0)),
            duration_seconds=duration_sec,
            walk_seconds=walk_sec,
            wait_seconds=wait_sec,
            in_vehicle_seconds=in_vehicle_sec,
            transfer_count=transfer_count,
            fare_amount=fare_amount,
            route_geometry=geometry,
            observed_at=datetime.now(timezone.utc),
            data_freshness=DataFreshness.LIVE,
        )

    async def compute_route(self, request: RouteRequest) -> List[RouteResult]:
        if not self.is_available():
            raise ProviderUnavailableError("Google Routes API key not configured")

        bucket = _bucket_time(request.departure_time)
        results: List[RouteResult] = []

        for mode in request.modes:
            mode_upper = mode.upper()
            if mode_upper not in self.SUPPORTED_MODES:
                continue

            # Cache check
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
                logger.debug("Route cache hit", mode=mode_upper)
                continue

            # Live API call
            try:
                google_mode = _MODE_MAP[mode_upper]
                payload = {
                    "origin": {
                        "location": {
                            "latLng": {
                                "latitude": request.origin_lat,
                                "longitude": request.origin_lon,
                            }
                        }
                    },
                    "destination": {
                        "location": {
                            "latLng": {
                                "latitude": request.dest_lat,
                                "longitude": request.dest_lon,
                            }
                        }
                    },
                    "travelMode": google_mode,
                    "routingPreference": (
                        "TRAFFIC_AWARE" if google_mode in ("DRIVE", "TWO_WHEELER") else None
                    ),
                    "computeAlternativeRoutes": False,
                    "languageCode": "en-IN",
                    "units": "METRIC",
                }
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}

                data = await self._call_api(payload)
                result = self._parse_response(data, mode_upper, bucket)
                if result:
                    await cache_set(cache_key, result.model_dump(mode="json"), settings.ROUTE_CACHE_TTL)
                    results.append(result)
            except ProviderUnavailableError:
                raise
            except Exception as exc:
                logger.error("Google Routes API error", mode=mode_upper, error=str(exc))
                raise ProviderUnavailableError(f"Google Routes failed for {mode_upper}: {exc}") from exc

        # Badge assignment
        _assign_badges(results)
        return results


def _assign_badges(results: List[RouteResult]) -> None:
    """Mark fastest, cheapest, fewest-transfers badges."""
    valid_dur = [r for r in results if r.duration_seconds is not None]
    valid_fare = [r for r in results if r.fare_amount is not None]
    valid_xfer = [r for r in results if r.transfer_count is not None]
    if valid_dur:
        min(valid_dur, key=lambda r: r.duration_seconds).is_fastest = True   # type: ignore
    if valid_fare:
        min(valid_fare, key=lambda r: r.fare_amount).is_cheapest = True      # type: ignore
    if valid_xfer:
        min(valid_xfer, key=lambda r: r.transfer_count).is_fewest_transfers = True  # type: ignore
