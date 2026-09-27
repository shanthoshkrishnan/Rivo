"""
RIVO Backend — Google Places Provider (Phase 3)
================================================
Implements PlacesProvider using Google Places API (New) Nearby Search.

Rules enforced:
  1. API key required — returns empty list if not configured.
  2. Only required fields are requested (field mask).
  3. Results are labelled LIVE (fresh from API) or RECENT (from cache).
  4. Fallback: local verified seed data labelled PERIODIC.
  5. Never store reviews, photos, or unnecessary personal data.
  6. Targeted small-radius searches; not called for every listing.

Fields requested per facility result:
  - id (place_id)
  - displayName (name)
  - location (lat/lon)
  - formattedAddress

Facility types mapped to Google includedTypes:
  school    → "school"
  hospital  → "hospital"
  pharmacy  → "pharmacy"
  transit   → "transit_station"

Reference: https://developers.google.com/maps/documentation/places/web-service/nearby-search
"""
from __future__ import annotations

import time
from typing import Any, List, Optional
import unittest.mock
import uuid
from datetime import datetime, timezone

import httpx

from app.core.circuit_breaker import circuit_breaker
from app.core.config import DataFreshness, get_settings
from app.core.logging import logger
from app.core.request_tracker import get_current_tracker
from app.db.cache import cache_get, cache_set, make_cache_key
from app.schemas.misc import FacilityOut
from app.services.providers.base import PlacesProvider

settings = get_settings()





# Google Places (New) Nearby Search endpoint
_PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Only the fields we actually use in FacilityOut
_PLACES_FIELD_MASK = "places.id,places.displayName,places.location,places.formattedAddress"

# Cache TTL for Places results (shorter than route cache — Places data changes more often)
_PLACES_CACHE_TTL = 1800  # 30 minutes

_TYPE_MAP = {
    "school": "school",
    "hospital": "hospital",
    "pharmacy": "pharmacy",
    "transit": "transit_station",
    "transit_station": "transit_station",
}


def classify_google_places_error(status_code: int, response_text: str) -> tuple[str, str]:
    """
    Classify Google Places API error without exposing any secrets.
    Returns (category, sanitized_message).
    """
    import json
    category = "OTHER"
    raw_msg = ""
    try:
        data = json.loads(response_text)
        err = data.get("error", {})
        raw_msg = err.get("message", "")
        status = err.get("status", "")
    except Exception:
        raw_msg = response_text[:200]
        status = ""

    lower_msg = raw_msg.lower()

    if status_code in (400, 401) and (
        "api key not valid" in lower_msg
        or "key invalid" in lower_msg
        or "api_key_invalid" in lower_msg
        or ("bad request" in lower_msg and "key" in lower_msg)
    ):
        category = "INVALID_KEY"
    elif "not been used in project" in lower_msg or "api has not been enabled" in lower_msg or "not enabled" in lower_msg:
        category = "API_NOT_ENABLED"
    elif "billing" in lower_msg or "billing_not_enabled" in lower_msg:
        category = "BILLING_REQUIRED"
    elif status_code == 403 or status == "PERMISSION_DENIED" or "permission" in lower_msg:
        category = "PERMISSION_DENIED"
    elif status_code == 429 or status == "RESOURCE_EXHAUSTED" or "quota" in lower_msg or "rate limit" in lower_msg:
        category = "QUOTA_EXCEEDED"
    elif status_code == 400 or status == "INVALID_ARGUMENT":
        category = "INVALID_REQUEST"
    else:
        category = f"HTTP_{status_code}"

    sanitized = raw_msg.split("?key=")[0].split("&key=")[0]
    return category, sanitized


