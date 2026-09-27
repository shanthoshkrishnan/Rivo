"""
RIVO Backend — Google Routes API Provider (Phase 3)
=====================================================
Implements RouteProvider using Google Routes API v2.

Phase 3 changes:
  - Field mask expanded to capture full transit itinerary:
      legs.steps (transit details, stop names, departure/arrival times,
      vehicle type, agency, headsign, line info)
  - _parse_response now builds RouteStep list from leg steps.
  - Traffic-aware duration returned for DRIVE / TWO_WHEELER with
    traffic_status=LIVE_TRAFFIC (not HISTORICAL).
  - departure_time / arrival_time plumbed through to RouteResult.
  - Fare parsing improved (units + nanos).
  - source_label set to "Google Routes API" on all results.

Key rules enforced here:
  1. API key is required — if absent, raises ProviderUnavailableError.
  2. Results are cached (route_cache). Caching complies with Google ToS:
       - Respect ROUTE_CACHE_TTL; do not persist indefinitely.
       - Cached results are labelled RECENT, not LIVE.
       - Do NOT reuse a stale "LIVE" result as if it were current.
  3. departure_bucket rounds time to 30-min windows for cache key.
  4. If the API call fails, raise ProviderUnavailableError so the caller
     can fall back to GTFS, OTP, or mock.
  5. TRANSIT results are ALWAYS tagged freshness=LIVE when fresh.
  6. DRIVE / TWO_WHEELER use TRAFFIC_AWARE routing.
  7. DO NOT invent stop names, schedules, bus numbers or fares.

Reference: https://developers.google.com/maps/documentation/routes/
"""
from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple
import unittest.mock

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.circuit_breaker import circuit_breaker
from app.core.config import DataFreshness, LiveApiDisabledError, get_settings
from app.core.logging import logger
from app.core.request_tracker import get_current_tracker
from app.db.cache import cache_get, cache_set, make_cache_key
from app.schemas.routing import (
    RouteRequest,
    RouteResult,
    RouteStep,
    TrafficInfo,
    TransitDetails,
)
from app.services.providers.base import RouteProvider

settings = get_settings()

GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"


# Map RIVO mode names to Google travel mode enum values

# Map RIVO mode names to Google travel mode enum values
_MODE_MAP = {
    "TRANSIT": "TRANSIT",
    "DRIVE": "DRIVE",
    "TWO_WHEELER": "TWO_WHEELER",
    "WALK": "WALK",
}

# Field mask: request exactly what the itinerary UI needs.
# Omit reviews, photos, attributions, alt_routes etc.
_TRANSIT_FIELD_MASK = (
    "routes.duration,"
    "routes.distanceMeters,"
    "routes.travelAdvisory,"
    "routes.polyline,"
    "routes.legs.duration,"
    "routes.legs.distanceMeters,"
    "routes.legs.polyline,"
    "routes.legs.startLocation,"
    "routes.legs.endLocation,"
    "routes.legs.steps.transitDetails,"
    "routes.legs.steps.travelMode,"
    "routes.legs.steps.staticDuration,"
    "routes.legs.steps.distanceMeters,"
    "routes.legs.steps.polyline,"
    "routes.legs.steps.navigationInstruction"
)

_DRIVE_FIELD_MASK = (
    "routes.duration,"
    "routes.distanceMeters,"
    "routes.travelAdvisory,"
    "routes.polyline,"
    "routes.legs.duration,"
    "routes.legs.distanceMeters,"
    "routes.legs.polyline"
)


class ProviderUnavailableError(Exception):
    """Raised when a routing provider cannot fulfil a request."""