class GooglePlacesProvider(PlacesProvider):
    """
    Live facility search via Google Places API (New).

    Cost control:
      - Cache results by (lat_rounded, lon_rounded, type, radius).
      - Only call for serious finalists, not every listing.
      - Request only required fields via X-Goog-FieldMask.
    """

    PROVIDER_NAME = "google_places"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    @property
    def api_key(self) -> str:
        if self._api_key is not None:
            return self._api_key
        return get_settings().GOOGLE_PLACES_API_KEY

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        if not (self.api_key and self.api_key.strip()):
            return False
        return circuit_breaker.is_places_available()

    async def nearby_facilities(
        self,
        latitude: float,
        longitude: float,
        facility_type: str,
        radius_m: int,
        limit: int,
    ) -> List[FacilityOut]:
        if not self.is_available():
            return []

        google_type = _TYPE_MAP.get(facility_type.lower(), facility_type.lower())
        tracker = get_current_tracker()

        # Cache key (4-decimal rounding ≈ 11 m precision; fine for facility search)
        cache_key = make_cache_key(
            "places",
            lat=round(latitude, 4),
            lon=round(longitude, 4),
            facility_type=google_type,
            radius_m=radius_m,
            provider=self.PROVIDER_NAME,
        )
        cached = await cache_get(cache_key)
        if cached:
            logger.debug("[PLACES] cache hit", facility_type=google_type)
            tracker.record_places_call("google_places", cache_hit=True, latency_ms=0.0, facility_type=facility_type)
            cached_facilities: List[FacilityOut] = []
            for item in cached:
                fac = FacilityOut(**item)
                fac.data_freshness = DataFreshness.RECENT
                fac.source_name = "Google Places API (cached)"
                cached_facilities.append(fac)
            return cached_facilities

        # Check budget before live API call
        if not tracker.can_request_places():
            logger.warning("[PLACES] Request budget reached, skipping live call", facility_type=facility_type)
            return []

        # Live API call
        payload = {
            "includedTypes": [google_type],
            "maxResultCount": min(limit, 20),   # Google caps at 20
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius_m),
                }
            },
        }

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    _PLACES_NEARBY_URL,
                    json=payload,
                    headers={
                        "X-Goog-Api-Key": self.api_key.strip(),
                        "X-Goog-FieldMask": _PLACES_FIELD_MASK,
                    },
                )
                latency_ms = (time.time() - t0) * 1000
                if resp.status_code != 200:
                    category, sanitized = classify_google_places_error(resp.status_code, resp.text)
                    if category == "QUOTA_EXCEEDED" or resp.status_code == 429:
                        circuit_breaker.trip_places("QUOTA_EXCEEDED")
                    logger.warning(
                        "[PLACES] Google Places API error",
                        category=category,
                        status=resp.status_code,
                        message=sanitized,
                    )
                    return []
                data = resp.json()
                tracker.record_places_call("google_places", cache_hit=False, latency_ms=latency_ms, facility_type=facility_type)

            places = data.get("places", [])
            results: List[FacilityOut] = []

            for place in places[:limit]:
                loc = place.get("location", {})
                p_lat = loc.get("latitude")
                p_lon = loc.get("longitude")
                if p_lat is None or p_lon is None:
                    continue

                # Haversine distance
                dist_m_val = _haversine_m(latitude, longitude, p_lat, p_lon)

                name_obj = place.get("displayName", {})
                name = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj)

                results.append(
                    FacilityOut(
                        id=uuid.uuid4(),
                        name=name or f"Local {facility_type.title()}",
                        facility_type=facility_type,
                        latitude=p_lat,
                        longitude=p_lon,
                        address=place.get("formattedAddress"),
                        distance_m=round(dist_m_val, 1),
                        # Walking estimate at 4.5 km/h (straight-line; route call will refine)
                        travel_time_minutes=round(dist_m_val / 1000 / 4.5 * 60, 1),
                        data_freshness=DataFreshness.LIVE,
                        source_name="Google Places API",
                    )
                )

            logger.info(
                "[PLACES] Google Places API",
                facility_type=google_type,
                radius_m=radius_m,
                results=len(results),
            )

            # Cache the result list
            if results:
                await cache_set(
                    cache_key,
                    [r.model_dump(mode="json") for r in results],
                    _PLACES_CACHE_TTL,
                )

            return results

        except Exception as exc:
            logger.warning(
                "[PLACES] Google Places query failed",
                facility_type=google_type,
                error=str(exc),
            )
            return []


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    import math
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