def _bucket_time(dt: Optional[datetime]) -> str:
    """Round to 30-minute bucket for cache key."""
    if dt is None:
        return "default"
    minute = (dt.minute // 30) * 30
    return f"{dt.hour:02d}:{minute:02d}"


def _parse_duration_str(s: Optional[str]) -> Optional[int]:
    """Parse Google '123s' duration string to integer seconds."""
    if not s:
        return None
    try:
        return int(s.rstrip("s"))
    except (ValueError, AttributeError):
        return None


def _parse_fare(advisory: dict) -> Optional[float]:
    """
    Parse fare from travelAdvisory.transitFare.
    Google returns units (whole INR) + nanos (fractions).
    """
    fare_info = advisory.get("transitFare", {})
    if not fare_info:
        return None
    try:
        units = int(fare_info.get("units", 0) or 0)
        nanos = int(fare_info.get("nanos", 0) or 0)
        return round(units + nanos / 1e9, 2)
    except (TypeError, ValueError):
        return None


def _parse_datetime(val: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 string to datetime. Returns None on failure."""
    if not val:
        return None
    try:
        # Google returns RFC-3339 strings like "2024-01-01T07:35:00Z"
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_transit_step(step: dict) -> RouteStep:
    """
    Parse one Google step dict into a RouteStep.
    type is TRANSIT when transitDetails is present, else WALK.
    DO NOT invent any values not present in the Google response.
    """
    travel_mode = step.get("travelMode", "WALK")
    duration_sec = _parse_duration_str(step.get("duration") or step.get("staticDuration"))
    dist_m = step.get("distanceMeters")

    instruction_text: Optional[str] = None
    nav = step.get("navigationInstruction", {})
    if nav:
        instruction_text = nav.get("instructions")

    step_polyline: Optional[str] = None
    if step.get("polyline", {}).get("encodedPolyline"):
        step_polyline = step["polyline"]["encodedPolyline"]

    transit: Optional[TransitDetails] = None
    td = step.get("transitDetails", {})
    if td:
        stop_details = td.get("stopDetails", {})
        departure_stop = stop_details.get("departureStop", {}).get("name")
        arrival_stop = stop_details.get("arrivalStop", {}).get("name")
        dep_time_raw = stop_details.get("departureTime")
        arr_time_raw = stop_details.get("arrivalTime")

        transit_line = td.get("transitLine", {})
        agencies = transit_line.get("agencies", [])
        agency = agencies[0].get("name") if agencies else None
        vehicle = transit_line.get("vehicle", {})
        vehicle_type = vehicle.get("type")  # BUS, HEAVY_RAIL, SUBWAY, etc.

        # line name / short name
        line_name = transit_line.get("name")
        line_short = transit_line.get("nameShort")
        headsign = td.get("headsign")

        transit = TransitDetails(
            agency=agency,
            line=line_name,
            line_short_name=line_short,
            vehicle_type=vehicle_type,
            headsign=headsign,
            departure_stop=departure_stop,
            arrival_stop=arrival_stop,
            departure_time=_parse_datetime(dep_time_raw),
            arrival_time=_parse_datetime(arr_time_raw),
            num_stops=td.get("stopCount"),
        )

    # Build instruction if Google didn't supply one
    if not instruction_text and transit:
        dep = transit.departure_stop or "transit stop"
        arr = transit.arrival_stop or "destination stop"
        lbl = transit.line_short_name or transit.line or ""
        instruction_text = f"Board {lbl} at {dep} toward {transit.headsign or arr}"
    elif not instruction_text and travel_mode == "WALK":
        dist_label = f"{round(dist_m)} m" if dist_m else ""
        instruction_text = f"Walk {dist_label}"

    step_type = "TRANSIT" if transit else ("WALK" if travel_mode == "WALK" else travel_mode)

    return RouteStep(
        type=step_type,
        instruction=instruction_text,
        duration_seconds=duration_sec,
        distance_m=float(dist_m) if dist_m is not None else None,
        polyline=step_polyline,
        transit=transit,
    )


def classify_google_error(status_code: int, response_text: str) -> tuple[str, str]:
    """
    Classify Google API error without exposing any secrets.
    Returns (category, sanitized_message).
    Categories:
      - INVALID_KEY
      - API_NOT_ENABLED
      - BILLING_REQUIRED
      - PERMISSION_DENIED
      - QUOTA_EXCEEDED
      - INVALID_REQUEST
      - NETWORK_ERROR
      - OTHER
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


class GoogleRouteProvider(RouteProvider):
    """
    Live routing via Google Routes API v2.

    Modes supported: TRANSIT, DRIVE, TWO_WHEELER, WALK.
    Each mode requires a separate API call (Google API limitation).

    Cost control:
      - Check route cache first (ROUTE_CACHE_TTL seconds).
      - Only call the API for cache misses.
      - Caller is responsible for not routing more than ~50 final candidates.
    """

    PROVIDER_NAME = "google"
    SUPPORTED_MODES = {"TRANSIT", "DRIVE", "TWO_WHEELER", "WALK"}

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    @property
    def api_key(self) -> str:
        if self._api_key is not None:
            return self._api_key
        return get_settings().GOOGLE_ROUTES_API_KEY

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    def is_available(self) -> bool:
        if not (self.api_key and self.api_key.strip()):
            return False
        return circuit_breaker.is_routes_available()

    def supports_mode(self, mode: str) -> bool:
        return mode.upper() in self.SUPPORTED_MODES

    async def _call_api(self, payload: dict, field_mask: str) -> dict:
        """Make a single Google Routes API call with error classification and safety guard."""
        key = self.api_key
        if not key or not key.strip():
            raise ProviderUnavailableError("Google Routes API key not configured")

        tracker = get_current_tracker()
        if not tracker.can_request_route():
            raise ProviderUnavailableError("Google Routes request budget exceeded for this session")

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    GOOGLE_ROUTES_URL,
                    json=payload,
                    headers={
                        "X-Goog-Api-Key": key.strip(),
                        "X-Goog-FieldMask": field_mask,
                    },
                )
                latency_ms = (time.time() - t0) * 1000
                if resp.status_code >= 400:
                    category, sanitized_msg = classify_google_error(resp.status_code, resp.text)
                    if category == "QUOTA_EXCEEDED" or resp.status_code == 429:
                        circuit_breaker.trip_routes("QUOTA_EXCEEDED")
                    logger.warning(
                        "[ROUTES] Google Routes API error",
                        category=category,
                        status_code=resp.status_code,
                        message=sanitized_msg,
                    )
                    raise ProviderUnavailableError(f"Google Routes API [{category}]: {sanitized_msg}")

                tracker.record_route_call("google", cache_hit=False, latency_ms=latency_ms)
                return resp.json()
        except httpx.TimeoutException:
            logger.warning("[ROUTES] Google Routes API timeout")
            raise ProviderUnavailableError("Google Routes API [NETWORK_ERROR]: Request timed out")
        except httpx.NetworkError as exc:
            logger.warning("[ROUTES] Google Routes API network error", error=str(exc))
            raise ProviderUnavailableError("Google Routes API [NETWORK_ERROR]: Network connection failed")

    def _parse_response(
        self,
        data: dict,
        mode: str,
        departure_time: Optional[datetime],
    ) -> Optional[RouteResult]:
        routes = data.get("routes", [])
        if not routes:
            return None
        route = routes[0]
        legs = route.get("legs", [{}])
        leg = legs[0] if legs else {}

        # Top-level duration
        duration_str = route.get("duration", "0s")
        duration_sec = _parse_duration_str(duration_str) or 0

        distance_m = float(route.get("distanceMeters", 0))

        # Route-level polyline
        geometry: Optional[str] = None
        if route.get("polyline", {}).get("encodedPolyline"):
            geometry = route["polyline"]["encodedPolyline"]

        # Fare
        advisory = route.get("travelAdvisory", {})
        fare_amount = _parse_fare(advisory) if mode == "TRANSIT" else None

        # Traffic info for road modes
        traffic: Optional[TrafficInfo] = None
        if mode in ("DRIVE", "TWO_WHEELER"):
            # staticDuration = no-traffic; duration = traffic-aware
            static_dur_str = route.get("staticDuration")
            static_dur = _parse_duration_str(static_dur_str)
            if static_dur and static_dur != duration_sec:
                traffic = TrafficInfo(
                    normal_duration_seconds=static_dur,
                    traffic_duration_seconds=duration_sec,
                    traffic_status="LIVE_TRAFFIC",
                )
            else:
                traffic = TrafficInfo(
                    normal_duration_seconds=duration_sec,
                    traffic_duration_seconds=None,
                    traffic_status="HISTORICAL",
                )

        # Build itinerary steps from leg steps (TRANSIT mode primarily)
        steps: List[RouteStep] = []
        walk_sec = 0
        wait_sec = 0
        in_vehicle_sec = 0
        transfer_count = 0

        leg_steps = leg.get("steps", [])
        if mode == "TRANSIT" and leg_steps:
            for s in leg_steps:
                rs = _parse_transit_step(s)
                steps.append(rs)
                step_dur = rs.duration_seconds or 0
                if rs.type == "WALK":
                    walk_sec += step_dur
                elif rs.type == "TRANSIT":
                    in_vehicle_sec += step_dur
                elif rs.type == "WAIT":
                    wait_sec += step_dur

            # Count transfers = number of TRANSIT steps - 1
            transit_steps = [s for s in steps if s.type == "TRANSIT"]
            transfer_count = max(0, len(transit_steps) - 1)

        # Parse departure/arrival times from first transit step if available
        dep_time: Optional[datetime] = departure_time
        arr_time: Optional[datetime] = None
        if steps:
            first_transit = next((s for s in steps if s.type == "TRANSIT"), None)
            last_transit = None
            for s in reversed(steps):
                if s.type == "TRANSIT":
                    last_transit = s
                    break
            if first_transit and first_transit.transit:
                dep_time = first_transit.transit.departure_time or dep_time
            if last_transit and last_transit.transit:
                arr_time = last_transit.transit.arrival_time

        return RouteResult(
            mode=mode,
            provider=self.PROVIDER_NAME,
            source_label="Google Routes API",
            distance_m=distance_m,
            duration_seconds=duration_sec,
            walk_seconds=walk_sec if walk_sec else None,
            wait_seconds=wait_sec if wait_sec else None,
            in_vehicle_seconds=in_vehicle_sec if in_vehicle_sec else None,
            transfer_count=transfer_count,
            fare_amount=fare_amount,
            route_geometry=geometry,
            observed_at=datetime.now(timezone.utc),
            data_freshness=DataFreshness.LIVE,
            steps=steps,
            departure_time=dep_time,
            arrival_time=arr_time,
            traffic=traffic,
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

            # ── Cache check ────────────────────────────────────────────────────
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
                result.source_label = "Google Routes API (cached)"
                tracker = get_current_tracker()
                tracker.record_route_call("google", cache_hit=True, latency_ms=0.0, operation=f"compute_{mode_upper.lower()}_cached")
                results.append(result)
                logger.debug(
                    "[ROUTE] cache hit",
                    provider="google",
                    mode=mode_upper,
                )
                continue

            # ── Live API call ──────────────────────────────────────────────────
            try:
                google_mode = _MODE_MAP[mode_upper]
                is_road = google_mode in ("DRIVE", "TWO_WHEELER")
                field_mask = _DRIVE_FIELD_MASK if is_road else _TRANSIT_FIELD_MASK

                payload: dict = {
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
                    "computeAlternativeRoutes": False,
                    "languageCode": "en-IN",
                    "units": "METRIC",
                }

                # Traffic-aware routing for road modes
                if is_road:
                    payload["routingPreference"] = "TRAFFIC_AWARE"

                # Departure time for transit (ISO-8601)
                if mode_upper == "TRANSIT":
                    dep = request.departure_time
                    if dep is None:
                        dep = datetime.now(timezone.utc)
                    # Validate: Google requires a current or future departure
                    if dep.tzinfo is None:
                        from datetime import timezone as tz
                        dep = dep.replace(tzinfo=tz.utc)
                    payload["departureTime"] = dep.strftime("%Y-%m-%dT%H:%M:%SZ")

                data = await self._call_api(payload, field_mask)
                result = self._parse_response(data, mode_upper, request.departure_time)
                if result:
                    logger.info(
                        "[ROUTE] Google Routes API",
                        provider="google",
                        mode=mode_upper,
                        origin_lat=round(request.origin_lat, 4),
                        origin_lon=round(request.origin_lon, 4),
                        dest_lat=round(request.dest_lat, 4),
                        dest_lon=round(request.dest_lon, 4),
                        departure=bucket,
                        duration_sec=result.duration_seconds,
                        transfers=result.transfer_count,
                        steps=len(result.steps),
                    )
                    await cache_set(
                        cache_key,
                        result.model_dump(mode="json"),
                        settings.ROUTE_CACHE_TTL,
                    )
                    results.append(result)
            except ProviderUnavailableError:
                raise
            except Exception as exc:
                logger.error(
                    "Google Routes API error",
                    mode=mode_upper,
                    error=str(exc),
                )
                raise ProviderUnavailableError(
                    f"Google Routes failed for {mode_upper}: {exc}"
                ) from exc

        # Badge assignment
        _assign_badges(results)
        return results

    async def compute_route_matrix(
        self,
        origins: List[Tuple[float, float]],
        dest_lat: float,
        dest_lon: float,
        travel_mode: str = "TRANSIT",
    ) -> Dict[int, Dict[str, Any]]:
        """
        Compute coarse Route Matrix (duration + distance only) for candidate ranking.
        Does NOT build detailed transit steps or polylines, saving compute & bandwidth.
        Returns mapping {origin_index: {"duration_seconds": ..., "distance_meters": ...}}.
        """
        key = self.api_key
        if not key or not self.is_available():
            raise ProviderUnavailableError("Google Routes API not available for route matrix")

        tracker = get_current_tracker()
        if not tracker.can_request_route():
            raise ProviderUnavailableError("Google Routes budget exceeded for route matrix")

        google_mode = _MODE_MAP.get(travel_mode.upper(), "TRANSIT")
        matrix_origins = [
            {"waypoint": {"location": {"latLng": {"latitude": lat, "longitude": lon}}}}
            for lat, lon in origins
        ]
        matrix_dests = [
            {"waypoint": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lon}}}}
        ]
        payload = {
            "origins": matrix_origins,
            "destinations": matrix_dests,
            "travelMode": google_mode,
        }
        field_mask = "originIndex,destinationIndex,status,condition,distanceMeters,duration"

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    GOOGLE_MATRIX_URL,
                    json=payload,
                    headers={
                        "X-Goog-Api-Key": key.strip(),
                        "X-Goog-FieldMask": field_mask,
                    },
                )
                latency_ms = (time.time() - t0) * 1000
                if resp.status_code >= 400:
                    category, sanitized = classify_google_error(resp.status_code, resp.text)
                    if category == "QUOTA_EXCEEDED" or resp.status_code == 429:
                        circuit_breaker.trip_routes("QUOTA_EXCEEDED")
                    raise ProviderUnavailableError(f"Route Matrix [{category}]: {sanitized}")

                data = resp.json()
                tracker.record_route_call("google", cache_hit=False, latency_ms=latency_ms, operation="compute_route_matrix")

            # Parse elements
            matrix_results: Dict[int, Dict[str, Any]] = {}
            elements = data if isinstance(data, list) else data.get("elements", [])
            for el in elements:
                idx = el.get("originIndex", 0)
                dur_str = el.get("duration", "0s")
                dur_sec = _parse_duration_str(dur_str)
                dist_m = float(el.get("distanceMeters", 0))
                matrix_results[idx] = {
                    "duration_seconds": dur_sec,
                    "distance_meters": dist_m,
                }
            return matrix_results
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(f"Route matrix failed: {exc}") from exc


def _assign_badges(results: List[RouteResult]) -> None:
    """Mark fastest, cheapest, fewest-transfers badges."""
    valid_dur = [r for r in results if r.duration_seconds is not None]
    valid_fare = [r for r in results if r.fare_amount is not None]
    valid_xfer = [r for r in results if r.transfer_count is not None]
    if valid_dur:
        min(valid_dur, key=lambda r: r.duration_seconds).is_fastest = True  # type: ignore
    if valid_fare:
        min(valid_fare, key=lambda r: r.fare_amount).is_cheapest = True  # type: ignore
    if valid_xfer:
        min(valid_xfer, key=lambda r: r.transfer_count).is_fewest_transfers = True  # type: ignore
